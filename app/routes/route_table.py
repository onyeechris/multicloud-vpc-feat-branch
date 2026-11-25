from typing import List

from fastapi import APIRouter, HTTPException

from app.models.common import StackResponse
from app.models.route_table import RouteTableRequest, RouteTablePatchRequest
from app.pulumi_programs.route_table import create_route_table_program
from app.utils.stack import stack_up_safe, stack_outputs, stack_destroy, stack_region, stack_list, stack_exists
from app.utils.region_state import get_region

router = APIRouter(prefix="/route-table", tags=["Route Table"])


@router.get("", response_model=List[StackResponse])
def list_route_tables():
    """List all Route Table stacks."""
    try:
        all_stacks = stack_list()
        vipes = [stack for stack in all_stacks if "associated_subnet_ids" in stack["outputs"]]
        region_h = get_region()
        vipes = [stack for stack in vipes if stack["outputs"].get("rt_region")==region_h]
        return [
            StackResponse(status="ok", stack=s["name"], outputs=s["outputs"]) for s in vipes]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("", response_model=StackResponse, status_code=201)
def create_route_table(req: RouteTableRequest):
    """Create a route table and optionally associate subnets."""
    if stack_exists(req.stack):
        raise HTTPException(status_code=409, detail="Route Table already exist")
    region = req.region or get_region()
    if not region:
        raise HTTPException(status_code=422, detail="No region provided and no active region selected.")
    try:
        program = create_route_table_program(req.name, req.vpc_id, region, req.subnet_ids, req.tags)
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
def get_route_table(stack_name: str):
    """Fetch outputs of an existing route table stack."""
    try:
        outputs = stack_outputs(stack_name)
        return StackResponse(status="ok", stack=stack_name, outputs=outputs)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# @router.put("/{stack_name}", response_model=StackResponse)
# def update_route_table(stack_name: str, req: RouteTableRequest):
#     """Update route table associations."""
#     if req.stack != stack_name:
#         raise HTTPException(status_code=400, detail="YOU CAN NOT CHANGE STACK NAME")
#     region = req.region or get_region()
#     if not region:
#         raise HTTPException(status_code=422, detail="No region provided and no active region selected.")
#     try:
#         program = create_route_table_program(req.name, req.vpc_id, region, req.subnet_ids, req.tags)
#         outputs = stack_up_safe(stack_name, region, program)
#         return StackResponse(status="updated", stack=stack_name, outputs=outputs)
#     except ValueError as exc:
#         raise HTTPException(status_code=400, detail=str(exc))



@router.patch("/{stack_name}", response_model=StackResponse)
def patch_route_table(stack_name: str, req: RouteTablePatchRequest):
    """Partially update a route table stack — only send the fields you want to change."""
    if req.stack is not None and req.stack != stack_name:
        raise HTTPException(status_code=400, detail="YOU CAN NOT CHANGE STACK NAME")
    try:
        current = stack_outputs(stack_name)
        region = req.region or get_region() or stack_region(stack_name)
        name = req.name if req.name is not None else current.get("name", stack_name)
        vpc_id = req.vpc_id if req.vpc_id is not None else current.get("vpc_id")
        if vpc_id is None:
            raise HTTPException(status_code=422, detail="vpc_id could not be resolved from stack outputs; provide it in the request body")
        subnet_ids = req.subnet_ids if req.subnet_ids is not None else current.get("associated_subnet_ids", [])
        tags = req.tags if req.tags is not None else {}
        program = create_route_table_program(name, vpc_id, region, subnet_ids, tags)
        outputs = stack_up_safe(stack_name, region, program)
        return StackResponse(status="updated", stack=stack_name, outputs=outputs)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/{stack_name}")
def delete_route_table(stack_name: str):
    """Destroy the route table stack."""
    try:
        stack_destroy(stack_name)
        return {"status": "deleted", "stack": stack_name}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
