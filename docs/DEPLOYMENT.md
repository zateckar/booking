# Deployment Guide

This guide provides step-by-step instructions for deploying the Booking Application using Docker.

## 🚀 Quick Start

### Option 1: Using Docker Compose (Recommended)

1. **Clone the repository**:
   ```bash
   git clone <your-repository-url>
   cd booking
   ```

2. **Configure environment** (optional):
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

3. **Deploy**:
   ```bash
   docker-compose up -d
   ```

4. **Access the application**:
   - Main app: http://localhost:8000
   - Admin panel: http://localhost:8000/static/admin.html

### Option 2: Using the Deployment Script

1. **Make script executable** (Linux/macOS):
   ```bash
   chmod +x deploy.sh
   ```

2. **Run deployment**:
   ```bash
   ./deploy.sh
   ```

3. **For help**:
   ```bash
   ./deploy.sh --help
   ```

## 📋 Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+ (or docker-compose 1.29+)
- Git
- curl (for health checks)

## 🔧 Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# Required
SECRET_KEY=your-long-random-secret-key

# Optional but recommended
DEFAULT_TIMEZONE=Europe/Prague
SENDGRID_API_KEY=your-sendgrid-api-key
FROM_EMAIL=noreply@yourdomain.com
FROM_NAME=Booking System
```

### Database

By default, the application uses SQLite. For production, consider PostgreSQL:

1. Uncomment PostgreSQL service in `docker-compose.yml`
2. Update `DATABASE_URL` in `.env`:
   ```
   DATABASE_URL=postgresql://booking_user:password@postgres:5432/booking
   ```

## 🛠️ GitHub Actions CI/CD

The repository includes automated CI/CD:

### Automatic Triggers
- **Push to main/master**: Builds and pushes to GitHub Container Registry
- **Pull requests**: Builds and tests
- **Git tags**: Creates versioned releases

### Manual Deployment from Registry

```bash
# Pull the latest image
docker pull ghcr.io/your-username/your-repo:latest

# Run using the production compose file
docker-compose -f deployment/docker-compose.prod.yml up -d
```

## 📊 Monitoring & Maintenance

### View Logs
```bash
# Docker Compose
docker-compose logs -f

# Direct Docker
docker logs -f booking-app
```

### Health Check
```bash
curl http://localhost:8000/api/oidc/providers
```

### Backup Data
```bash
# Backup volumes
docker run --rm -v booking_data:/data -v $(pwd):/backup alpine tar czf /backup/booking-backup.tar.gz /data

# Restore from backup
docker run --rm -v booking_data:/data -v $(pwd):/backup alpine tar xzf /backup/booking-backup.tar.gz -C /
```

### Update Application
```bash
# Using Docker Compose
docker-compose pull
docker-compose up -d

# Using deployment script
./deploy.sh
```

## 🔒 Security Considerations

### Production Checklist

- [ ] Change `SECRET_KEY` from default
- [ ] Set `DEBUG=false`
- [ ] Use HTTPS with reverse proxy
- [ ] Configure proper CORS origins
- [ ] Use PostgreSQL instead of SQLite
- [ ] Set up regular backups
- [ ] Monitor logs and metrics
- [ ] Keep Docker images updated

### Recommended Production Setup

```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  nginx:
    image: nginx:alpine
    ports:
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/ssl/certs
    depends_on:
      - booking-app

  booking-app:
    image: ghcr.io/your-username/booking:latest
    environment:
      - SECRET_KEY=${SECRET_KEY}
      - DATABASE_URL=postgresql://user:pass@postgres:5432/booking
    depends_on:
      - postgres

  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=booking
      - POSTGRES_USER=booking_user
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
```

## 🐛 Troubleshooting

### Common Issues

1. **Port already in use**:
   ```bash
   # Check what's using port 8000
   netstat -tulpn | grep :8000
   # Or change port in docker-compose.yml
   ```

2. **Database locked errors**:
   - Ensure only one container accesses SQLite
   - Consider switching to PostgreSQL

3. **OIDC authentication failures**:
   - Check provider configuration in admin panel
   - Verify network connectivity
   - Review application logs

4. **Container won't start**:
   ```bash
   # Check logs
   docker-compose logs booking-app
   
   # Check container status
   docker ps -a
   ```

### Getting Help

1. Check application logs first
2. Verify environment configuration
3. Test with minimal configuration
4. Review GitHub Issues for similar problems

## 📈 Scaling

### Horizontal Scaling
```yaml
services:
  booking-app:
    deploy:
      replicas: 3
  
  nginx:
    # Configure load balancing
```

### Performance Tuning
- Use PostgreSQL for better concurrent access
- Add Redis for session storage
- Configure nginx for static file serving
- Monitor resource usage

## 🔄 Updates & Maintenance

### Regular Tasks
- Monitor disk usage (logs, database, backups)
- Update Docker images monthly
- Review and rotate secrets quarterly
- Test backup/restore procedures

### Version Updates
1. Review changelog for breaking changes
2. Test in staging environment
3. Backup production data
4. Deploy during low-traffic period
5. Monitor application health post-deployment
