from typing import Dict, List
import pulumi
import pulumi_aws as aws


def create_route_table_program(
    name: str,
    vpc_id: str,
    region: str,
    subnet_ids: List[str],
    tags: Dict[str, str],
):
    def program():
        base_tags = {"ManagedBy": "Pulumi", **tags, "Name": f"{name}-rt"}
        rt = aws.ec2.RouteTable(
            f"{name}-rt",
            vpc_id=vpc_id,
            tags=base_tags
        )

        for i, subnet_id in enumerate(subnet_ids):
            aws.ec2.RouteTableAssociation(
                f"{name}-rta-{i + 1}",
                subnet_id=subnet_id,
                route_table_id=rt.id,
            )

        pulumi.export("route_table_id", rt.id)
        pulumi.export("vpc_id", vpc_id)
        pulumi.export("associated_subnet_ids", subnet_ids)
        pulumi.export("rt_region", region)
        pulumi.export("name", name)

    return program
