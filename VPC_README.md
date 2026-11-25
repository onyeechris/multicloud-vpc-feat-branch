# MultiCloud Edge — AWS Networking Microservice

A **FastAPI + Pulumi Automation API** microservice that provisions AWS networking
infrastructure on demand. Each resource type is an independent Pulumi stack with its
own full CRUD API. Users interact via REST — no AWS Console, no manual Pulumi commands.

This service is one microservice in the larger **MultiCloud Edge** platform, which lets
teams provision cloud resources across AWS, Azure, and GCP from a single API surface.

---

## Architecture

```
Client (REST)
     │
     ▼
FastAPI  (main.py)
     │
     ├── /vpc           → VPC stack
     ├── /subnet        → Subnet stack (single or multi-AZ)
     ├── /igw           → Internet Gateway stack
     ├── /route-table   → Route Table + subnet associations stack
     ├── /nat-gateway   → NAT Gateway + Elastic IP stack
     └── /route         → Route entries stack
             │
             ▼
     Pulumi Automation API
             │
             ▼
     AWS (EC2 networking resources)
             │
     State stored in S3
```

Each resource lives in its own Pulumi stack. Stacks are independent — you can
create, update, or destroy one without touching the others.

---

## Project Structure

```
multi-cloudEge-backend/
├── main.py                              # Uvicorn entry point
├── Pulumi.yaml                          # Pulumi project metadata
├── requirements.txt                     # Python dependencies
├── .env.example                         # Environment variable template
├── .gitignore
├── README.md
│
└── app/
    ├── main.py                          # FastAPI app + router registration
    │
    ├── models/
    │   ├── common.py                    # Shared StackResponse model
    │   ├── vpc.py
    │   ├── subnet.py
    │   ├── igw.py
    │   ├── route_table.py
    │   ├── nat_gateway.py
    │   └── route.py
    │
    ├── routes/
    │   ├── vpc.py                       # POST · GET · PUT · DELETE /vpc
    │   ├── subnet.py                    # POST · GET · PUT · DELETE /subnet
    │   ├── igw.py                       # POST · GET · PUT · DELETE /igw
    │   ├── route_table.py               # POST · GET · PUT · DELETE /route-table
    │   ├── nat_gateway.py               # POST · GET · PUT · DELETE /nat-gateway
    │   └── route.py                     # POST · GET · PUT · DELETE /route
    │
    ├── pulumi_programs/
    │   ├── vpc.py                       # Pulumi inline program — VPC
    │   ├── subnet.py                    # Pulumi inline program — Subnets
    │   ├── igw.py                       # Pulumi inline program — IGW
    │   ├── route_table.py               # Pulumi inline program — Route Table
    │   ├── nat_gateway.py               # Pulumi inline program — NAT Gateway
    │   └── route.py                     # Pulumi inline program — Routes
    │
    └── utils/
        ├── stack.py                     # Shared stack_up / stack_outputs / stack_destroy
        └── slack.py                     # Optional Slack notifications
```

---

## AWS Resources Per Stack

| Stack | Resources Created |
|---|---|
| `/vpc` | VPC (DNS enabled) |
| `/subnet` | 1–N Subnets across 1–N AZs |
| `/igw` | Internet Gateway, attached to VPC |
| `/route-table` | Route Table, Route Table Associations |
| `/nat-gateway` | Elastic IP, NAT Gateway |
| `/route` | Route entries added to an existing Route Table |

---

## Prerequisites

| Tool | Minimum Version |
|---|---|
| Python | 3.11+ |
| Pulumi CLI | 3.x |
| AWS CLI | 2.x |

---

## Setup

### 1. Clone and create virtualenv

```bash
git clone <repo-url>
cd multi-cloudEge-backend

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your values
```

Required variables:

| Variable | Description |
|---|---|
| `PULUMI_BACKEND_URL` | S3 state bucket e.g. `s3://my-bucket` |
| `PULUMI_CONFIG_PASSPHRASE` | Passphrase for stack secret encryption (set to empty string to disable) |
| `AWS_ACCESS_KEY_ID` | AWS access key |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key |
| `AWS_DEFAULT_REGION` | Default AWS region |

Optional:

| Variable | Description |
|---|---|
| `PULUMI_ACCESS_TOKEN` | Use instead of `PULUMI_BACKEND_URL` to store state in Pulumi Cloud |
| `SLACK_WEBHOOK_URL` | Slack notifications (see Slack section below) |

### 3. Create an S3 state bucket (first time only)

```bash
aws s3 mb s3://my-pulumi-state-bucket --region us-east-1
```

Then set in `.env`:
```
PULUMI_BACKEND_URL=s3://my-pulumi-state-bucket
```

