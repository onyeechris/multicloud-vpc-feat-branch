# MultiCloud AWS Networking API

FastAPI + Pulumi Automation API service that provisions AWS networking: VPCs, subnets, internet gateways, NAT gateways, route tables and routes.

Each resource type (for example a VPC, a subnet or a VM) is managed as its **own Pulumi stack**, created, updated and destroyed through REST endpoints. The service drives Pulumi through its Automation API, so no `pulumi up` is ever run by hand.

> This is one of four related services. See [Related repositories](#related-repositories).

## Contents

- [How it works](#how-it-works) · [Authentication](#authentication) · [Quick start](#quick-start) · [Configuration](#configuration)
- [API reference](#api-reference) · [Typical workflow](#typical-workflow) · [Docker](#docker) · [Project layout](#project-layout)
- [Security notes](#security-notes) · [Troubleshooting](#troubleshooting)

## How it works

```
client --HTTPS + JWT--> FastAPI --> Pulumi Automation API --> AWS resources
                                          |
                                          +--> stack state in an S3 bucket
```

- **Resources covered:** VPC, Subnet, Internet Gateway, NAT Gateway (with Elastic IP), Route Table, Route.
- **One stack per resource.** You choose the stack name. Dependent resources reference earlier stacks by name, and the service resolves their outputs for you.
- **POST** creates a stack and returns 409 if it already exists. If creation fails part-way, the half-built stack is destroyed so the name can be reused. **PATCH** changes only the fields you send. **DELETE** destroys the stack's resources and removes its state.
- Stack state lives in `s3://<bucket>/.pulumi/stacks/multicloud-networking/<stack>.json`, and the service lists stacks by reading that prefix directly.
- The active region is held in process memory and chosen with `POST /region/{region}`.

## Authentication

Every endpoint except the health checks requires a JWT bearer token:

```
Authorization: Bearer <token>
```

The service **only validates** tokens. It does not issue them, so they come from whatever identity service you run. Requirements:

| Item | Value |
|---|---|
| Algorithm | `HS256` |
| Signing key | the `jwt_secret_key` environment variable, shared with the issuer |
| Required claims | `sub` (an integer user id) and `role` |

A missing, malformed, wrongly signed or incomplete token gets `401`. If `jwt_secret_key` is not set, protected routes return `500` instead of silently allowing access.

Mint a token for local testing:

```bash
python -c "from jose import jwt; print(jwt.encode({'sub': '1', 'role': 'admin'}, 'your-jwt-secret', algorithm='HS256'))"
export TOKEN=<paste the output>
```

Auth is applied where routers are mounted in `app/main.py` (`dependencies=[Depends(get_current_user)]`), so any new router added there is protected automatically. The `role` claim is read but not yet used for authorization, so every valid token has full access.

## Quick start

Prerequisites: Python 3.12+, the [Pulumi CLI](https://www.pulumi.com/docs/install/), and AWS credentials with permission to create the resources above.

```bash
git clone <this repo> && cd <this repo>
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then edit the values
uvicorn main:app --reload
```

- Interactive docs: http://localhost:8000/docs (use **Authorize** to paste your token)
- Health check: `curl http://localhost:8000/health`

The first time you use the service, create the state container (an S3 bucket) and put its URL in `PULUMI_BACKEND_URL`. The app refuses to start if neither `PULUMI_BACKEND_URL` nor `PULUMI_ACCESS_TOKEN` is set, or if `PULUMI_CONFIG_PASSPHRASE` is missing.

## Configuration

All settings are environment variables, loaded from `.env`. Never commit `.env`.

| Variable | Required | Purpose |
|---|---|---|
| `PULUMI_BACKEND_URL` | one of these two | State backend, e.g. `s3://my-pulumi-state-bucket` |
| `PULUMI_ACCESS_TOKEN` | one of these two | Pulumi Cloud token, used if no backend URL is set |
| `PULUMI_CONFIG_PASSPHRASE` | yes | Encrypts secrets inside stack state. Set once and do not change it for existing stacks |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | yes | Credentials used to provision resources and read the state bucket |
| `AWS_DEFAULT_REGION` | yes | Default region (e.g. `us-east-1`) |
| `jwt_secret_key` | yes | HS256 key used to validate API tokens. Use a long random value |
| `SLACK_WEBHOOK_URL` | no | Incoming webhook for deployment notifications |

## API reference

All paths below require the bearer token unless marked otherwise. Live, always-current documentation is served at `/docs` (Swagger) and `/redoc`.

| Method | Path | Description |
|---|---|---|
| POST / GET | `/region/{region}`, `/region` | Set / read the active AWS region used by all stack operations |
| GET, POST | `/vpc` | List VPC stacks / create a VPC |
| GET, PATCH, DELETE | `/vpc/{stack_name}` | Read outputs / partially update / destroy |
| GET, POST | `/subnet` | List subnet stacks / create one or many subnets (public or private) |
| GET, PATCH, DELETE | `/subnet/{stack_name}` | Read / update / destroy |
| GET, POST | `/igw` | List / create and attach an Internet Gateway |
| GET, DELETE | `/igw/{stack_name}` | Read / detach and destroy |
| GET, POST | `/nat-gateway` | List / create a NAT Gateway (auto-creates or accepts an Elastic IP) |
| GET, DELETE | `/nat-gateway/{stack_name}` | Read / destroy |
| GET, POST | `/route-table` | List / create a route table, optionally associating subnets |
| GET, PATCH, DELETE | `/route-table/{stack_name}` | Read / update / destroy |
| GET, POST | `/route` | List / add routes to a route table |
| GET, PATCH, DELETE | `/route/{stack_name}` | Read / update / remove the routes the stack manages |
| GET | `/health` | Liveness check (no auth) |

Example:

```bash
curl -X POST http://localhost:8000/vpc \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"stack": "dev-vpc-us-east-1", "name": "dev-vpc", "cidr_block": "10.0.0.0/16", "region": "us-east-1"}'
```

Errors follow FastAPI's `{"detail": ...}` shape. Typical codes: `401` bad token, `404` unknown stack, `409` stack already exists, `422` validation error, `502` the cloud provider rejected the request.

More detail: [`docs/API_GUIDE.md`](docs/API_GUIDE.md) (Detailed request/response examples for every networking endpoint).

## Typical workflow

Create resources in dependency order, since each step uses outputs from the one before:

```
1. POST /region/us-east-1
2. POST /vpc                      -> vpc_id
3. POST /subnet (public/private)  -> subnet_ids
4. POST /igw                      -> igw_id            (needs vpc_id)
5. POST /nat-gateway              -> nat_gateway_id    (needs a public subnet_id)
6. POST /route-table              -> route_table_id    (public and private)
7. POST /route                    -> 0.0.0.0/0 via IGW (public) or NAT (private)
```

A consistent stack naming pattern keeps things findable, e.g. `{env}-{resource}-{region}`.

## Docker

```bash
docker build -t multicloud-vpc .
docker run -p 8000:8000 --env-file .env multicloud-vpc
```

The image is based on `pulumi/pulumi-python-3.12` and listens on port 8000. `entrypoint.sh` sets public DNS resolvers and starts uvicorn with a long keep-alive timeout, because stack operations can take minutes.

The included workflow `.github/workflows/cicd.yaml` is an example that builds the image and pushes it to Amazon ECR. It runs only on manual dispatch and needs the repository secrets `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION` and `ECR_REPOSITORY`.

## Project layout

```
main.py                  entry point (uvicorn main:app)
Pulumi.yaml              Pulumi project definition
app/
  main.py                FastAPI app, CORS, auth wiring, backend checks
  routes/                one router per resource (HTTP layer)
  models/                Pydantic request and response models
  pulumi_programs/       Pulumi programs that define the cloud resources
  utils/
    auth.py              JWT bearer validation
    stack.py             create / update / destroy / list stacks
    region_state.py   active region state
    slack.py             optional notifications
docs/                    detailed guide
```

## Security notes

- Keep `jwt_secret_key`, cloud credentials and `PULUMI_CONFIG_PASSPHRASE` in a secret manager or in environment variables. Never put them in the repo, and rotate any that were ever committed.
- The service holds credentials that can create and destroy cloud infrastructure. Run it on a private network, put it behind TLS, and restrict who can obtain tokens.
- CORS currently allows only `http://localhost:3000`. Change `allow_origins` in `app/main.py` for your front end.
- Private keys returned by `/key-pair/{stack}/download` are sensitive. Treat that endpoint accordingly.
- Authorization is all-or-nothing today. Enforce the `role` claim if you need least-privilege access.

## Troubleshooting

- **App exits at startup:** a required variable (`PULUMI_BACKEND_URL` or `PULUMI_ACCESS_TOKEN`, and `PULUMI_CONFIG_PASSPHRASE`) is missing.
- **401 on every call:** the token is signed with a different key than `jwt_secret_key`, or lacks `sub` / `role`.
- **500 "Auth is not configured":** `jwt_secret_key` is not set in the service's environment.
- **A request hangs for minutes:** stack operations are synchronous and cloud provisioning is slow. This is expected for NAT gateways, VMs and similar resources.

## Related repositories

[multicloud-eks-ec2-branch](https://github.com/onyeechris/multicloud-eks-ec2-branch) (EC2 compute that consumes the subnets created here), [multicloud-vnet-branch](https://github.com/onyeechris/multicloud-vnet-branch) (Azure equivalent), [multicloud-global-lb-branch](https://github.com/onyeechris/multicloud-global-lb-branch) (AWS-Azure VPN and load balancer).
