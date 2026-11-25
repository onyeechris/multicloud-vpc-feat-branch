import os
import boto3
import json
from botocore.exceptions import ClientError
from typing import Callable
from importlib.metadata import version
from pulumi import automation as auto
import logging
logger = logging.getLogger(__name__)

_s3 = boto3.client("s3", region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"))
_BUCKET = os.getenv("PULUMI_BACKEND_URL", "").replace("s3://", "")

#----------------------------------------

PROJECT_NAME = "multicloud-networking"
_AWS_PLUGIN_VERSION = f"v{version('pulumi-aws')}"

_AWS_INPUT_ERRORS = (
    "InvalidSubnet",
    "does not exist",
    "InvalidVpcID",
    "InvalidParameterValue",
    "InvalidAMIID",
    "InvalidNatGatewayID",
    "NatGatewayNotFound",
    "InvalidAllocationID",
    "InvalidInternetGatewayID",
    "InvalidRouteTableID",
    "Gateway.NotAttached",
    "no Internet gateway attached",
)

# Function to fetch from s3

def _get_stack_state_from_s3(stack_name: str) -> dict:
    key = f".pulumi/stacks/{PROJECT_NAME}/{stack_name}.json"
    try:
        obj = _s3.get_object(Bucket=_BUCKET, Key=key)
        state = json.loads(obj["Body"].read())
        outputs = {}
        for resource in state.get("checkpoint", {}).get("latest", {}).get("resources", []):
            if resource.get("type") == "pulumi:pulumi:Stack":
                outputs = resource.get("outputs", {})  # ← plain values, no .get("value")
        return outputs
    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchKey":
            raise KeyError(f"Stack {stack_name} not found")
        raise
# ---------------------------------------------------
def _plugin_present(stack: auto.Stack, name: str, version: str, kind: str = "resource") -> bool:
    installed = stack.workspace.list_plugins()
    return any(p.name == name and p.kind == kind and p.version == version for p in installed)

def stack_up(stack_name: str, region: str, program: Callable) -> dict:
    stack = auto.create_or_select_stack(
        stack_name=stack_name,
        project_name=PROJECT_NAME,
        program=program,
    )

    if _plugin_present(stack, "aws", _AWS_PLUGIN_VERSION):
        logger.info(f"Plugin aws@{_AWS_PLUGIN_VERSION} already installed, skipping install")
    else:
        stack.workspace.install_plugin("aws", _AWS_PLUGIN_VERSION)

    stack.set_config("aws:region", auto.ConfigValue(value=region))
    result = stack.up(on_output=print)
    return {k: v.value for k, v in result.outputs.items()}




# def stack_up(stack_name: str, region: str, program: Callable) -> dict:
#     stack = auto.create_or_select_stack(
#         stack_name=stack_name,
#         project_name=PROJECT_NAME,
#         program=program,
#     )
#     stack.workspace.install_plugin("aws", _AWS_PLUGIN_VERSION)
#     stack.set_config("aws:region", auto.ConfigValue(value=region))
#     result = stack.up(on_output=print)
#     return {k: v.value for k, v in result.outputs.items()}


def stack_up_safe(stack_name: str, region: str, program: Callable) -> dict:
    """Wrap stack_up and re-raise known AWS input errors as ValueError (→ HTTP 400)."""
    try:
        return stack_up(stack_name, region, program)
    except Exception as exc:
        msg = str(exc)
        if any(k in msg for k in _AWS_INPUT_ERRORS):
            raise ValueError(f"Invalid AWS input: {msg}")
        raise


def stack_exists(stack_name: str) -> bool:
    try:
        auto.select_stack(
            stack_name=stack_name,
            project_name=PROJECT_NAME,
            program=lambda: None,
        )
        return True
    except auto.StackNotFoundError:
        return False

def stack_outputs(stack_name: str) -> dict:
    """Get stack outputs by reading S3 directly — fast."""
    return _get_stack_state_from_s3(stack_name)


def stack_region(stack_name: str) -> str:
    stack = auto.select_stack(
        stack_name=stack_name,
        project_name=PROJECT_NAME,
        program=lambda: None,
    )
    return stack.get_config("aws:region").value


def stack_list() -> list[dict]:
    """List all stacks by reading S3 directly — fast."""
    key_prefix = f".pulumi/stacks/{PROJECT_NAME}/"
    try:
        response = _s3.list_objects_v2(Bucket=_BUCKET, Prefix=key_prefix)
        result = []
        for obj in response.get("Contents", []):
            # stack_name = obj["Key"].replace(key_prefix, "").replace(".json", "")      # Has been replaced with better slicing
            key = obj["Key"]
            if not key.endswith(".json"):
                continue
            stack_name = key[len(key_prefix): -len(".json")]
            if stack_name.startswith("."):
                continue
            try:
                outputs = _get_stack_state_from_s3(stack_name)
            except (ClientError, KeyError) as e:
                logger.warning(f"Failed to get stack outputs for {stack_name!r}: {e}")
                outputs = {}
            result.append({"name": stack_name, "outputs": outputs})
        return result
    except Exception as exc:
        raise RuntimeError(f"Failed to list stacks from S3: {exc}")


def stack_destroy(stack_name: str) -> None:
    stack = auto.select_stack(
        stack_name=stack_name,
        project_name=PROJECT_NAME,
        program=lambda: None,
    )
    stack.destroy(on_output=print)
    stack.workspace.remove_stack(stack_name)
