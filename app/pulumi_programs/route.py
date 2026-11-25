from typing import Dict, List, Optional
import pulumi
import pulumi_aws as aws

from app.models.route import RouteEntry


def create_route_program(
    name: str,
    route_table_id: str,
    region: str,
    routes: List[RouteEntry],
    tags: Dict[str, str],
    vgw_id: Optional[List[str]] = None
):
    base_tags = {"ManagedBy": "Pulumi", **tags, "Name": f"{name}-route"}

    def program():
        if routes is not None:
            for r in routes:
                safe_cidr = r.destination_cidr.replace("/", "-").replace(".", "-")
                resource_name = f"{name}-route-{safe_cidr}"

                kwargs: Dict = {
                    "route_table_id": route_table_id,
                    "destination_cidr_block": r.destination_cidr,
                }
                if r.gateway_id is not None:
                    kwargs["gateway_id"] = r.gateway_id
                elif r.nat_gateway_id is not None:
                    kwargs["nat_gateway_id"] = r.nat_gateway_id


                aws.ec2.Route(resource_name, **kwargs)
                pulumi.export("route_count", len(routes))
                pulumi.export("route_configs", [
                    {
                        "destination_cidr": r.destination_cidr,
                        "gateway_id": r.gateway_id,
                        "nat_gateway_id": r.nat_gateway_id,
                    }
                    for r in routes
                ])

        if vgw_id is not None:
            aws.ec2.VpnGatewayRoutePropagation(
            f"{name}-propagation-{vgw_id}",
            route_table_id=route_table_id,
            vpn_gateway_id=vgw_id
            )
        pulumi.export("route_table_id", route_table_id)
        pulumi.export("route_region", region)
        pulumi.export("tags", base_tags)
        pulumi.export("vgw_id", vgw_id or [])

    return program
