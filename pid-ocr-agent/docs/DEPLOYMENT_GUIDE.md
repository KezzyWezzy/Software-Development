# P&ID OCR Agent - Deployment Guide

## Quick Start (5 Minutes)

### Prerequisites
- Docker and Docker Compose installed
- 8GB RAM minimum (16GB recommended)
- 20GB disk space

### Deploy with Docker Compose

```bash
# Clone repository
git clone <repository-url>
cd pid-ocr-agent

# Copy environment file
cp .env.example .env

# Edit .env with your settings
nano .env

# Start all services
docker-compose up -d

# Check services are running
docker-compose ps

# View logs
docker-compose logs -f

# Access the application
# API: http://localhost:8000
# API Docs: http://localhost:8000/docs
# Worker Monitor: http://localhost:5555
```

That's it! The system is now running autonomously 24/7.

---

## Service URLs

Once deployed:

- **API Endpoint**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Flower (Worker Monitor)**: http://localhost:5555
- **MinIO Console**: http://localhost:9001

---

## Autonomous Operation Verification

### 1. Upload a Test Document

```bash
curl -X POST "http://localhost:8000/api/v1/documents/upload" \
  -F "file=@test_pid.pdf" \
  -F "project_name=Test Project" \
  -F "pid_reference=P&ID-001" \
  -F "auto_process=true"
```

**Expected Response:**
```json
{
  "status": "success",
  "document_id": "Test Project_20250107_120000",
  "task_id": "abc123...",
  "processing_status": "started"
}
```

### 2. Monitor Processing

Visit http://localhost:5555 to see:
- Task running in real-time
- Worker status
- Processing progress

### 3. Check Results

```bash
# Get task status
curl http://localhost:8000/api/v1/tasks/{task_id}
```

---

## Scaling for Production

### Horizontal Scaling

**Scale workers based on load:**

```yaml
# docker-compose.prod.yml
services:
  celery_worker:
    deploy:
      replicas: 10  # Run 10 workers
      update_config:
        parallelism: 2
        delay: 10s
      restart_policy:
        condition: on-failure
```

**Deploy:**
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --scale celery_worker=10
```

### Load Balancer Setup

```nginx
# nginx.conf
upstream pidocr_backend {
    least_conn;
    server backend1:8000;
    server backend2:8000;
    server backend3:8000;
}