### 4. Start the server

Always use `python -m uvicorn` (not the bare `uvicorn` command) so the virtualenv
packages are used:

```bash
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Interactive API docs: http://localhost:8000/docs

---

## API Endpoints

Every resource follows the same pattern:

| Method | Path | Action |
|---|---|---|
| `POST` | `/{resource}` | Create a new stack |
| `GET` | `/{resource}/{stack_name}` | Fetch current outputs |
| `PUT` | `/{resource}/{stack_name}` | Update (Pulumi diffs + applies changes) |
| `DELETE` | `/{resource}/{stack_name}` | Destroy all resources in the stack |

---

### POST `/vpc` — Create a VPC

```json
{
  "stack": "prod-vpc",
  "region": "us-east-1",
  "name": "prod",
  "cidr_block": "10.0.0.0/16",
  "enable_dns_support": true,
  "enable_dns_hostnames": true,
  "tags": { "Environment": "prod" }
}
```

**Response outputs:** `vpc_id`, `vpc_cidr`, `name`

---

### POST `/subnet` — Create subnets

The entire behavior is driven by the `subnets` array. The number of entries controls
single vs. multiple subnets; the `map_public_ip_on_launch` flag on each entry controls
public vs. private. All combinations can be mixed in one request.

#### Single subnet

Pass exactly one entry in `subnets`:

```json
{
  "stack": "dev-subnet",
  "region": "us-east-1",
  "name": "dev",
  "vpc_id": "vpc-0abc123",
  "subnets": [
    {
      "cidr_block": "10.0.1.0/24",
      "availability_zone": "us-east-1a",
      "map_public_ip_on_launch": false,
      "name": "dev-subnet"
    }
  ]
}
```

#### Multiple subnets

Pass two or more entries — all subnets are created in the same Pulumi stack:

```json
{
  "stack": "dev-subnets",
  "region": "us-east-1",
  "name": "dev",
  "vpc_id": "vpc-0abc123",
  "subnets": [
    { "cidr_block": "10.0.1.0/24", "availability_zone": "us-east-1a" },
    { "cidr_block": "10.0.2.0/24", "availability_zone": "us-east-1b" },
    { "cidr_block": "10.0.3.0/24", "availability_zone": "us-east-1c" }
  ]
}
```

#### Private subnet

Set `map_public_ip_on_launch: false` (this is the **default** if the field is omitted).
Instances launched here will not receive a public IP automatically:

```json
{
  "cidr_block": "10.0.10.0/24",
  "availability_zone": "us-east-1a",
  "map_public_ip_on_launch": false,
  "name": "prod-private-1a"
}
```

#### Public subnet

Set `map_public_ip_on_launch: true`. Instances launched here will auto-receive a public IP:

```json
{
  "cidr_block": "10.0.20.0/24",
  "availability_zone": "us-east-1a",
  "map_public_ip_on_launch": true,
  "name": "prod-public-1a"
}
```

> **Note:** `map_public_ip_on_launch: true` only sets the auto-assign flag. For the subnet
> to route internet traffic you also need an Internet Gateway (`POST /igw`) and a route
> table with `0.0.0.0/0 → igw` (`POST /route`).

#### Mixed public + private in one stack

```json
{
  "stack": "prod-subnets",
  "region": "us-east-1",
  "name": "prod",
  "vpc_id": "vpc-0abc123",
  "subnets": [
    { "cidr_block": "10.0.1.0/24",  "availability_zone": "us-east-1a", "map_public_ip_on_launch": true,  "name": "prod-public-1a" },
    { "cidr_block": "10.0.2.0/24",  "availability_zone": "us-east-1b", "map_public_ip_on_launch": true,  "name": "prod-public-1b" },
    { "cidr_block": "10.0.10.0/24", "availability_zone": "us-east-1a", "map_public_ip_on_launch": false, "name": "prod-private-1a" },
    { "cidr_block": "10.0.11.0/24", "availability_zone": "us-east-1b", "map_public_ip_on_launch": false, "name": "prod-private-1b" }
  ],
  "tags": { "Environment": "prod" }
}
```

If `name` is omitted on an entry, the program auto-generates it as `{name}-subnet-1`,
`{name}-subnet-2`, etc.

**Response outputs:** `subnet_ids`, `subnet_count`, `vpc_id`

---

### POST `/igw` — Create an Internet Gateway

```json
{
  "stack": "prod-igw",
  "region": "us-east-1",
  "name": "prod",
  "vpc_id": "vpc-0abc123",
  "tags": { "Environment": "prod" }
}
```

**Response outputs:** `igw_id`, `vpc_id`, `name`

---

### POST `/route-table` — Create a route table

```json
{
  "stack": "prod-public-rt",
  "region": "us-east-1",
  "name": "prod-public",
  "vpc_id": "vpc-0abc123",
  "subnet_ids": ["subnet-aaa", "subnet-bbb"],
  "tags": { "Tier": "public" }
}
```

**Response outputs:** `route_table_id`, `vpc_id`, `associated_subnet_ids`, `name`

---

### POST `/nat-gateway` — Create a NAT Gateway

```json
{
  "stack": "prod-nat",
  "region": "us-east-1",
  "name": "prod",
  "subnet_id": "subnet-aaa",
  "create_eip": true,
  "tags": { "Environment": "prod" }
}
```

Set `create_eip: false` and provide `eip_allocation_id` to bring your own Elastic IP.

**Response outputs:** `nat_gateway_id`, `eip_public_ip`, `subnet_id`, `name`

---

### POST `/route` — Add routes to a route table

```json
{
  "stack": "prod-public-routes",
  "region": "us-east-1",
  "name": "prod-public",
  "route_table_id": "rtb-111",
  "routes": [
    { "destination_cidr": "0.0.0.0/0", "gateway_id": "igw-0def456" }
  ],
  "tags": {}
}
```

For private route tables pointing to NAT:
```json
{
  "routes": [
    { "destination_cidr": "0.0.0.0/0", "nat_gateway_id": "nat-0abc789" }
  ]
}
```

**Response outputs:** `route_table_id`, `route_count`, `routes`

---

## Typical Provisioning Order

Resources must be created in dependency order since each step uses IDs from the previous:

```
1. POST /vpc
        │  vpc_id
        ▼
