# TLS/HTTPS Configuration Guide

This document describes the TLS protection mechanisms implemented in the Master Agent and how to configure them.

## Overview

The Master Agent implements multiple layers of TLS protection:

1. **TLS Enforcement Middleware** - Validates that requests are over HTTPS
2. **Security Headers Middleware** - Adds security headers including HSTS
3. **HTTPS Redirect** - Automatically redirects HTTP to HTTPS (configurable)

## Features

### 1. TLS Enforcement

- Validates that requests are over HTTPS
- Checks `X-Forwarded-Proto` header (for reverse proxy setups)
- Allows HTTP for localhost in development
- Host header validation (optional)

### 2. HSTS (HTTP Strict Transport Security)

- Forces browsers to use HTTPS for future connections
- Configurable max-age (default: 1 year)
- Optional `includeSubDomains`
- Optional `preload` for HSTS preload list

### 3. Security Headers

The following security headers are automatically added to all responses:

- **Strict-Transport-Security**: HSTS header
- **Content-Security-Policy**: Prevents XSS and injection attacks
- **X-Content-Type-Options**: Prevents MIME type sniffing
- **X-Frame-Options**: Prevents clickjacking (set to DENY)
- **X-XSS-Protection**: Enables XSS filter
- **Referrer-Policy**: Controls referrer information
- **Permissions-Policy**: Disables unnecessary browser features
- **Server header**: Removed to hide server information

## Configuration

### Environment Variables

```bash
# Required for production
ENVIRONMENT=production  # Automatically enables TLS enforcement

# TLS Configuration
REQUIRE_TLS=true  # Enforce TLS (defaults to true in production)
ENFORCE_HTTPS=true  # Redirect HTTP to HTTPS (defaults to true in production)

# HSTS Configuration
HSTS_MAX_AGE=31536000  # Max-age in seconds (default: 1 year)
HSTS_INCLUDE_SUBDOMAINS=true  # Include subdomains in HSTS (default: true)
HSTS_PRELOAD=false  # Enable HSTS preload (default: false, requires manual setup)

# Host Validation
ALLOWED_HOSTS=api.example.com,www.example.com  # Comma-separated list
```

### Production Configuration

**Recommended production settings:**

```bash
export ENVIRONMENT=production
export REQUIRE_TLS=true
export ENFORCE_HTTPS=true
export HSTS_MAX_AGE=31536000  # 1 year
export HSTS_INCLUDE_SUBDOMAINS=true
export HSTS_PRELOAD=false  # Set to true after testing if desired
export ALLOWED_HOSTS=api.tilli.com,api-staging.tilli.com
```

### Development Configuration

**Development settings (HTTP allowed for localhost):**

```bash
export ENVIRONMENT=development
export REQUIRE_TLS=false  # Allow HTTP for localhost
export ENFORCE_HTTPS=false  # Don't redirect HTTP to HTTPS
# HSTS settings are ignored when ENFORCE_HTTPS=false
```

## Reverse Proxy Setup

For production deployments behind a reverse proxy (nginx, load balancer), configure the proxy to:

1. **Terminate TLS** at the proxy
2. **Set X-Forwarded-Proto header** to `https`
3. **Set X-Forwarded-Ssl header** to `on` (optional)

### Nginx Example Configuration

```nginx
server {
    listen 443 ssl http2;
    server_name api.example.com;
    
    # SSL Configuration
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    # TLS 1.3 only (recommended)
    ssl_protocols TLSv1.3;
    
    # Or allow TLS 1.2 and 1.3 (if needed for compatibility)
    # ssl_protocols TLSv1.2 TLSv1.3;
    
    # Strong cipher suites
    ssl_ciphers 'TLS_AES_128_GCM_SHA256:TLS_AES_256_GCM_SHA384:TLS_CHACHA20_POLY1305_SHA256';
    ssl_prefer_server_ciphers off;
    
    # HSTS (also set by application, but good to have at proxy level)
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;  # Important!
        proxy_set_header X-Forwarded-Ssl on;
    }
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name api.example.com;
    return 301 https://$server_name$request_uri;
}
```

### Load Balancer (AWS ALB/ELB) Configuration

