from typing import List

from fastapi import APIRouter, HTTPException

from app.models.common import StackResponse
from app.models.route import RouteRequest, RoutePatchRequest, RouteEntry
from app.pulumi_programs.route import create_route_program
from app.utils.stack import stack_up_safe, stack_outputs, stack_destroy, stack_region, stack_list, stack_exists
from app.utils.region_state import get_region

router = APIRouter(prefix="/route", tags=["Route"])


def resolve_vgw_id(vgw_stack: str):
    """Pull `vgw_id` from an VGW stack's outputs."""
    try:
        outputs = stack_outputs(vgw_stack)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=f"Could not resolve NSG stack '{vgw_stack}': {exc}")
    vgw_id = outputs.get("vgw_id")
    if not vgw_id:
        raise HTTPException(status_code=404, detail=f"vgw_id not found in stack '{vgw_stack}'")
    return vgw_id


@router.get("", response_model=List[StackResponse])
def list_routes():
    """List all Route stacks."""
    try:
        all_stacks = stack_list()
        region = get_region()
        vipes = [stack for stack in all_stacks if "route_count" in stack["outputs"] and stack["outputs"].get("route_region") == region]
        return [StackResponse(status="ok", stack=s["name"], outputs=s["outputs"]) for s in vipes]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("", response_model=StackResponse, status_code=201)
def create_route(req: RouteRequest):
    """Add one or more routes to an existing route table."""
    if stack_exists(req.stack):
        raise HTTPException(status_code=409, detail="Route already exist")
    region = req.region or get_region()
    if not region:
        raise HTTPException(status_code=422, detail="No region provided and no active region selected. Call POST /region/{region} first.")
    try:
        # program = create_route_program(req.name, req.route_table_id, region, req.routes, req.tags)
        vgw_id = resolve_vgw_id(req.vgw_stack) if req.vgw_stack else None
        program = create_route_program(req.name, req.route_table_id, region, req.routes, req.tags, vgw_id)
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
def get_route(stack_name: str):
    """Fetch outputs of an existing route stack."""
    try:
        outputs = stack_outputs(stack_name)
        return StackResponse(status="ok", stack=stack_name, outputs=outputs)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# @router.put("/{stack_name}", response_model=StackResponse)
# def update_route(stack_name: str, req: RouteRequest):
#     """Update routes in a route table (Pulumi diffs additions and removals)."""
#     if req.stack != stack_name:
#         raise HTTPException(status_code=400, detail="YOU CAN NOT CHANGE STACK NAME")
#     region = req.region or get_region()
#     if not region:
#         raise HTTPException(status_code=422, detail="No region provided and no active region selected. Call POST /region/{region} first.")
#     try:
#         program = create_route_program(req.name, req.route_table_id, region, req.routes, req.tags)
#         outputs = stack_up_safe(stack_name, region, program)
#         return StackResponse(status="updated", stack=stack_name, outputs=outputs)
#     except ValueError as exc:
#         raise HTTPException(status_code=400, detail=str(exc))



@router.patch("/{stack_name}", response_model=StackResponse)
def patch_route(stack_name: str, req: RoutePatchRequest):
    """Partially update a route stack — only send the fields you want to change."""
    if req.stack is not None and req.stack != stack_name:
        raise HTTPException(status_code=400, detail="YOU CAN NOT CHANGE STACK NAME")
    try:
        current = stack_outputs(stack_name)
        region = req.region or get_region() or stack_region(stack_name)
        name = req.name if req.name is not None else current.get("name", stack_name)
        route_table_id = req.route_table_id if req.route_table_id is not None else current.get("route_table_id")
        if route_table_id is None:
            raise HTTPException(status_code=422, detail="route_table_id could not be resolved from stack outputs; provide it in the request body")
        if req.routes is not None:
            routes = req.routes
        else:
            raw = current.get("route_configs")
            if not raw:
                raise HTTPException(status_code=422, detail="routes could not be resolved from stack outputs; provide them in the request body")
            routes = [RouteEntry(**r) for r in raw]
        tags = req.tags if req.tags is not None else {}
        vgw_id = resolve_vgw_id(req.vgw_stack) if req.vgw_stack is not None else current.get("vgw_id") or None
        # program = create_route_program(name, route_table_id, region, routes, tags)
        program = create_route_program(name, route_table_id, region, routes, tags, vgw_id)
        outputs = stack_up_safe(stack_name, region, program)
        return StackResponse(status="updated", stack=stack_name, outputs=outputs)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/{stack_name}")
def delete_route(stack_name: str):
    """Remove all routes managed by this stack from the route table."""
    try:
        stack_destroy(stack_name)
        return {"status": "deleted", "stack": stack_name}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
