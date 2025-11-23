# Cloud Deployment Guide

This guide details how to deploy the Master Agent to a cloud environment. The application is containerized and designed to be cloud-agnostic, making it suitable for AWS, Google Cloud Platform (GCP), or Azure.

## Prerequisites

*   **Docker**: For building the image locally or in CI/CD.
*   **Cloud Provider Account**: AWS, GCP, or Azure.
*   **Domain Name**: (Optional) For HTTPS termination.
*   **Gemini API Key**: A valid Google Gemini API key.
*   **Auth0 Account**: (Recommended) For production authentication.

## Infrastructure Components

To run this application in production, you will need the following managed services:

1.  **Compute**: A container orchestration service (e.g., AWS ECS Fargate, Google Cloud Run, Kubernetes).
2.  **Data Store**:
    *   **Redis**: Managed Redis (AWS ElastiCache, GCP Memorystore) for rate limiting.
    *   **Database**: (Future) Managed SQL (AWS RDS, Cloud SQL) when replacing the mock data layer.
3.  **Secrets Management**: AWS Secrets Manager, GCP Secret Manager, or Azure Key Vault.
4.  **Logging**: Centralized logging (CloudWatch Logs, Cloud Logging) or an external sink (Splunk, Datadog).
5.  **Authentication**: Auth0 (recommended) or custom JWT implementation.

## Environment Configuration

Configure these environment variables in your cloud provider's container definition:

### Authentication & Security
| Variable | Description | Production Value Recommendation |
| :--- | :--- | :--- |
| `AUTH0_DOMAIN` | Auth0 tenant domain | `your-tenant.us.auth0.com` (**Secret** via Secret Manager) |
| `AUTH0_AUDIENCE` | Auth0 API identifier | `https://api.tilli.com/chatbot` (**Secret** via Secret Manager) |
| `ENABLE_AUTH` | Enable authentication | `true` |
| `JWT_SECRET_KEY` | Key for signing local JWTs | **Secret** (Inject via Secret Manager, fallback only) |

### API Keys & External Services
| Variable | Description | Production Value Recommendation |
| :--- | :--- | :--- |
| `GEMINI_API_KEY` | Google Gemini API Key | **Secret** (Inject via Secret Manager) |

### Infrastructure
| Variable | Description | Production Value Recommendation |
| :--- | :--- | :--- |
| `REDIS_URL` | Connection string for Redis | `redis://<your-managed-redis-host>:6379/0` |
| `TEST_MODE` | Enables mock responses | `false` |
| `ENFORCE_HTTPS` | Forces HTTPS redirects | `true` (if not handled by Load Balancer) |

### Audit Logging
| Variable | Description | Production Value Recommendation |
| :--- | :--- | :--- |
| `AUDIT_SINKS` | Where to send audit logs | `splunk` or `webhook` (Do not use local file) |
| `AUDIT_WEBHOOK_URL`| URL for audit log collector | Your log ingestion endpoint |
| `SPLUNK_HEC_URL` | Splunk HEC endpoint | `https://splunk.example.com:8088/services/collector` |
| `SPLUNK_HEC_TOKEN` | Splunk HEC token | **Secret** (Inject via Secret Manager) |

## Deployment Strategies

### Option 1: Google Cloud Run (Recommended for Simplicity)

Cloud Run is a fully managed serverless platform that scales containers automatically.

1.  **Build & Push Image**:
    ```bash
    gcloud builds submit --tag gcr.io/PROJECT-ID/master-agent
    ```

2.  **Deploy with Auth0**:
    ```bash
    gcloud run deploy master-agent \
      --image gcr.io/PROJECT-ID/master-agent \
      --platform managed \
      --region us-central1 \
      --allow-unauthenticated \
      --set-env-vars="TEST_MODE=false,ENABLE_AUTH=true,AUDIT_SINKS=webhook" \
      --set-secrets="GEMINI_API_KEY=gemini-api-key:latest,AUTH0_DOMAIN=auth0-domain:latest,AUTH0_AUDIENCE=auth0-audience:latest"
    ```

### Option 2: AWS ECS (Fargate)

1.  **Push Image to ECR**: Create an ECR repository and push your Docker image.
2.  **Create Task Definition**:
    *   Add the `master-agent` container.
    *   Set environment variables.
    *   **Inject secrets from AWS Secrets Manager**:
        ```json
        {
          "secrets": [
            {
              "name": "AUTH0_DOMAIN",
              "valueFrom": "arn:aws:secretsmanager:region:account:secret:auth0-domain"
            },
            {
              "name": "AUTH0_AUDIENCE",
              "valueFrom": "arn:aws:secretsmanager:region:account:secret:auth0-audience"
            },
            {
              "name": "GEMINI_API_KEY",
              "valueFrom": "arn:aws:secretsmanager:region:account:secret:gemini-api-key"
            }
          ]
        }
        ```
    *   Configure `awslogs` driver for CloudWatch logging.
3.  **Create Service**:
    *   Select **Fargate** launch type.
    *   Attach an Application Load Balancer (ALB) for HTTPS termination.
    *   Ensure the Security Group allows traffic from the ALB on port 8000.

