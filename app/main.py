import os
from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI

from app.routes.region import router as region_router
from app.routes.vpc import router as vpc_router
from app.routes.subnet import router as subnet_router
from app.routes.igw import router as igw_router
from app.routes.route_table import router as route_table_router
from app.routes.nat_gateway import router as nat_gateway_router
from app.routes.route import router as route_router



# Pulumi state backend — S3 takes priority; fall back to Pulumi Cloud token.
_backend_url = os.getenv("PULUMI_BACKEND_URL")
_pulumi_token = os.getenv("PULUMI_ACCESS_TOKEN")

if _backend_url:
    os.environ["PULUMI_BACKEND_URL"] = _backend_url
elif _pulumi_token:
    os.environ["PULUMI_ACCESS_TOKEN"] = _pulumi_token
else:
    raise RuntimeError(
        "No Pulumi backend configured. Set either PULUMI_BACKEND_URL (S3) "
        "or PULUMI_ACCESS_TOKEN (Pulumi Cloud) in your .env file."
    )

# Required when using a self-hosted backend (S3).
_passphrase = os.getenv("PULUMI_CONFIG_PASSPHRASE")
if _passphrase is None:
    raise RuntimeError(
        "PULUMI_CONFIG_PASSPHRASE is not set. Add it to your .env file. "
        "Set to empty string to disable passphrase encryption."
    )
os.environ["PULUMI_CONFIG_PASSPHRASE"] = _passphrase

app = FastAPI(
    title="MultiCloud Edge — AWS Networking Service",
    description=(
        "Microservice for provisioning AWS networking resources via the Pulumi Automation API. "
        "Each resource type (VPC, Subnet, IGW, Route Table, NAT Gateway, Route) is an "
        "independent Pulumi stack with full CRUD endpoints."
    ),
    version="2.0.0",
)

app.include_router(region_router)
app.include_router(vpc_router)
app.include_router(subnet_router)
app.include_router(igw_router)
app.include_router(route_table_router)
app.include_router(nat_gateway_router)
app.include_router(route_router)


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok", "service": "aws-networking"}
