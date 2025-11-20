# Cloud Deployment Guide

This guide details how to deploy the Master Agent to a cloud environment. The application is containerized and designed to be cloud-agnostic, making it suitable for AWS, Google Cloud Platform (GCP), or Azure.

## Prerequisites

*   **Docker**: For building the image locally or in CI/CD.
*   **Cloud Provider Account**: AWS, GCP, or Azure.
*   **Domain Name**: (Optional) For HTTPS termination.
*   **Gemini API Key**: A valid Google Gemini API key.

## Infrastructure Components

To run this application in production, you will need the following managed services:

1.  **Compute**: A container orchestration service (e.g., AWS ECS Fargate, Google Cloud Run, Kubernetes).
2.  **Data Store**:
    *   **Redis**: Managed Redis (AWS ElastiCache, GCP Memorystore) for rate limiting.
    *   **Database**: (Future) Managed SQL (AWS RDS, Cloud SQL) when replacing the mock data layer.
3.  **Secrets Management**: AWS Secrets Manager, GCP Secret Manager, or Azure Key Vault.
4.  **Logging**: Centralized logging (CloudWatch Logs, Cloud Logging) or an external sink (Splunk, Datadog).

## Environment Configuration

Configure these environment variables in your cloud provider's container definition:

| Variable | Description | Production Value Recommendation |
| :--- | :--- | :--- |
| `GEMINI_API_KEY` | Google Gemini API Key | **Secret** (Inject via Secret Manager) |
| `JWT_SECRET_KEY` | Key for signing JWTs | **Secret** (Inject via Secret Manager) |
| `REDIS_URL` | Connection string for Redis | `redis://<your-managed-redis-host>:6379/0` |
| `TEST_MODE` | Enables mock responses | `false` |
| `ENFORCE_HTTPS` | Forces HTTPS redirects | `true` (if not handled by Load Balancer) |
| `AUDIT_SINKS` | Where to send audit logs | `splunk` or `webhook` (Do not use local file) |
| `AUDIT_WEBHOOK_URL`| URL for audit log collector | Your log ingestion endpoint |

## Deployment Strategies

### Option 1: Google Cloud Run (Recommended for Simplicity)

Cloud Run is a fully managed serverless platform that scales containers automatically.

1.  **Build & Push Image**:
    ```bash
    gcloud builds submit --tag gcr.io/PROJECT-ID/master-agent
    ```

2.  **Deploy**:
    ```bash
    gcloud run deploy master-agent \
      --image gcr.io/PROJECT-ID/master-agent \
      --platform managed \
      --region us-central1 \
      --allow-unauthenticated \
      --set-env-vars="TEST_MODE=false,AUDIT_SINKS=webhook" \
      --set-secrets="GEMINI_API_KEY=gemini-api-key:latest"
    ```

### Option 2: AWS ECS (Fargate)

1.  **Push Image to ECR**: Create an ECR repository and push your Docker image.
2.  **Create Task Definition**:
    *   Add the `master-agent` container.
    *   Set environment variables.
    *   Configure `awslogs` driver for CloudWatch logging.
3.  **Create Service**:
    *   Select **Fargate** launch type.
    *   Attach an Application Load Balancer (ALB) for HTTPS termination.
    *   Ensure the Security Group allows traffic from the ALB on port 8000.

### Option 3: Kubernetes (GKE / EKS / AKS)

1.  **Create a Deployment**:
    ```yaml
    apiVersion: apps/v1
    kind: Deployment
    metadata:
      name: master-agent
    spec:
      replicas: 2
      selector:
        matchLabels:
          app: master-agent
      template:
        metadata:
          labels:
            app: master-agent
        spec:
          containers:
          - name: master-agent
            image: <your-registry>/master-agent:latest
            ports:
            - containerPort: 8000
            env:
            - name: REDIS_URL
              value: "redis://redis-service:6379/0"
            - name: GEMINI_API_KEY
              valueFrom:
                secretKeyRef:
                  name: app-secrets
                  key: gemini-key
    ```

2.  **Expose Service**: Use a `LoadBalancer` service or an Ingress Controller.

## Audit Logging in the Cloud

**Critical**: In a containerized environment, local files are ephemeral. If a container restarts, the `audit.log` file is lost.

**Configuration**:
1.  Set `AUDIT_LOG_TO_FILE=false` to disable local file writing (optional, but saves disk I/O).
2.  Set `AUDIT_LOG_STDOUT=true`. Most cloud providers (AWS CloudWatch, GCP Cloud Logging) automatically capture stdout/stderr.
3.  **Best Practice**: Configure an external sink using `AUDIT_SINKS`.
    *   **Splunk**: Set `SPLUNK_HEC_URL` and `SPLUNK_HEC_TOKEN`.
    *   **Webhook**: Set `AUDIT_WEBHOOK_URL` to forward logs to a sidecar or collector (like Fluent Bit).

## Database Migration

Currently, the application uses mock data (`DataRouter` implementation). For production:

1.  Provision a managed database (e.g., AWS RDS for PostgreSQL).
2.  Update `app/services/data_router.py` to use `SQLAlchemy` or `asyncpg`.
3.  Set connection strings via environment variables (e.g., `DATABASE_URL`).
4.  Run migrations as part of your CD pipeline or an init container.

## Health Checks

Configure your load balancer to use the application's health check endpoint:
*   **Path**: `/health`
*   **Protocol**: HTTP
*   **Success Code**: 200
