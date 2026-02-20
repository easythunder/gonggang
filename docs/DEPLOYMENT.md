# Production Deployment Guide (T096)

## Pre-Deployment Checklist

### Environment Setup
- [ ] PostgreSQL 14+ instance available
- [ ] Python 3.11+ runtime
- [ ] Tesseract OCR library installed (`apt-get install tesseract-ocr`)
- [ ] TLS certificates (self-signed for dev, valid CA for prod)
- [ ] Environment variables configured (see Environment Variables section)

### Database Preparation
- [ ] PostgreSQL database created (`createdb gonggang`)
- [ ] User with permissions created
- [ ] Connection tested from application server
- [ ] Backup strategy in place (daily snapshots)

### Kubernetes Setup (if using K8s)
- [ ] Cluster access configured (`kubectl config`)
- [ ] Namespace created (`kubectl create namespace gonggang`)
- [ ] Secrets for DB credentials (`kubectl create secret`)
- [ ] CronJob manifest reviewed and ready

---

## Database Setup

### 1. Create Database and User
```bash
psql -U postgres

# Connect to PostgreSQL and run:
CREATE DATABASE gonggang ENCODING UTF8;
CREATE USER gonggang_user WITH PASSWORD 'strong_password_123';
ALTER ROLE gonggang_user WITH SUPERUSER CREATEROLE CREATEDB;
GRANT ALL PRIVILEGES ON DATABASE gonggang TO gonggang_user;
\c gonggang
GRANT ALL ON SCHEMA public TO gonggang_user;
```

### 2. Run Migrations
```bash
cd /app/gonggang
export DATABASE_URL="postgresql://gonggang_user:strong_password_123@pg.example.com:5432/gonggang"

# Create tables
alembic upgrade head

# Or manually create schema:
cat docs/schema.sql | psql $DATABASE_URL
```

### 3. Set Up Indexes
```sql
-- Create covering indexes for common queries
CREATE INDEX idx_group_expires_at ON groups(expires_at) WHERE deleted_at IS NULL;
CREATE INDEX idx_submission_group_nickname ON submissions(group_id, nickname);
CREATE INDEX idx_interval_submission_day ON intervals(submission_id, day_of_week);
CREATE INDEX idx_free_time_result_group_version ON group_free_time_results(group_id, version DESC);
```

---

## Environment Variables

### Required (.env file or k8s secrets)
```bash
# Database
DATABASE_URL=postgresql://gonggang_user:password@postgres.example.com:5432/gonggang

# Application
ENVIRONMENT=production
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=false

# OCR
OCR_LIBRARY=tesseract  # or 'paddleocr'
OCR_TIMEOUT_SECONDS=3
OCR_MAX_CONCURRENT=3

# Batch Deletion
DELETION_BATCH_INTERVAL_SECONDS=600  # 10 minutes
DELETION_DRY_RUN=false
DELETION_BATCH_SIZE=100

# Polling
POLLING_INTERVAL_MS=2500  # Server-enforced minimum

# TLS
TLS_CERT_PATH=/etc/ssl/certs/gonggang.crt
TLS_KEY_PATH=/etc/ssl/private/gonggang.key
```

---

## Docker Deployment

### Build Image
```bash
cd gonggang
docker build -t gonggang:0.1.0 \
  --build-arg PYTHON_VERSION=3.11 \
  -f docker/Dockerfile \
  .
```

### Run Container
```bash
docker run -d \
  --name gonggang-api \
  -p 8000:8000 \
  -e DATABASE_URL="postgresql://user:pass@db:5432/gonggang" \
  -e ENVIRONMENT=production \
  -v /etc/ssl/certs:/etc/ssl/certs:ro \
  --health-cmd="curl -f http://localhost:8000/health || exit 1" \
  --health-interval=30s \
  gonggang:0.1.0
```

### Docker Compose
```bash
# Start full stack
docker-compose -f docker/docker-compose.yml up -d

# View logs
docker-compose logs -f gonggang-api

# Stop
docker-compose down
```

---

## Kubernetes Deployment