1. **Configure HTTPS listener** on port 443
2. **Enable SSL termination** at the load balancer
3. **Configure health check** to use HTTP (backend connection)
4. **Set target group** to HTTP (backend doesn't need to terminate TLS)

The load balancer will automatically:
- Set `X-Forwarded-Proto` header to `https`
- Terminate TLS before forwarding to backend

### Cloudflare Configuration

If using Cloudflare:

1. **SSL/TLS mode**: Set to "Full" or "Full (strict)"
2. **Always Use HTTPS**: Enable redirect
3. **Automatic HTTPS Rewrites**: Enable
4. **HSTS**: Can enable at Cloudflare level (redundant but okay)

## Testing TLS Configuration

### Test HTTPS Enforcement

```bash
# Should redirect to HTTPS (if ENFORCE_HTTPS=true)
curl -I http://api.example.com/

# Should work over HTTPS
curl -I https://api.example.com/

# Should return security headers
curl -I https://api.example.com/health
```

### Check Security Headers

```bash
curl -I https://api.example.com/health | grep -i "strict-transport-security\|content-security-policy\|x-frame-options"
```

Expected headers:
```
Strict-Transport-Security: max-age=31536000; includeSubDomains
Content-Security-Policy: default-src 'self'; ...
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
```

### Test Host Header Validation

```bash
# Should work
curl -H "Host: api.example.com" https://api.example.com/

# Should fail (if ALLOWED_HOSTS is set)
curl -H "Host: evil.com" https://api.example.com/
```

## HSTS Preload

If you want to submit your domain to the HSTS preload list:

1. **Enable preload**:
   ```bash
   export HSTS_PRELOAD=true
   export HSTS_INCLUDE_SUBDOMAINS=true
   ```

2. **Verify your HSTS header**:
   ```bash
   curl -I https://api.example.com/ | grep Strict-Transport-Security
   ```
   Should show: `max-age=31536000; includeSubDomains; preload`

3. **Test your domain**:
   - Visit: https://hstspreload.org/
   - Enter your domain
   - Fix any issues reported

4. **Submit to preload list**:
   - After fixing issues, submit at: https://hstspreload.org/

**⚠️ Warning**: Once on the preload list, it's difficult to remove. Make sure your HTTPS setup is stable.

## TLS Certificate Management

### Let's Encrypt (Recommended)

Use Certbot for free SSL certificates:

```bash
# Install certbot
sudo apt-get install certbot python3-certbot-nginx

# Get certificate (for nginx)
sudo certbot --nginx -d api.example.com

# Auto-renewal is set up automatically
sudo certbot renew --dry-run  # Test renewal
```

### Self-Signed Certificate (Development Only)

```bash
# Generate self-signed certificate
openssl req -x509 -newkey rsa:4096 -nodes \
  -keyout key.pem -out cert.pem \
  -days 365 -subj "/CN=localhost"

# Run with uvicorn (development only!)
uvicorn app.main:app --host 0.0.0.0 --port 8000 \
  --ssl-keyfile key.pem --ssl-certfile cert.pem
```

**⚠️ Warning**: Never use self-signed certificates in production!

## Security Checklist

- [ ] TLS 1.3 enabled (or TLS 1.2 minimum)
- [ ] Strong cipher suites configured
- [ ] Certificate from trusted CA (not self-signed)
- [ ] HSTS enabled with max-age >= 31536000 (1 year)
- [ ] HTTP to HTTPS redirect configured
- [ ] Host header validation configured (if applicable)
- [ ] Security headers verified in responses
- [ ] Certificate auto-renewal configured (if using Let's Encrypt)
- [ ] Reverse proxy properly configured with X-Forwarded-Proto
- [ ] TLS termination at reverse proxy (not application level)

## Troubleshooting

### "TLS/HTTPS is required" Error

**Problem**: Getting 400 error with "TLS/HTTPS is required"

**Solutions**:
1. Make sure you're accessing via HTTPS: `https://api.example.com`
2. Check that reverse proxy sets `X-Forwarded-Proto: https` header
3. If testing locally, use `localhost` (HTTP allowed for localhost)
4. Disable TLS requirement for testing: `export REQUIRE_TLS=false`

### HSTS Header Not Appearing

**Problem**: HSTS header missing from responses

**Solutions**:
1. Check that `ENFORCE_HTTPS=true` or `ENVIRONMENT=production`
2. Verify middleware is added before other middleware
3. Check logs for middleware initialization messages
4. Test with: `curl -I https://api.example.com/health`

### Host Header Validation Failing

**Problem**: Getting "Invalid host header" error

**Solutions**:
1. Make sure request `Host` header matches one in `ALLOWED_HOSTS`
2. Check that `ALLOWED_HOSTS` is set correctly (comma-separated)
3. Remove `ALLOWED_HOSTS` to allow all hosts (not recommended for production)

## Additional Resources

- [OWASP TLS Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Transport_Layer_Protection_Cheat_Sheet.html)
- [HSTS Preload List](https://hstspreload.org/)
- [SSL Labs SSL Test](https://www.ssllabs.com/ssltest/) - Test your TLS configuration
- [Mozilla SSL Configuration Generator](https://ssl-config.mozilla.org/) - Generate nginx/HAProxy configs


