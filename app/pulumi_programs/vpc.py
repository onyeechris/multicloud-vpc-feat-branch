from typing import Dict
import pulumi
import pulumi_aws as aws


def create_vpc_program(
    name: str,
    cidr_block: str,
    region: str,
    enable_dns_support: bool,
    enable_dns_hostnames: bool,
    tags: Dict[str, str],
):
    def program():
        base_tags = {"ManagedBy": "Pulumi", **tags, "Name": name}
        vpc = aws.ec2.Vpc(
            f"{name}-vpc",
            cidr_block=cidr_block,
            enable_dns_support=enable_dns_support,
            enable_dns_hostnames=enable_dns_hostnames,
            tags=base_tags,
        )
        pulumi.export("vpc_id", vpc.id)
        pulumi.export("vpc_cidr", vpc.cidr_block)
        pulumi.export("enable_dns_support", enable_dns_support)
        pulumi.export("enable_dns_hostnames", enable_dns_hostnames)
        pulumi.export("vpc_region", region)
        pulumi.export("name", name)

    return program
