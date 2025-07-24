# OIDC HTTPS Redirect URI Security Fix

## Overview

This document describes the security fix implemented to ensure OIDC (OpenID Connect) redirect URIs use HTTPS scheme in production environments, which is required by most OIDC identity providers for security compliance.

## Problem Statement

When deploying web applications behind reverse proxies (like Nginx, Apache, or cloud load balancers) that terminate TLS/SSL, the internal application receives HTTP requests even though external users connect via HTTPS. This causes OIDC redirect URIs to be constructed with HTTP scheme, which:

1. **Violates OIDC security requirements** - Most identity providers reject HTTP redirect URIs in production
2. **Creates security vulnerabilities** - Authorization codes could be transmitted over unencrypted connections
3. **Breaks authentication flow** - Users cannot complete OIDC login process

### Example of the Problem

```
User connects to: https://myapp.example.com/api/login/oidc/provider
Internal request to app: http://app:8000/api/login/oidc/provider
Generated redirect URI: http://myapp.example.com/api/auth/oidc/provider  ❌ HTTP!
OIDC provider rejects: Invalid redirect_uri scheme
```

## Solution Implementation

The fix implements intelligent HTTPS detection and automatic scheme correction for OIDC redirect URIs using multiple detection methods:

### Detection Methods

#### 1. Explicit Configuration
```bash
# Environment variable to force HTTPS redirects
FORCE_HTTPS_REDIRECTS=true
```

#### 2. Reverse Proxy Headers
The system automatically detects HTTPS termination by checking standard reverse proxy headers:
- `X-Forwarded-Proto: https`
- `X-Forwarded-Ssl: on`

#### 3. Containerized Environment Detection
When running in containers (Docker), the system assumes production deployment with HTTPS termination unless explicitly configured for development:
- Detects container environment via `DOCKER_CONTAINER` env var or `/.dockerenv` file
- Can be overridden with `ENVIRONMENT=development`

### Code Implementation

The fix is implemented in two main locations:

#### 1. OIDC Login Handler (`src/booking/__init__.py`)
```python
def _get_secure_redirect_uri(request: Request, endpoint: str, **path_params) -> str:
    """Generate a secure redirect URI, ensuring HTTPS in production environments."""
    
    # Generate the base URI
    redirect_uri = str(request.url_for(endpoint, **path_params))
    
    # Apply HTTPS detection logic
    force_https = _should_force_https(request)
    
    if force_https and redirect_uri.startswith("http://"):
        redirect_uri = redirect_uri.replace("http://", "https://", 1)
        logger.info(f"Redirect URI scheme changed to HTTPS for production: {redirect_uri}")
    
    return redirect_uri
```

#### 2. OIDC Logout Handler (`src/booking/routers/auth.py`)
```python
def _get_secure_logout_redirect_uri(request: Request) -> str:
    """Generate a secure post-logout redirect URI, ensuring HTTPS in production."""
    
    # Build base URL and apply same HTTPS detection logic
    # for post-logout redirect URIs
```

## Configuration Options

### Environment Variables

#### Required for Production
```bash
# Option 1: Explicit HTTPS forcing (recommended for production)
FORCE_HTTPS_REDIRECTS=true

# Option 2: Set environment type (prevents auto-detection issues)
ENVIRONMENT=production
```

#### Development Override
```bash
# Prevent HTTPS forcing in development environments
ENVIRONMENT=development
# or
ENVIRONMENT=dev
# or
ENVIRONMENT=local
```

### Reverse Proxy Configuration

Ensure your reverse proxy sends the correct headers:

#### Nginx Example
```nginx
server {
    listen 443 ssl;
    server_name myapp.example.com;
    
    location / {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;  # Important!
    }
}
```

#### Apache Example
```apache
<VirtualHost *:443>
    ServerName myapp.example.com
    
    ProxyPass / http://backend:8000/
    ProxyPassReverse / http://backend:8000/
    ProxyPreserveHost On
    
    # Important headers
    ProxyAddHeaders On
    ProxyAddHeaders X-Forwarded-Proto https
</VirtualHost>
```

#### Docker Compose with Traefik
```yaml
services:
  booking-app:
    image: ghcr.io/zateckar/booking:latest
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.booking.rule=Host(`myapp.example.com`)"
      - "traefik.http.routers.booking.tls=true"
      # Traefik automatically adds X-Forwarded-Proto headers
```

## Verification

### Check Logs
The application logs when HTTPS redirection is applied:

```
INFO - HTTPS detected via X-Forwarded-Proto header
INFO - Redirect URI scheme changed to HTTPS for production: https://myapp.example.com/api/auth/oidc/provider
```

### Test OIDC Flow
1. Access your application via HTTPS: `https://myapp.example.com`
2. Initiate OIDC login
3. Check browser developer tools network tab for redirect URI
4. Verify OIDC provider accepts the redirect URI
5. Complete authentication flow successfully

### Debug Mode
Enable debug logging to see detection logic:

```python
# In logging configuration
logging.getLogger("routers.auth").setLevel(logging.DEBUG)
logging.getLogger("main").setLevel(logging.DEBUG)
```

## Deployment Examples

### Production Deployment
```bash
# docker-compose.yml or environment
FORCE_HTTPS_REDIRECTS=true
ENVIRONMENT=production
```

### Development Deployment
```bash
# Local development
ENVIRONMENT=development
# HTTPS forcing will be disabled
```

### Cloud Deployment (AWS ALB, GCP Load Balancer, etc.)
```bash
# Usually no explicit config needed
# Cloud load balancers typically send correct X-Forwarded-Proto headers
# Container detection will automatically enable HTTPS
```

## Security Benefits

1. **OIDC Compliance** - Redirect URIs use secure HTTPS scheme as required by identity providers
2. **Data Protection** - Authorization codes transmitted securely
3. **Automatic Detection** - No manual configuration required in most deployments
4. **Flexible Configuration** - Explicit control when needed
5. **Development Friendly** - Doesn't interfere with local development

## Troubleshooting

### Issue: OIDC provider still rejects redirect URI

**Solution**: Check that your reverse proxy is sending the correct headers:
```bash
# Test headers received by application
curl -H "X-Forwarded-Proto: https" http://localhost:8000/api/oidc/providers
```

### Issue: HTTPS forced in development

**Solution**: Set development environment:
```bash
export ENVIRONMENT=development
```

### Issue: HTTPS not being applied in production

**Solution**: Explicitly force HTTPS:
```bash
export FORCE_HTTPS_REDIRECTS=true
```

## Related Files

- `src/booking/__init__.py` - Main OIDC login handler with secure redirect URI generation
- `src/booking/routers/auth.py` - OIDC logout handler with secure post-logout redirect URI
- `.env.example` - Environment variable documentation
- `docs/OIDC_HTTPS_REDIRECT_URI_FIX.md` - This documentation file

## Migration Notes

This fix is **backward compatible** and requires no database migrations or configuration changes for existing deployments. The automatic detection ensures existing production deployments will immediately benefit from HTTPS redirect URIs.

For new deployments, consider setting `FORCE_HTTPS_REDIRECTS=true` explicitly to ensure consistent behavior regardless of deployment environment.
