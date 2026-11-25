from pydantic import BaseModel, Field
from typing import Dict, Optional
class VpcRequest(BaseModel):
    stack: str = Field(..., description="Pulumi stack name")
    region: Optional[str] = Field(None, description="AWS region — omit to use the pre-selected region")
    name: str = Field(..., description="Resource name prefix")
    cidr_block: str = Field(..., description="VPC CIDR block e.g. 10.0.0.0/16")
    enable_dns_support: bool = True
    enable_dns_hostnames: bool = True
    tags: Dict[str, str] = {}

class VpcPatchRequest(BaseModel):
    stack: Optional[str] = None
    region: Optional[str] = None
    name: Optional[str] = None
    cidr_block: Optional[str] = None
    enable_dns_support: Optional[bool] = None
    enable_dns_hostnames: Optional[bool] = None
    tags: Optional[Dict[str, str]] = None
