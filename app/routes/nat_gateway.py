from typing import List

from fastapi import APIRouter, HTTPException

from app.models.common import StackResponse
from app.models.nat_gateway import NatGatewayRequest
from app.pulumi_programs.nat_gateway import create_nat_gateway_program
from app.utils.stack import stack_up_safe, stack_outputs, stack_destroy, stack_region, stack_list, stack_exists
from app.utils.region_state import get_region

router = APIRouter(prefix="/nat-gateway", tags=["NAT Gateway"])


@router.get("", response_model=List[StackResponse])
def list_nat_gateways():
    """List all NAT Gateway stacks."""
    try:
        all_stacks = stack_list()
        region_h =get_region()
        vipes = [stack for stack in all_stacks if "nat_gateway_id" in stack["outputs"] and stack["outputs"].get("nat_region")==region_h]
        return [StackResponse(status="ok", stack=s["name"], outputs=s["outputs"]) for s in vipes]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("", response_model=StackResponse, status_code=201)
def create_nat_gateway(req: NatGatewayRequest):
    """Create a NAT Gateway (with an auto-created or provided Elastic IP)."""
    if stack_exists(req.stack):
        raise HTTPException(status_code=409, detail="NAT Gateway already exist")
    region = req.region or get_region()
    if not region:
        raise HTTPException(status_code=422, detail="No region provided and no active region selected.")
    try:
        program = create_nat_gateway_program(
            req.name, req.subnet_id, region, req.create_eip, req.eip_allocation_id, req.tags
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
def get_nat_gateway(stack_name: str):
    """Fetch outputs of an existing NAT Gateway stack."""
    try:
        outputs = stack_outputs(stack_name)
        return StackResponse(status="ok", stack=stack_name, outputs=outputs)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# @router.put("/{stack_name}", response_model=StackResponse)
# def update_nat_gateway(stack_name: str, req: NatGatewayRequest):
#     """Update an existing NAT Gateway stack."""
#     if req.stack != stack_name:
#         raise HTTPException(status_code=400, detail="YOU CAN NOT CHANGE STACK NAME")
#     region = req.region or get_region()
#     if not region:
#         raise HTTPException(status_code=422, detail="No region provided and no active region selected. Call POST /region/{region} first.")
#     try:
#         program = create_nat_gateway_program(
#             req.name, req.subnet_id, req.create_eip, req.eip_allocation_id, req.tags
#         )
#         outputs = stack_up_safe(stack_name, region, program)
#         return StackResponse(status="updated", stack=stack_name, outputs=outputs)
#     except ValueError as exc:
#         raise HTTPException(status_code=400, detail=str(exc))
#
#
# @router.patch("/{stack_name}", response_model=StackResponse)
# def patch_nat_gateway(stack_name: str, req: NatGatewayPatchRequest):
#     """Partially update a NAT Gateway stack — only send the fields you want to change."""
#     if req.stack is not None and req.stack != stack_name:
#         raise HTTPException(status_code=400, detail="YOU CAN NOT CHANGE STACK NAME")
#     try:
#         current = stack_outputs(stack_name)
#         region = req.region or get_region() or stack_region(stack_name)
#         name = req.name if req.name is not None else current.get("name", stack_name)
#         subnet_id = req.subnet_id if req.subnet_id is not None else current.get("subnet_id")
#         if subnet_id is None:
#             raise HTTPException(status_code=422, detail="subnet_id could not be resolved from stack outputs; provide it in the request body")
#         create_eip = req.create_eip if req.create_eip is not None else current.get("create_eip", True)
#         eip_allocation_id = req.eip_allocation_id if req.eip_allocation_id is not None else current.get("eip_allocation_id")
#         tags = req.tags if req.tags is not None else {}
#         program = create_nat_gateway_program(name, subnet_id, create_eip, eip_allocation_id, tags)
#         outputs = stack_up_safe(stack_name, region, program)
#         return StackResponse(status="updated", stack=stack_name, outputs=outputs)
#     except Exception as exc:
#         raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/{stack_name}")
def delete_nat_gateway(stack_name: str):
    """Destroy the NAT Gateway stack."""
    try:
        stack_destroy(stack_name)
        return {"status": "deleted", "stack": stack_name}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
