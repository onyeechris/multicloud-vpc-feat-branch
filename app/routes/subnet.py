from typing import List

from fastapi import APIRouter, HTTPException

from app.models.common import StackResponse
from app.models.subnet import SubnetRequest, SubnetPatchRequest, SubnetConfig
from app.pulumi_programs.subnet import create_subnet_program
from app.utils.stack import stack_up_safe, stack_outputs, stack_destroy, stack_region, stack_list, stack_exists
from app.utils.region_state import get_region

router = APIRouter(prefix="/subnet", tags=["Subnet"])


@router.get("", response_model=List[StackResponse])
def list_subnets():
    """List all Subnet stacks."""
    try:
        all_stacks = stack_list()
        region_h = get_region()
        vipes = [stack for stack in all_stacks if "subnet_configs" in stack["outputs"] and stack["outputs"].get("sub_region") == region_h]
        
        return [StackResponse(status="ok", stack=s["name"], outputs=s["outputs"]) for s in vipes]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("", response_model=StackResponse, status_code=201)
def create_subnet(req: SubnetRequest):
    """Create a subnet stack (single subnet if one entry, multiple if more)."""
    if stack_exists(req.stack):
        raise HTTPException(status_code=409, detail="Subnet already exist")
    region = req.region or get_region()
    if not region:
        raise HTTPException(status_code=422, detail="No region provided and no active region selected. Call POST /region/{region} first.")
    try:
        program = create_subnet_program(req.name, req.vpc_id, region, req.subnets, req.tags)
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
def get_subnet(stack_name: str):
    """Fetch outputs of an existing subnet stack."""
    try:
        outputs = stack_outputs(stack_name)
        return StackResponse(status="ok", stack=stack_name, outputs=outputs)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# @router.put("/{stack_name}", response_model=StackResponse)
# def update_subnet(stack_name: str, req: SubnetRequest):
#     """Update an existing subnet stack."""
#     if req.stack != stack_name:
#         raise HTTPException(status_code=400, detail="YOU CAN NOT CHANGE STACK NAME")
#     region = req.region or get_region()
#     if not region:
#         raise HTTPException(status_code=422, detail="No region provided and no active region selected.")
#     try:
#         program = create_subnet_program(req.name, req.vpc_id, region, req.subnets, req.tags)
#         outputs = stack_up_safe(stack_name, region, program)
#         return StackResponse(status="updated", stack=stack_name, outputs=outputs)
#     except ValueError as exc:
#         raise HTTPException(status_code=400, detail=str(exc))




@router.patch("/{stack_name}", response_model=StackResponse)
def patch_subnet(stack_name: str, req: SubnetPatchRequest):
    """Partially update a subnet stack — only send the fields you want to change."""
    if req.stack is not None and req.stack != stack_name:
        raise HTTPException(status_code=400, detail="YOU CAN NOT CHANGE STACK NAME")
    try:
        current = stack_outputs(stack_name)
        region = req.region or get_region() or stack_region(stack_name)
        name = req.name if req.name is not None else current.get("name", stack_name)
        vpc_id = req.vpc_id if req.vpc_id is not None else current.get("vpc_id")
        if vpc_id is None:
            raise HTTPException(status_code=422, detail="vpc_id could not be resolved from stack outputs; provide it in the request body")
        if req.subnets is not None:
            subnets = req.subnets
        else:
            raw = current.get("subnet_configs")
            if not raw:
                raise HTTPException(status_code=422, detail="subnets could not be resolved from stack outputs; provide them in the request body")
            subnets = [SubnetConfig(**s) for s in raw]
        tags = req.tags if req.tags is not None else {}
        program = create_subnet_program(name, vpc_id, region, subnets, tags)
        outputs = stack_up_safe(stack_name, region, program)
        return StackResponse(status="updated", stack=stack_name, outputs=outputs)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@router.delete("/{stack_name}")
def delete_subnet(stack_name: str):
    """Destroy the subnet stack."""
    try:
        stack_destroy(stack_name)
        return {"status": "deleted", "stack": stack_name}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
