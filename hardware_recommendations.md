# Hardware Requirements & Optimization Guide

## 1. Resource Usage Analysis

### CPU
- **Base Load**: FastAPI + Uvicorn is lightweight and efficient.
- **Peak Load**:
    - **Log Rotation**: The background compression (`gzip`) and hashing (`SHA-256`) are CPU-intensive.
    - **Impact**: Frequent rotations (small `AUDIT_LOG_MAX_BYTES`) will cause CPU spikes.
- **Optimization**: The current implementation uses background threads to avoid blocking the main request loop.

### Memory (RAM)
- **Base Load**: ~100MB - 200MB for the Python process (depending on loaded libraries).
- **Peak Load**:
    - **Log Rotation**: The implementation uses **streaming** (`shutil.copyfileobj` and 4KB chunked reads) for compression and hashing. This ensures memory usage remains constant and low (~few MBs) regardless of log file size.
    - **Concurrency**: High concurrency (many requests/sec) will increase memory usage for request handling.

### Disk I/O
- **High Impact**: Audit logging is write-heavy.
- **Latency**: Slow disk I/O can block the logging thread if the buffer fills up, potentially slowing down the application.
- **Recommendation**: Use SSDs for the `logs/` directory.

## 2. Recommended Hardware Specifications

### Minimum (Development / Low Traffic)
- **CPU**: 1 vCPU
- **RAM**: 512 MB
- **Storage**: 10 GB (SSD preferred)

### Recommended (Production / Moderate Traffic)
- **CPU**: 2 vCPUs (allows background compression to run without starving the main app)
- **RAM**: 1 GB - 2 GB
- **Storage**: 50 GB+ SSD (depending on retention policy)

### High Performance (High Traffic)
- **CPU**: 4+ vCPUs
- **RAM**: 4 GB+
- **Storage**: High-performance NVMe SSDs

## 3. Configuration for Optimization

### Docker Resource Limits
It is **highly recommended** to set resource limits in `docker-compose.yml` or Kubernetes to prevent the container from consuming all host resources during a log rotation spike or DoS attack.

**Example `docker-compose.yml` update:**
```yaml
services:
  master-agent:
    # ...
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 256M
```

### Log Rotation Tuning
- **`AUDIT_LOG_MAX_BYTES`**:
    - **Small (e.g., 10MB)**: More frequent rotations, more frequent CPU spikes, but smaller files (faster to compress/upload).
    - **Large (e.g., 100MB)**: Less frequent rotations, but longer compression time and higher I/O burst.
    - **Recommendation**: **50MB - 100MB** is a good balance for production.

### Concurrency
- **Workers**: For production, run Uvicorn with multiple workers (`--workers`) or use a process manager (Gunicorn) to utilize multiple CPU cores.
    - Formula: `workers = (2 x num_cores) + 1`
