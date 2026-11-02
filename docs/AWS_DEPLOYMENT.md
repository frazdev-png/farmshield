# FarmShield AI - AWS Deployment Architecture & Readiness Guide

## Overview
FarmShield AI is engineered with an AWS-cloud-native, decoupled microservices architecture designed for resilience, horizontal scalability, and high-availability agricultural intelligence.

```
                  +-----------------------------------+
                  |        Amazon Route 53 (DNS)      |
                  +-----------------+-----------------+
                                    |
                    +---------------+---------------+
                    |                               |
                    v                               v
        +-----------------------+       +-----------------------+
        |   Frontend CloudFront |       | Application Load      |
        |   + S3 Static Hosting |       | Balancer (ALB)        |
        +-----------------------+       +-----------+-----------+
                                                    |
                                                    v
                                        +-----------------------+
                                        |  AWS ECS Fargate /    |
                                        |  FastAPI Backend      |
                                        |  (Auto-scaling)       |
                                        +-----------+-----------+
                                                    |
                                                    v
                                        +-----------------------+
                                        | Amazon RDS PostgreSQL |
                                        | (Multi-AZ Deployment) |
                                        +-----------------------+
```

---

## 1. Architecture Components

### Frontend (React + Vite + Tailwind CSS)
- **Hosting**: Amazon S3 (Static Website Hosting) or AWS Amplify.
- **CDN**: Amazon CloudFront distribution for edge caching, SSL/TLS termination, and low-latency delivery across rural and regional edges.
- **Routing**: Single Page Application (SPA) error response rewrite (`404` -> `/index.html` with HTTP 200).

### Backend (FastAPI + Pydantic + SQLAlchemy 2.x)
- **Containerization**: Dockerized OCI container image stored in Amazon Elastic Container Registry (ECR).
- **Compute**: AWS ECS with AWS Fargate (serverless containers) or AWS Elastic Beanstalk (Docker).
- **Load Balancing**: AWS Application Load Balancer (ALB) performing TLS termination with AWS Certificate Manager (ACM) and routing `/health`, `/api/*` traffic with target group health checks on `/health`.

### Database Foundation
- **Service**: Amazon RDS for PostgreSQL (v15+ or v16+).
- **Reliability**: Multi-AZ deployment for automated failover, daily automated snapshots, and read replicas.
- **Security**: Hosted in private VPC subnets with security group rules allowing inbound traffic exclusively on port 5432 from ECS backend security groups.
- **Connection Management**: Amazon RDS Proxy for connection pooling under sudden burst traffic.
- **Migrations**: Alembic migrations run as an ECS pre-deployment task or AWS CodePipeline deployment hook.

---

## 2. Environment Variables & Secrets Management

All production secrets and sensitive configuration values must be retrieved from **AWS Secrets Manager** or **AWS Systems Manager (SSM) Parameter Store**. Never store real secrets in Git repositories.

| Parameter Key | Purpose | Recommended AWS Source |
|---|---|---|
| `APP_ENV` | Application environment (`production` / `staging`) | ECS Task Definition Env |
| `DATABASE_URL` | PostgreSQL connection string | AWS Secrets Manager |
| `CORS_ORIGINS` | JSON array of permitted frontend origins | SSM Parameter Store / Secrets Manager |
| `API_V1_PREFIX` | Prefix for v1 routes (`/api/v1`) | ECS Task Definition Env |
| `DEBUG` | FastAPI debug mode (`False` in production) | ECS Task Definition Env |

---

## 3. Containerization Strategy

### Backend Dockerfile
The backend container uses a multi-stage or lean non-root Python base image:
- Base: `python:3.11-slim` or `python:3.12-slim`
- User: Dedicated unprivileged user (`appuser`)
- Health Check: Docker-native health check querying `http://localhost:8000/health`
- Web Server: `uvicorn` with configurable worker processes (`WEB_CONCURRENCY`)

### Frontend Build
- Production bundle compiled with `npm run build` producing static assets in `dist/`.
- Ready for automated sync to S3 via `aws s3 sync dist/ s3://<bucket-name> --delete` followed by CloudFront cache invalidation.

---

## 4. Health Checks and Observability
- **ALB Health Check Path**: `/health` (returns HTTP 200 `{"status": "healthy"}`)
- **Container Health Check Path**: `GET /health` or `GET /api/v1/health`
- **Logging**: Application logs output to `stdout`/`stderr` in JSON format, ingested by AWS CloudWatch Logs.
- **Metrics**: CloudWatch Container Insights monitoring CPU/Memory utilization and error rates for ECS auto-scaling triggers.

---

## 5. Security & Network Architecture
- **VPC Subnets**:
  - **Public Subnet**: ALB and NAT Gateway.
  - **Private Application Subnet**: ECS Fargate tasks running FastAPI backend.
  - **Private Database Subnet**: RDS PostgreSQL instances (no direct internet route).
- **IAM Principle of Least Privilege**: Dedicated Task Execution Role for pulling ECR images and writing to CloudWatch, plus Task Role for scoped access to AWS services.

