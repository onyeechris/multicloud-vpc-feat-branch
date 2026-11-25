from pydantic import BaseModel, Field
from typing import Dict, Optional


class IgwRequest(BaseModel):
    stack: str = Field(..., description="Pulumi stack name")
    region: Optional[str] = Field(None, description="AWS region — omit to use the pre-selected region")
    name: str = Field(..., description="Resource name prefix")
    vpc_id: str = Field(..., description="VPC ID to attach the IGW to")
    tags: Dict[str, str] = {}