2. POST /subnet  (public)       POST /subnet  (private)
        │  subnet_ids                  │  subnet_ids
        ▼                              │
3. POST /igw                    POST /nat-gateway ◄── uses a public subnet_id
        │  igw_id                      │  nat_gateway_id
        ▼                              ▼
4. POST /route-table (public)   POST /route-table (private)
        │  route_table_id              │  route_table_id
        ▼                              ▼
5. POST /route (→ IGW)          POST /route (→ NAT GW)
```

---

## Stack Naming Convention

Use a consistent naming pattern to keep stacks identifiable:

```
{env}-{resource}-{region}

prod-vpc-us-east-1
prod-public-subnets-us-east-1
prod-igw-us-east-1
prod-public-rt-us-east-1
prod-nat-us-east-1
prod-public-routes-us-east-1
```

---

## How Pulumi State Works

Each stack has a state file in S3 that tracks the AWS resources it manages.

- **POST** and **PUT** both call `stack.up()` — Pulumi diffs current vs desired state
  and applies only what changed. Re-running is safe and idempotent.
- **DELETE** calls `stack.destroy()` then removes the stack record from S3.
- Stacks are fully isolated — destroying one never touches another.

---

## Slack Notifications (disabled by default)

Slack is not active in the current code. To enable it:

**1.** Create an Incoming Webhook at https://api.slack.com/messaging/webhooks

**2.** Add to `.env`:
```
SLACK_WEBHOOK_URL=<your-slack-incoming-webhook-url>.../B.../xxx
```

**3.** In any route file (e.g. `app/routes/vpc.py`), add at the top:
```python
from app.utils.slack import send_slack_message
```

Then call it after a successful `stack_up(...)`:
```python
send_slack_message(f":white_check_mark: *{req.stack}* created — VPC: {outputs.get('vpc_id')}")
```

The `send_slack_message` function silently skips if the webhook URL is missing.

---

## Running in Production

```bash
pip install gunicorn
gunicorn main:app -k uvicorn.workers.UvicornWorker -w 2 --bind 0.0.0.0:8000
```

---

## Extending to Other Cloud Providers

To add Azure or GCP networking:

1. Add models in `app/models/`
2. Add a Pulumi program in `app/pulumi_programs/`
3. Add a router in `app/routes/` and register it in `app/main.py`

No existing files need to change.

## Dockerfile usage

Uses python:3.12-slim to match the project's Python version                                                                                                                                         
Installs dependencies from requirements.txt
Copies Pulumi.yaml, main.py, and the app/ package                                                                                                                                                   
Exposes port 8000 and runs uvicorn                                                                                                                                                                  
   
To build and run:                                                                                                                                                                                     
docker build -t multicloud-demo-backend .                       
docker run -p 8000:8000 --env-file .env multicloud-demo-backend                                                                                                                                       
                                                                  
The app requires these env vars at runtime (via --env-file .env):
PULUMI_ACCESS_TOKEN or PULUMI_BACKEND_URL                                                                                                                                                       PULUMI_CONFIG_PASSPHRASE                                                                                                                                                                            
AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION  
