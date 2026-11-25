from typing import Dict
import pulumi
import pulumi_aws as aws


def create_igw_program(name: str, region: str, vpc_id: str, tags: Dict[str, str]):
    def program():
        base_tags = {"ManagedBy": "Pulumi", **tags, "Name": f"{name}-igw"}
        igw = aws.ec2.InternetGateway(
            f"{name}-igw",
            vpc_id=vpc_id,
            tags=base_tags,
        )
        pulumi.export("igw_id", igw.id)
        pulumi.export("vpc_id", vpc_id)
        pulumi.export("igw_region", region)
        pulumi.export("name", name)

    return program