server {
    listen 80;
    server_name pidocr.yourdomain.com;

    location / {
        proxy_pass http://pidocr_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## Production Configuration

### Environment Variables

```bash
# Production .env
DEBUG=False
LOG_LEVEL=WARNING

# Use production database
DATABASE_URL=postgresql://user:pass@prod-db:5432/pidocr

# Use production Redis
REDIS_URL=redis://prod-redis:6379/0

# Security
SECRET_KEY=<generate-secure-random-key>

# Scaling
MAX_CONCURRENT_JOBS=20
CELERY_WORKER_CONCURRENCY=8

# Resource limits
MAX_UPLOAD_SIZE=209715200  # 200MB
PROCESSING_TIMEOUT=1800    # 30 minutes
```

### Generate Secure Key

```python
import secrets
print(secrets.token_urlsafe(32))
```

---

## Monitoring Setup

### 1. Health Checks

Add health check endpoint monitoring:

```bash
# Add to cron
*/5 * * * * curl -f http://localhost:8000/health || alert_team
```

### 2. Prometheus Metrics

```yaml
# docker-compose.monitoring.yml
services:
  prometheus:
    image: prom/prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
```

### 3. Log Aggregation

```yaml
# docker-compose.logging.yml
services:
  elasticsearch:
    image: elasticsearch:7.17.0
    environment:
      - discovery.type=single-node

  logstash:
    image: logstash:7.17.0
    volumes:
      - ./logstash.conf:/usr/share/logstash/pipeline/logstash.conf

  kibana:
    image: kibana:7.17.0
    ports:
      - "5601:5601"
```

---

## Backup and Recovery

### Database Backup

```bash
# Automated daily backup script
#!/bin/bash
BACKUP_DIR="/backups/pidocr"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Backup PostgreSQL
docker exec pidocr_postgres pg_dump -U postgres pidocr > \
  $BACKUP_DIR/pidocr_$TIMESTAMP.sql

# Compress
gzip $BACKUP_DIR/pidocr_$TIMESTAMP.sql

# Keep last 30 days
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete
```

### Document Storage Backup

```bash
# Backup MinIO data
docker exec pidocr_minio mc mirror /data /backups/minio
```

### Restore Procedure

```bash
# Restore database
docker exec -i pidocr_postgres psql -U postgres pidocr < backup.sql

# Restore MinIO
docker exec pidocr_minio mc mirror /backups/minio /data
```

---

## Performance Tuning

### Database Optimization

```sql
-- Create indexes for faster queries
CREATE INDEX idx_documents_project ON documents(project_name);
CREATE INDEX idx_documents_status ON documents(status);
CREATE INDEX idx_instruments_tag ON instruments(tag);
CREATE INDEX idx_hazop_risk ON hazop_deviations(risk_ranking);
```

### Redis Configuration

```bash
# redis.conf
maxmemory 4gb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
```

### Celery Optimization

```python
# celery_config.py
CELERYD_PREFETCH_MULTIPLIER = 1  # Disable prefetching for long tasks
CELERY_ACKS_LATE = True          # Acknowledge after completion
CELERYD_MAX_TASKS_PER_CHILD = 100  # Restart worker after 100 tasks
```

---

## Security Hardening

### 1. Enable HTTPS

```yaml
# docker-compose.https.yml
services:
  nginx:
    image: nginx:alpine
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - /etc/letsencrypt:/etc/letsencrypt
    ports:
      - "443:443"
      - "80:80"
```

### 2. API Authentication

```python
# Add JWT authentication to endpoints
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer

security = HTTPBearer()

@app.post("/api/v1/documents/upload")
async def upload(token: str = Depends(security)):
    verify_token(token)
    # ... upload logic
```

### 3. Rate Limiting

```python
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter

@app.post("/api/v1/documents/upload")
@limiter.limit("10/minute")
async def upload():
    # ... upload logic
```

---

## Disaster Recovery

### High Availability Setup

```yaml
# docker-compose.ha.yml
services:
  postgres:
    deploy:
      replicas: 3
      placement:
        constraints:
          - node.role == worker

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes --cluster-enabled yes
```

### Failover Configuration

```yaml
# keepalived.conf
vrrp_instance VI_1 {
    state MASTER
    interface eth0
    virtual_router_id 51
    priority 100
    virtual_ipaddress {
        192.168.1.100
    }
}
```

---

## Cost Optimization

### Resource Management

```yaml
# Limit resources per container
services:
  celery_worker:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 2G
```

### Auto-Scaling Rules

```bash
# Scale based on queue length
if [ $(celery -A app.core.celery_app inspect active | wc -l) -gt 50 ]; then
  docker-compose scale celery_worker=10
else
  docker-compose scale celery_worker=3
fi
```

---

## Troubleshooting

### Common Issues

**1. Workers not starting:**
```bash
# Check logs
docker-compose logs celery_worker

# Verify Redis connection
docker exec pidocr_celery_worker redis-cli -h redis ping
```

**2. Out of memory:**
```bash
# Increase worker memory limit
docker-compose up -d --no-recreate --scale celery_worker=2
```

**3. Slow processing:**
```bash
# Check worker utilization
celery -A app.core.celery_app inspect stats

# Scale workers
docker-compose scale celery_worker=10
```

**4. Database connection pool exhausted:**
```python
# Increase pool size in settings.py
DB_POOL_SIZE = 50
DB_MAX_OVERFLOW = 20
```

---

## Maintenance

### Regular Tasks

**Daily:**
- Check worker status
- Review failed tasks
- Monitor disk space

**Weekly:**
- Review and archive old documents
- Database vacuum and analyze
- Update dependencies

**Monthly:**
- Security updates
- Performance review
- Capacity planning

### Update Procedure

```bash
# Pull latest code
git pull origin main

# Rebuild containers
docker-compose build

# Deploy with zero downtime
docker-compose up -d --no-deps --build celery_worker
docker-compose up -d --no-deps --build backend

# Run migrations
docker-compose exec backend alembic upgrade head
```

---

## Cloud Deployment

### AWS

```bash
# Deploy to ECS
ecs-cli compose -f docker-compose.yml up \
  --create-log-groups \
  --cluster pidocr-cluster

# Use RDS for PostgreSQL
DATABASE_URL=postgresql://user:pass@rds-endpoint:5432/pidocr

# Use ElastiCache for Redis
REDIS_URL=redis://elasticache-endpoint:6379/0

# Use S3 for document storage
AWS_S3_BUCKET=pidocr-documents
```

### Azure

```bash
# Deploy to Azure Container Instances
az container create \
  --resource-group pidocr-rg \
  --file docker-compose.yml

# Use Azure Database for PostgreSQL
# Use Azure Cache for Redis
# Use Azure Blob Storage
```

### Google Cloud

```bash
# Deploy to Cloud Run
gcloud run deploy pidocr-backend \
  --image gcr.io/project/pidocr-backend \
  --platform managed \
  --region us-central1

# Use Cloud SQL for PostgreSQL
# Use Memorystore for Redis
# Use Cloud Storage
```

---

## Support & Maintenance

### Getting Help

1. **Documentation**: Check `/docs` folder
2. **GitHub Issues**: Report bugs and feature requests
3. **Community**: Join our Discord/Slack
4. **Enterprise Support**: support@kjvsolutions.com

### Service Level Targets

- **Uptime**: 99.9%
- **Response Time**: < 5 seconds
- **Processing Time**: < 2 minutes per P&ID
- **Batch Processing**: 100+ documents per hour

---

**Deployed and Maintained by KJV Solutions™**
**For 24/7 Autonomous Operation**
