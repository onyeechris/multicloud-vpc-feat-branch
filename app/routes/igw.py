from typing import List
from fastapi import APIRouter, HTTPException
from app.models.common import StackResponse
from app.models.igw import IgwRequest
from app.pulumi_programs.igw import create_igw_program
from app.utils.stack import stack_up_safe, stack_outputs, stack_destroy, stack_region, stack_list, stack_exists
from app.utils.region_state import get_region
router = APIRouter(prefix="/igw", tags=["Internet Gateway"])
@router.get("", response_model=List[StackResponse])
def list_igws():
    """List all Internet Gateway stacks."""
    try:
        region_h = get_region()
        all_stacks = stack_list()
        vipes = [stack for stack in all_stacks if "igw_id" in stack["outputs"]]
        vipes = [stack for stack in vipes if stack["outputs"].get("igw_region")==region_h]
        return [
            StackResponse(status="ok", stack=s["name"], outputs=s["outputs"]) for s in vipes]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
@router.post("", response_model=StackResponse, status_code=201)
def create_igw(req: IgwRequest):
    """Create and attach an Internet Gateway to a VPC."""
    if stack_exists(req.stack):
        raise HTTPException(status_code=409, detail="Internet Gateway already exist")
    region = req.region or get_region()
    if not region:
        raise HTTPException(status_code=422, detail="No region provided and no active region selected")
    try:
        program = create_igw_program(req.name, region, req.vpc_id, req.tags)
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
def get_igw(stack_name: str):
    """Fetch outputs of an existing IGW stack."""
    try:
        outputs = stack_outputs(stack_name)
        return StackResponse(status="ok", stack=stack_name, outputs=outputs)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc))
@router.delete("/{stack_name}")
def delete_igw(stack_name: str):
    """Detach and destroy the Internet Gateway."""
    try:
        stack_destroy(stack_name)
        return {"status": "deleted", "stack": stack_name}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
