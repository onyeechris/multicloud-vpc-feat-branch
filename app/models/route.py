from pydantic import BaseModel, Field, model_validator
from typing import Dict, List, Optional


class RouteEntry(BaseModel):
    destination_cidr: str = Field(..., description="Destination CIDR e.g. 0.0.0.0/0")
    gateway_id: Optional[str] = Field(None, description="Internet Gateway ID")
    nat_gateway_id: Optional[str] = Field(None, description="NAT Gateway ID")

    @model_validator(mode="after")
    def validate_target(self) -> "RouteEntry":
        if not self.gateway_id and not self.nat_gateway_id:
            raise ValueError("Each route must specify either gateway_id, nat_gateway_id or vgw_stack")
        return self


class RouteRequest(BaseModel):
    stack: str = Field(..., description="Pulumi stack name")
    region: Optional[str] = Field(None, description="AWS region — omit to use the pre-selected region")
    name: str = Field(..., description="Resource name prefix")
    route_table_id: str = Field(..., description="Route table to add routes to")
    routes: Optional[List[RouteEntry]] = Field(None)
    vgw_stack: Optional[str] = Field(default=None, description="Virtual Private Gateway IDs to enable route propagation for")
    tags: Dict[str, str] = {}


class RoutePatchRequest(BaseModel):
    stack: Optional[str] = None
    region: Optional[str] = None
    name: Optional[str] = None
    route_table_id: Optional[str] = None
    routes: Optional[List[RouteEntry]] = None
    vgw_stack: Optional[str] = None
    tags: Optional[Dict[str, str]] = None