### Create Namespace and Secrets
```bash
kubectl create namespace gonggang

# Create DB credentials
kubectl create secret generic db-credentials \
  --from-literal=username=gonggang_user \
  --from-literal=password=strong_password_123 \
  -n gonggang

# Create TLS cert
kubectl create secret tls gonggang-tls \
  --cert=/path/to/cert.crt \
  --key=/path/to/key.key \
  -n gonggang
```

### Deploy API Server
```bash
# Edit k8s/deployment.yaml with image tag and resource limits
kubectl apply -f k8s/deployment.yaml

# Check deployment status
kubectl rollout status deployment/gonggang-api -n gonggang

# View logs
kubectl logs -l app=gonggang-api -n gonggang -f
```

### Deploy Batch Deletion CronJob
```bash
# Edit k8s/cronjob.yaml with schedule and image
kubectl apply -f k8s/cronjob.yaml

# Verify CronJob
kubectl get cronjob -n gonggang

# Check last run
kubectl describe cronjob gonggang-batch-deletion -n gonggang
```

### Service Exposure
```bash
kubectl apply -f k8s/service.yaml

# Get service endpoint
kubectl get svc gonggang-api -n gonggang
```

---

## TLS/HTTPS Setup

### Generate Self-Signed Certificate (Development)
```bash
openssl req -x509 -newkey rsa:4096 -nodes \
  -out /etc/ssl/certs/gonggang.crt \
  -keyout /etc/ssl/private/gonggang.key \
  -days 365 \
  -subj "/C=KR/ST=Seoul/L=Seoul/O=Company/CN=gonggang.local"
```

### Valid Certificate (Production)
```bash
# Use Let's Encrypt with Certbot
certbot certonly --standalone -d gonggang.example.com

# Copy to secure location
cp /etc/letsencrypt/live/gonggang.example.com/fullchain.pem /etc/ssl/certs/gonggang.crt
cp /etc/letsencrypt/live/gonggang.example.com/privkey.pem /etc/ssl/private/gonggang.key
```

### Configure in Application
```python
# src/main.py
import ssl

if config.TLS_CERT_PATH:
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_context.load_cert_chain(config.TLS_CERT_PATH, config.TLS_KEY_PATH)
    
    # Run with: uvicorn src.main:app --ssl-certfile ... --ssl-keyfile ...
```

---

## Health Checks and Monitoring

### Health Check Endpoint
```bash
curl https://gonggang.example.com/health

# Expected response:
{
  "status": "success",
  "data": {
    "status": "healthy",
    "version": "0.1.0",
    "environment": "production",
    "database": "connected",
    "timestamp": "2026-02-20T10:30:00Z"
  }
}
```

### Kubernetes Liveness Probe
```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
    scheme: HTTPS
  initialDelaySeconds: 30
  periodSeconds: 10
```

### Readiness Probe
```yaml
readinessProbe:
  httpGet:
    path: /health
    port: 8000
    scheme: HTTPS
  initialDelaySeconds: 5
  periodSeconds: 5
```

---

## Backup and Disaster Recovery

### Database Backup Strategy
```bash
# Daily automated backup
0 2 * * * pg_dump -h postgres.example.com -U gonggang_user gonggang | gzip > /backups/gonggang_$(date +\%Y\%m\%d).sql.gz

# Keep 30 days of backups
find /backups -name "gonggang_*.sql.gz" -mtime +30 -delete

# Test restore
gunzip < /backups/gonggang_20260220.sql.gz | psql $DATABASE_URL
```

### Disaster Recovery Procedure
1. Stop all running instances
2. Create new database (or restore from backup)
3. Run migrations: `alembic upgrade head`
4. Restart instances
5. Verify health: `curl /health`

---

## Performance Tuning

### PostgreSQL Configuration
```sql
-- In postgresql.conf for production:
max_connections = 100
shared_buffers = 256MB        # 25% of RAM
effective_cache_size = 1GB    # 50-75% of RAM
work_mem = 4MB
maintenance_work_mem = 64MB
wal_buffers = 16MB

-- Enable connection pooling (PgBouncer)
# Edit pgbouncer.ini
[databases]
gonggang = host=postgres.example.com port=5432 dbname=gonggang

[pgbouncer]
pool_mode = transaction
max_client_conn = 1000
default_pool_size = 25
```

