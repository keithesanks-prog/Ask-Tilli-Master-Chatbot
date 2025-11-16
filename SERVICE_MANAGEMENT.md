# Service Management & Fail-Safe Behavior

**Document Version:** 1.0  
**Last Updated:** 2024  
**Purpose:** Service management commands and fail-safe shutdown behavior

---

## Overview

The Master Agent service implements **fail-safe shutdown behavior** - when the service stops, it immediately rejects all new requests (like a safe lock that locks when power fails). This ensures:

- ✅ No new data access during shutdown
- ✅ No partial state during shutdown
- ✅ In-flight requests complete gracefully
- ✅ Audit logs are written before shutdown

---

## Service Management Commands

### **Using systemd (Linux - Recommended)**

**Install Service:**
```bash
sudo ./deployment/manage-service.sh install
sudo systemctl enable master-agent.service  # Enable on boot
```

**Start Service:**
```bash
sudo systemctl start master-agent
# or
sudo ./deployment/manage-service.sh start
```

**Stop Service (Graceful Shutdown - Fail-Safe):**
```bash
sudo systemctl stop master-agent
# or
sudo ./deployment/manage-service.sh stop
```

**Restart Service:**
```bash
sudo systemctl restart master-agent
# or
sudo ./deployment/manage-service.sh restart
```

**Reload Service (Graceful Reload):**
```bash
sudo systemctl reload master-agent
# or
sudo ./deployment/manage-service.sh reload
```

**Check Status:**
```bash
sudo systemctl status master-agent
# or
sudo ./deployment/manage-service.sh status
```

---

### **Using Management Script**

**Location:** `deployment/manage-service.sh`

**Available Commands:**
```bash
./deployment/manage-service.sh start      # Start service
./deployment/manage-service.sh stop       # Stop service (graceful shutdown)
./deployment/manage-service.sh restart    # Restart service
./deployment/manage-service.sh reload     # Reload service (graceful)
./deployment/manage-service.sh status     # Show status and logs
./deployment/manage-service.sh install    # Install service file
./deployment/manage-service.sh help       # Show help
```

---

### **Manual Start/Stop (Development)**

**Start Service:**
```bash
cd /opt/master-agent
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**Stop Service:**
- Press `Ctrl+C` for graceful shutdown
- Or send `SIGTERM`: `kill -TERM <pid>`

**Background Process:**
```bash
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > logs/app.log 2>&1 &
echo $! > master-agent.pid  # Save PID for later
```

**Stop Background Process:**
```bash
kill -TERM $(cat master-agent.pid)  # Graceful shutdown
```

---

## Fail-Safe Behavior

### **What is Fail-Safe?**

**Fail-Safe** = When service stops, it **prevents new actions** (like a safe lock that locks when power fails).

**Behavior:**
- ✅ **Service Stopping** → Rejects all new requests immediately
- ✅ **In-Flight Requests** → Allowed to complete gracefully
- ✅ **New Data Access** → Prevented during shutdown
- ✅ **Audit Logs** → Written before shutdown completes

---

### **Service States**

1. **STARTING** - Service is initializing
   - Not accepting requests yet
   - Security measures loading

2. **RUNNING** - Service is operational
   - ✅ Accepting new requests
   - ✅ Processing requests normally
   - ✅ All security measures active

3. **STOPPING** - Service is shutting down (Fail-Safe Mode)
   - ❌ **Rejects all new requests** (fail-safe)
   - ✅ Allows in-flight requests to complete
   - ✅ Waits up to 30 seconds for completion
   - ✅ Prevents new data access

4. **STOPPED** - Service is stopped
   - Not accepting requests
   - All requests completed or timed out

---

### **Fail-Safe Implementation**

**1. Request Rejection (503 Service Unavailable)**

When service enters `STOPPING` state:
```json
{
  "error": "Service Unavailable",
  "message": "Service is shutting down. Please try again later.",
  "service_state": "stopping",
  "fail_safe": true
}
```

**2. Graceful Shutdown Sequence**

```
1. Signal received (SIGTERM, SIGINT)
   ↓
2. Service state → STOPPING (fail-safe mode)
   ↓
3. Fail-safe middleware rejects new requests
   ↓
4. In-flight requests complete gracefully
   ↓
5. Wait up to 30 seconds for completion
   ↓
6. Service state → STOPPED
   ↓
7. Service exits
```

**3. In-Flight Request Tracking**

- Service tracks number of in-flight requests
- New requests are rejected when stopping
- Existing requests can complete
- Shutdown waits for all requests to finish

---

## Configuration

### **Environment Variables**

```bash
# Maximum shutdown wait time (seconds)
SHUTDOWN_TIMEOUT=30  # Default: 30 seconds

# Enable fail-safe behavior (default: true)
ENABLE_FAIL_SAFE=true
```

---

## Monitoring Shutdown

### **Check Service State**

**Via Health Endpoint:**
```bash
curl http://localhost:8000/health
```

**Via Service Manager (Internal):**
```python
from app.services.service_manager import get_service_manager

