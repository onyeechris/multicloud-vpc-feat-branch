from pydantic import BaseModel, Field
from typing import Dict, List, Optional


class RouteTableRequest(BaseModel):
    stack: str = Field(..., description="Pulumi stack name")
    region: Optional[str] = Field(None, description="AWS region — omit to use the pre-selected region")
    name: str = Field(..., description="Resource name prefix")
    vpc_id: str = Field(..., description="VPC ID")
    subnet_ids: List[str] = Field(
        default=[],
        description="Subnet IDs to associate with this route table"
    )
    tags: Dict[str, str] = {}


class RouteTablePatchRequest(BaseModel):
    stack: Optional[str] = None
    region: Optional[str] = None
    name: Optional[str] = None
    vpc_id: Optional[str] = None
    subnet_ids: Optional[List[str]] = None
    tags: Optional[Dict[str, str]] = None
