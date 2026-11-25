from typing import List

from fastapi import APIRouter, HTTPException

from app.models.common import StackResponse
from app.models.vpc import VpcRequest, VpcPatchRequest
from app.pulumi_programs.vpc import create_vpc_program
from app.utils.stack import stack_up_safe, stack_outputs, stack_destroy, stack_region, stack_list, stack_exists
from app.utils.region_state import get_region

router = APIRouter(prefix="/vpc", tags=["VPC"])


@router.get("", response_model=List[StackResponse])
def list_vpcs():
    """List all VPC stacks."""
    try:
        all_stacks = stack_list()
        region_h = get_region()
        vipes = [stack for stack in all_stacks if "vpc_cidr" in stack["outputs"]]
        vipes = [stack for stack in vipes if stack["outputs"].get("vpc_region")==region_h]
        return [
            StackResponse(status="ok", stack=s["name"], outputs=s["outputs"]) for s in vipes]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("", response_model=StackResponse, status_code=201)
def create_vpc(req: VpcRequest):
    """Create a new VPC stack."""
    if stack_exists(req.stack):
        raise HTTPException(status_code=409, detail=f"{req.stack} already exist")
    region = req.region or get_region()
    if not region:
        raise HTTPException(status_code=422, detail="No region provided and no active region selected. Call POST /region/{region} first.")
    try:
        program = create_vpc_program(
            name=req.name,
            cidr_block=req.cidr_block,
            region=region,
            enable_dns_support=req.enable_dns_support,
            enable_dns_hostnames=req.enable_dns_hostnames,
            tags=req.tags,
        )
        outputs = stack_up_safe(req.stack, region, program)
        return StackResponse(status="created", stack=req.stack, outputs=outputs)
    except Exception as exc:
        if stack_exists(req.stack):
            try:
                stack_destroy(req.stack)
            except Exception as exc2:
                raise HTTPException(
                    status_code=500,
                    detail=f"Original error: {exc}. Also failed to cleanup: {exc2}. Manually check stack {req.stack}"
                )
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/{stack_name}", response_model=StackResponse)
def get_vpc(stack_name: str):
    """Fetch outputs of an existing VPC stack."""
    try:
        outputs = stack_outputs(stack_name)
        return StackResponse(status="ok", stack=stack_name, outputs=outputs)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# @router.put("/{stack_name}", response_model=StackResponse)
# def update_vpc(stack_name: str, req: VpcRequest):
#     """Update an existing VPC stack (Pulumi diffs and applies changes)."""
#     if req.stack != stack_name:
#         raise HTTPException(status_code=400, detail="YOU CAN NOT CHANGE STACK NAME")
#     region = req.region or get_region()
#     if not region:
#         raise HTTPException(status_code=422, detail="No region provided and no active region selected. Call POST /region/{region} first.")
#     try:
#         program = create_vpc_program(
#             name=req.name,
#             cidr_block=req.cidr_block,
#             region=region,
#             enable_dns_support=req.enable_dns_support,
#             enable_dns_hostnames=req.enable_dns_hostnames,
#             tags=req.tags,
#         )
#         outputs = stack_up_safe(stack_name, region, program)
#         return StackResponse(status="updated", stack=stack_name, outputs=outputs)
#     except ValueError as exc:
#         raise HTTPException(status_code=400, detail=str(exc))

@router.patch("/{stack_name}", response_model=StackResponse)
def patch_vpc(stack_name: str, req: VpcPatchRequest):
    """Partially update a VPC stack — only send the fields you want to change."""
    if req.stack is not None and req.stack != stack_name:
        raise HTTPException(status_code=400, detail="YOU CAN NOT CHANGE STACK NAME")
    try:
        current = stack_outputs(stack_name)
        region = req.region or get_region() or stack_region(stack_name)
        name = req.name if req.name is not None else current.get("name", stack_name)
        cidr_block = req.cidr_block if req.cidr_block is not None else current.get("vpc_cidr", "10.0.0.0/16")
        enable_dns_support = req.enable_dns_support if req.enable_dns_support is not None else current.get("enable_dns_support", True)
        enable_dns_hostnames = req.enable_dns_hostnames if req.enable_dns_hostnames is not None else current.get("enable_dns_hostnames", True)
        tags = req.tags if req.tags is not None else {}
        program = create_vpc_program(name, cidr_block, region, enable_dns_support, enable_dns_hostnames, tags)
        outputs = stack_up_safe(stack_name, region, program)
        return StackResponse(status="updated", stack=stack_name, outputs=outputs)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/{stack_name}")
def delete_vpc(stack_name: str):
    """Destroy the VPC stack and all its resources."""
    try:
        stack_destroy(stack_name)
        return {"status": "deleted", "stack": stack_name}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