service_manager = get_service_manager()
print(f"Service state: {service_manager.state.value}")
print(f"Accepting requests: {service_manager.is_accepting_requests}")
print(f"In-flight requests: {service_manager.in_flight_count}")
```

**Via Systemd:**
```bash
systemctl status master-agent
journalctl -u master-agent -f  # Follow logs
```

---

## Logs During Shutdown

**Normal Shutdown:**
```
INFO: Received signal 15. Initiating graceful shutdown (fail-safe)...
WARNING: Service state: STOPPING - Rejecting new requests (fail-safe mode). 3 in-flight requests remaining.
INFO: Waiting up to 30s for 3 in-flight requests to complete...
INFO: Service state: STOPPED - All requests completed gracefully
INFO: Service shutdown complete
```

**Timeout Shutdown:**
```
WARNING: Shutdown timeout: 2 requests still in-flight after 30s
ERROR: Force shutdown: In-flight requests did not complete in time
```

---

## Testing Fail-Safe Behavior

### **Test 1: Request Rejection During Shutdown**

```bash
# Terminal 1: Start service
./deployment/manage-service.sh start

# Terminal 2: Send request and immediately stop service
curl http://localhost:8000/health &
sleep 1
./deployment/manage-service.sh stop

# Should see: 503 Service Unavailable (fail-safe)
```

### **Test 2: In-Flight Request Completion**

```python
import requests
import time

# Start long-running request
response = requests.get("http://localhost:8000/health", timeout=60)

# While request is running, stop service
# Request should complete (if within timeout)
```

---

## Production Best Practices

### **1. Deployment Strategy**

**Zero-Downtime Deployment:**
1. Deploy new version alongside old version
2. Switch traffic to new version
3. Wait for in-flight requests on old version
4. Stop old version (fail-safe shutdown)
5. Verify new version is healthy

### **2. Health Check Integration**

**Load Balancer Health Checks:**
- Load balancer should stop sending traffic when health check fails
- Service enters STOPPING state → Health check returns 503
- Load balancer stops routing new traffic
- In-flight requests complete on old instance

### **3. Monitoring**

**Alert on:**
- Service shutdown events
- Shutdown timeouts (>30 seconds)
- Requests rejected during shutdown
- Unusual shutdown patterns

---

## Troubleshooting

### **Issue: Service Won't Stop**

**Symptoms:**
- `systemctl stop` hangs
- Service doesn't respond to SIGTERM

**Solutions:**
```bash
# Check in-flight requests
systemctl status master-agent

# Force stop (not recommended - may lose data)
systemctl kill -s KILL master-agent

# Check for hung requests
journalctl -u master-agent | grep "in-flight"
```

### **Issue: Requests Not Completing**

**Symptoms:**
- Shutdown timeout (>30 seconds)
- In-flight requests never complete

**Solutions:**
1. Check for long-running database queries
2. Check for hung external API calls (Gemini)
3. Reduce timeout: `SHUTDOWN_TIMEOUT=15`
4. Investigate specific endpoints causing delays

### **Issue: New Requests Accepted During Shutdown**

**Symptoms:**
- Service accepts requests after stop command

**Solutions:**
1. Verify fail-safe middleware is loaded first
2. Check service state transitions
3. Verify signal handlers are registered

---

## Systemd Service File

**Location:** `deployment/master-agent.service`

**Key Features:**
- Graceful shutdown (30 second timeout)
- Automatic restart on failure
- Security hardening (NoNewPrivileges, PrivateTmp)
- Resource limits
- Journal logging

**Installation:**
```bash
sudo cp deployment/master-agent.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable master-agent
sudo systemctl start master-agent
```

---

## Docker Deployment (Alternative)

**Dockerfile:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Docker Commands:**
```bash
# Start
docker-compose up -d

# Stop (graceful shutdown)
docker-compose stop

# Restart
docker-compose restart

# Logs
docker-compose logs -f
```

---

## Kubernetes Deployment (Alternative)

**Deployment with Graceful Shutdown:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: master-agent
spec:
  replicas: 2
  template:
    spec:
      containers:
      - name: master-agent
        image: master-agent:latest
        ports:
        - containerPort: 8000
        lifecycle:
          preStop:
            exec:
              command: ["/bin/sh", "-c", "sleep 10"]  # Grace period
        terminationGracePeriodSeconds: 30  # Fail-safe timeout
```

**Kubernetes Commands:**
```bash
kubectl apply -f deployment.yaml
kubectl scale deployment master-agent --replicas=3
kubectl delete pod <pod-name>  # Graceful shutdown
```

---

## Security Considerations

### **Fail-Safe During Security Incidents**

**Scenario: Security Breach Detected**
1. Service enters STOPPING state immediately
2. All new requests rejected (fail-safe)
3. Prevents further data access
4. In-flight requests complete and are logged
5. Service shuts down cleanly

**Implementation:**
```python
# Emergency shutdown endpoint (protected by admin auth)
@app.post("/admin/emergency-shutdown")
async def emergency_shutdown(current_user: dict = Depends(require_admin)):
    service_manager = get_service_manager()
    service_manager.stop()  # Trigger fail-safe shutdown
    return {"status": "shutdown_initiated"}
```

---

## References

- [FastAPI Lifespan Events](https://fastapi.tiangolo.com/advanced/events/)
- [Systemd Service Management](https://www.freedesktop.org/software/systemd/man/systemd.service.html)
- [Graceful Shutdown Patterns](https://cloud.google.com/blog/products/containers-kubernetes/kubernetes-best-practices-terminating-with-grace)

---

**Document Version:** 1.0  
**Last Updated:** 2024


