from typing import Dict, Optional
import pulumi
import pulumi_aws as aws


def create_nat_gateway_program(
    name: str,
    subnet_id: str,
    region: str,
    create_eip: bool,
    eip_allocation_id: Optional[str],
    tags: Dict[str, str],
):
    def program():
        base_tags = {"ManagedBy": "Pulumi", **tags}

        if create_eip and not eip_allocation_id:
            eip = aws.ec2.Eip(
                f"{name}-eip",
                domain="vpc",
                tags={**base_tags, "Name": f"{name}-eip"},
            )
            allocation_id = eip.id
            pulumi.export("eip_public_ip", eip.public_ip)
        else:
            allocation_id = eip_allocation_id

        nat = aws.ec2.NatGateway(
            f"{name}-nat",
            allocation_id=allocation_id,
            subnet_id=subnet_id,
            tags={**base_tags, "Name": f"{name}-nat"},
        )
        pulumi.export("nat_gateway_id", nat.id)
        pulumi.export("subnet_id", subnet_id)
        pulumi.export("create_eip", create_eip)
        pulumi.export("eip_allocation_id", eip_allocation_id)
        pulumi.export("name", name)
        pulumi.export("nat_region", region)

    return program
