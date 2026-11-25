from enum import Enum


class AwsRegion(str, Enum):
    us_east_1 = "us-east-1"
    us_west_1 = "us-west-1"
    eu_central = "eu-central"


_active_region: str = AwsRegion.us_east_1.value


def set_region(region: AwsRegion) -> None:
    global _active_region
    _active_region = region.value


def get_region() -> str | None:
    return _active_region