### Application Tuning
```python
# src/lib/database.py
pool_size = 20  # Connections per app instance
max_overflow = 5
pool_pre_ping = True  # Validate connections before use
pool_recycle = 3600  # Recycle connections every hour
```

### OCR Optimization
```bash
# Tesseract configuration
export TESSERACT_CONFIG="--oem 1 --psm 3"  # Use neural net + simple layout

# Or use faster but less accurate mode for scheduling
export TESSERACT_CONFIG="--oem 1 --psm 6"  # Single uniform block
```

---

## Logging and Troubleshooting

### View Application Logs
```bash
# Docker
docker logs -f gonggang-api --tail=100

# Kubernetes
kubectl logs -f deployment/gonggang-api -n gonggang --tail=100

# File logs (if using logging to file)
tail -f /var/log/gonggang.log
```

### Common Issues

#### Database Connection Failed
```
Error: could not connect to server: Connection refused
```
**Solution**:
- Check DATABASE_URL is correct
- Verify PostgreSQL is running
- Test connection: `psql $DATABASE_URL -c "SELECT 1"`

#### OCR Timeout
```
Error: OCR parsing timeout after 3 seconds
```
**Solution**:
- Increase OCR_TIMEOUT_SECONDS in environment
- Reduce concurrent submissions (OCR_MAX_CONCURRENT)
- Upgrade server CPU

#### Batch Deletion Failures
```
Error: Failed to delete group due to foreign key constraint
```
**Solution**:
- Check for orphaned submissions (shouldn't happen with CASCADE)
- Run: `DELETE FROM submissions WHERE group_id = 'xxx'`
- Re-run batch deletion

---

## Rollback Procedure

### If New Deployment Causes Issues
```bash
# Kubernetes rolling back to previous version
kubectl rollout undo deployment/gonggang-api -n gonggang

# Verify rollback
kubectl rollout status deployment/gonggang-api -n gonggang

# View deployment history
kubectl rollout history deployment/gonggang-api -n gonggang
```

---

## Monitoring and Alerting

### Key Metrics to Monitor
1. **Request Latency**: P95, P99 response times for each endpoint
2. **Error Rate**: Percentage of 5xx responses
3. **OCR Success Rate**: Percentage of successful image parses
4. **Database Connections**: Active connections vs pool size
5. **Batch Deletion**: Last completed run, number of groups deleted
6. **Response Headers**: X-Poll-Wait, X-Response-Time correctness

### Alert Thresholds
| Metric | Threshold | Severity |
|--------|-----------|----------|
| POST /submissions P95 | > 5000ms | Critical |
| GET /free-time P95 | > 1000ms | High |
| OCR failure rate | > 5% | High |
| DB connection errors | > 1 per min | Critical |
| Batch deletion failure | > 1 per hour | Medium |

---

## Security Hardening

### Network Security
```bash
# Firewall rules (UFW example)
ufw allow 22/tcp          # SSH
ufw allow 443/tcp         # HTTPS
ufw allow 5432/tcp        # PostgreSQL (restricted to app servers)
ufw enable
```

### Application Security Headers
```python
# src/main.py - Add to app
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response
```

### SQL Injection Protection
- ✅ SQLAlchemy ORM prevents injection by default
- ✅ All inputs validated via Pydantic
- ✅ No dynamic SQL construction

### DDoS Protection
- Rate limiting: 100 req/min per IP
- Request size limit: 10MB max image
- Polling minimum: 2000ms between requests (enforced server-side)

---

## Maintenance Schedule

| Task | Frequency | Owner |
|------|-----------|-------|
| Database backup | Daily | DevOps |
| Backup restore test | Weekly | DevOps |
| Log rotation | Daily | System |
| Security updates | As available | DevOps |
| Dependency updates | Monthly | Development |
| Performance review | Monthly | DevOps |
| Capacity planning | Quarterly | DevOps |

---

**Document Version**: 1.0  
**Last Updated**: 2026-02-20  
**Deployment Contact**: devops@example.com
