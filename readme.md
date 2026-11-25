# MultiCloud VPC Provisioning API

This project provides a **REST API for provisioning AWS VPCs using Pulumi Automation API and FastAPI**.

The API allows users to dynamically create AWS Virtual Private Clouds (VPCs) by sending a request to the service. Infrastructure is defined programmatically using Pulumi and deployed directly from the API.

The infrastructure state is stored in **Amazon S3 instead of Pulumi Cloud**.

---

# Architecture Overview

The application consists of:

* **FastAPI** – API framework for exposing endpoints
* **Pulumi Automation API** – used to provision infrastructure programmatically
* **AWS** – target cloud provider
* **Amazon S3** – backend storage for Pulumi state

Workflow:

User Request → FastAPI API → Pulumi Automation API → AWS VPC Created → State Stored in S3

---

# Requirements

The following tools must be installed before running the project.

## 1. Python

Python 3.9 or later is recommended.

Check your version:

```bash
python --version
```

## 2. Pulumi CLI

Install Pulumi CLI:

https://www.pulumi.com/docs/install/

Verify installation:

```bash
pulumi version
```

## 3. AWS CLI

Install AWS CLI:

https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html

Configure AWS credentials:

```bash
aws configure
```

Provide:

* AWS Access Key
* AWS Secret Access Key
* Default Region

---

# Python Dependencies

Install the required Python libraries.

Create a `requirements.txt` file:

```
fastapi
uvicorn
pulumi
pulumi-aws
python-dotenv
pydantic
slack_sdk
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

# Environment Configuration

Create a `.env` file in the project root.

Example:

```
PULUMI_BACKEND_URL=s3://your-pulumi-state-bucket
AWS_REGION=us-east-1
SLACK_WEBHOOK_URL=<your-slack-incoming-webhook-url>
```

### Variable Description

| Variable           | Description                                      |
| ------------------ | ------------------------------------------------ |
| PULUMI_BACKEND_URL | Pulumi state storage location                    |
| AWS_REGION         | AWS region where infrastructure will be deployed |
| SLACK_WEBHOOK_URL  | Slack webhook for deployment notifications       |

---

# Project Structure

```
project/
│
├── main.py
├── vpc.py
├── slack.py
├── requirements.txt
├── .env
├── .env.example
├── .gitignore
└── README.md
```

Description:

| File             | Purpose                        |
| ---------------- | ------------------------------ |
| main.py          | FastAPI application            |
| vpc.py           | Pulumi VPC module              |
| slack.py         | Slack notification integration |
| requirements.txt | Python dependencies            |
| .env             | Environment variables          |

---

# Configure Pulumi Backend (S3)

Create an S3 bucket to store Pulumi state.

Example:

```bash
aws s3 mb s3://your-pulumi-state-bucket
```

Pulumi will automatically use this bucket when:

```
PULUMI_BACKEND_URL=s3://your-pulumi-state-bucket
```

is set in the environment.

---

# Running the Application

Start the FastAPI server using Uvicorn.

```bash
uvicorn main:app --reload
```

Example output:

```
Uvicorn running on http://127.0.0.1:8000
```

---

# API Documentation

FastAPI automatically generates interactive documentation.

Open in your browser:

Swagger UI

```
http://127.0.0.1:8000/docs
```

Alternative documentation view:

```
http://127.0.0.1:8000/redoc
```

---

# API Endpoint

## Create VPC

Endpoint:

```
POST /vpc
```

Example request:

```json
{
  "name": "demo-vpc",
  "cidr_block": "10.0.0.0/16",
  "stack": "dev",
  "region": "us-east-1",
  "tags": {
    "Environment": "dev",
    "Owner": "platform-te
```
