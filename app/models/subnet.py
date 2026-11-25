from pydantic import BaseModel, Field
from typing import Dict, List, Optional


class SubnetConfig(BaseModel):
    cidr_block: str
    availability_zone: str
    map_public_ip_on_launch: bool = False
    name: str = ""


class SubnetRequest(BaseModel):
    stack: str = Field(..., description="Pulumi stack name")
    region: Optional[str] = Field(None, description="AWS region — omit to use the pre-selected region")
    name: str = Field(..., description="Resource name prefix")
    vpc_id: str = Field(..., description="Target VPC ID")
    subnets: List[SubnetConfig] = Field(
        ..., min_length=1,
        description="One entry = single subnet. Multiple entries = multi-subnet stack."
    )
    tags: Dict[str, str] = {}


class SubnetPatchRequest(BaseModel):
    stack: Optional[str] = None
    region: Optional[str] = None
    name: Optional[str] = None
    vpc_id: Optional[str] = None
    subnets: Optional[List[SubnetConfig]] = None
    tags: Optional[Dict[str, str]] = None
