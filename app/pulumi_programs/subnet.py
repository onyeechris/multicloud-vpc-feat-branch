from typing import Dict, List
import pulumi
import pulumi_aws as aws
from pulumi_aws import get_region

from app.models.subnet import SubnetConfig


def create_subnet_program(
    name: str,
    vpc_id: str,
    region: str,
    subnets: List[SubnetConfig],
    tags: Dict[str, str],
):
    def program():
        base_tags = {"ManagedBy": "Pulumi", **tags}
        created = []
        # resolved_region = get_region()
        for i, s in enumerate(subnets):
            subnet_name = s.name or f"{name}-subnet-{i + 1}"
            subnet = aws.ec2.Subnet(
                subnet_name,
                vpc_id=vpc_id,
                cidr_block=s.cidr_block,
                availability_zone=s.availability_zone,
                map_public_ip_on_launch=s.map_public_ip_on_launch,
                tags={**base_tags, "Name": subnet_name},
            )
            created.append(subnet)

        # pulumi.export("subnet_ids", [s.id for s in created])
        pulumi.export("subnet_count", len(created))
        pulumi.export("vpc_id", vpc_id)
        pulumi.export("name", name)
        pulumi.export("sub_region", region)

        subnet_configs = pulumi.Output.all(*[s.id for s in created]).apply(
            lambda ids: [
                {
                    "cidr_block": s.cidr_block,
                    "availability_zone": s.availability_zone,
                    "map_public_ip_on_launch": s.map_public_ip_on_launch,
                    "name": s.name,
                    "subnet_id": subnet_id,
                }
                for s, subnet_id in zip(subnets, ids)
            ]
        )
        pulumi.export("subnet_configs", subnet_configs)

    return program
