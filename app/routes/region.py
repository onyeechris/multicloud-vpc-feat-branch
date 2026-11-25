from fastapi import APIRouter, HTTPException

from app.utils.region_state import AwsRegion, get_region, set_region

router = APIRouter(prefix="/region", tags=["Region"])


@router.post("/{region}", status_code=200)
async def select_region(region: AwsRegion):
    """Pre-select the active AWS region used by all stack operations."""
    set_region(region)
    return {"active_region": region.value}


@router.get("")
async def current_region():
    """Return the currently active AWS region."""
    r = get_region()
    if r is None:
        raise HTTPException(status_code=404, detail="No region selected yet. Call POST /region/{region} first.")
    return {"active_region": r}