### Option 3: Kubernetes (GKE / EKS / AKS)

1.  **Create Secrets**:
    ```bash
    kubectl create secret generic app-secrets \
      --from-literal=gemini-key=<your-key> \
      --from-literal=auth0-domain=<your-tenant>.us.auth0.com \
      --from-literal=auth0-audience=https://api.tilli.com/chatbot
    ```

2.  **Create a Deployment**:
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
            - name: ENABLE_AUTH
              value: "true"
            - name: TEST_MODE
              value: "false"
            - name: GEMINI_API_KEY
              valueFrom:
                secretKeyRef:
                  name: app-secrets
                  key: gemini-key
            - name: AUTH0_DOMAIN
              valueFrom:
                secretKeyRef:
                  name: app-secrets
                  key: auth0-domain
            - name: AUTH0_AUDIENCE
              valueFrom:
                secretKeyRef:
                  name: app-secrets
                  key: auth0-audience
    ```

3.  **Expose Service**: Use a `LoadBalancer` service or an Ingress Controller.

## Authentication Configuration

### Auth0 Setup (Recommended)

1. **Create Auth0 Tenant**: Follow the [Auth0 Setup Guide](docs/AUTH0_SETUP_GUIDE.md)
2. **Configure Custom Claims**: Add Auth0 Action to include `role` and `school_id` in tokens
3. **Store Credentials**: Add `AUTH0_DOMAIN` and `AUTH0_AUDIENCE` to your secrets manager
4. **Set User Metadata**: Configure `app_metadata` for each user with their role and school

### Local JWT (Fallback)

If not using Auth0, ensure `JWT_SECRET_KEY` is set and tokens include:
- `sub` or `user_id`
- `role` (educator/admin)
- `school_id` (e.g., "School 1")

## Audit Logging in the Cloud

**Critical**: In a containerized environment, local files are ephemeral. If a container restarts, the `audit.log` file is lost.

**Configuration**:
1.  Set `AUDIT_LOG_TO_FILE=false` to disable local file writing (optional, but saves disk I/O).
2.  Set `AUDIT_LOG_STDOUT=true`. Most cloud providers (AWS CloudWatch, GCP Cloud Logging) automatically capture stdout/stderr.
3.  **Best Practice**: Configure an external sink using `AUDIT_SINKS`.
    *   **Splunk**: Set `SPLUNK_HEC_URL` and `SPLUNK_HEC_TOKEN`.
    *   **Webhook**: Set `AUDIT_WEBHOOK_URL` to forward logs to a sidecar or collector (like Fluent Bit).
    *   **OpenSearch**: Set `OPENSEARCH_URL`, `OPENSEARCH_USERNAME`, `OPENSEARCH_PASSWORD`.

**What Gets Logged**:
- Data access events (FERPA/UNICEF compliance)
- Harmful content detections
- Security events (authentication, authorization failures)
- Cross-school access attempts
- Auth0 token verifications

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

The health check verifies:
- Application is running
- Redis connection (if configured)
- Database connection (when implemented)

## Security Checklist for Production

Before deploying to production, ensure:

- [ ] `ENABLE_AUTH=true` is set
- [ ] Auth0 credentials (`AUTH0_DOMAIN`, `AUTH0_AUDIENCE`) are configured
- [ ] All secrets are injected via Secret Manager (not hardcoded)
- [ ] `ENFORCE_HTTPS=true` or HTTPS handled by load balancer
- [ ] `TEST_MODE=false`
- [ ] Audit logging is configured with external sink
- [ ] Redis is using managed service (not local)
- [ ] CORS origins are properly configured
- [ ] Rate limiting is enabled
- [ ] Health checks are configured on load balancer
- [ ] TLS/HTTPS is enforced
- [ ] Security headers are enabled

## Monitoring & Alerts

Set up monitoring for:
- **Application Health**: Monitor `/health` endpoint
- **Authentication Failures**: Alert on repeated Auth0 verification failures
- **Authorization Denials**: Monitor cross-school access attempts
- **Audit Log Delivery**: Alert if audit logs fail to reach external sink
- **Rate Limiting**: Monitor rate limit violations
- **Error Rates**: Track 4xx and 5xx responses

## Scaling Considerations

- **Horizontal Scaling**: The application is stateless and can scale horizontally
- **Redis**: Use managed Redis cluster for high availability
- **Database**: Use read replicas for read-heavy workloads
- **Rate Limiting**: Redis-based rate limiting scales with Redis cluster
- **Auth0**: Handles authentication at scale (no additional config needed)

## Cost Optimization

- **Cloud Run**: Scales to zero when not in use (lowest cost for low traffic)
- **Fargate**: Fixed cost per task (predictable for steady traffic)
- **Kubernetes**: Most cost-effective at scale (requires more management)
- **Redis**: Use smaller instances for dev/staging, cluster for production
- **Auth0**: Free tier supports up to 7,000 active users

---

**See Also**:
- [Auth0 Setup Guide](docs/AUTH0_SETUP_GUIDE.md)
- [Security Assessment](SECURITY_ASSESSMENT.md)
- [Audit Logging](AUDIT_LOGGING.md)
