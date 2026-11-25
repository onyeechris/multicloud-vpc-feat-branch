from pydantic import BaseModel, Field
from typing import Dict, Optional


class NatGatewayRequest(BaseModel):
    stack: str = Field(..., description="Pulumi stack name")
    region: Optional[str] = Field(None, description="AWS region — omit to use the pre-selected region")
    name: str = Field(..., description="Resource name prefix")
    subnet_id: str = Field(..., description="Public subnet ID to place the NAT Gateway in")
    create_eip: bool = Field(True, description="Auto-create an Elastic IP for the NAT Gateway")
    eip_allocation_id: Optional[str] = Field(
        None, description="Bring your own EIP allocation ID (used when create_eip=false)"
    )
    tags: Dict[str, str] = {}


# class NatGatewayPatchRequest(BaseModel):
#     stack: Optional[str] = None
#     region: Optional[str] = None
#     name: Optional[str] = None
#     subnet_id: Optional[str] = None
#     create_eip: Optional[bool] = None
#     eip_allocation_id: Optional[str] = None
#     tags: Optional[Dict[str, str]] = None
