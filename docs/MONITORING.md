# Monitoring and Observability (T094)

## Key Metrics to Track

### Request Metrics

#### Response Times (Latency)
- **Endpoint**: All HTTP endpoints
- **Metrics**:
  - Mean response time (ms)
  - Median (P50)
  - 95th percentile (P95)
  - 99th percentile (P99)
  - Maximum (P100)

| Endpoint | Target P95 | Alert Threshold | Notes |
|----------|-----------|--------------|-------|
| POST /groups | <100ms | >500ms | Simple insert |
| POST /groups/{id}/submissions | <5s | >8s | Includes OCR (1-3s) |
| GET /groups/{id}/free-time | <500ms | >1s | Cached reads |
| DELETE /groups/{id}/submissions/{id} | <1s | >3s | DB update |
| GET /health | <50ms | >200ms | Probe response |

#### Request Volume
- **Metric**: Requests per minute (RPM)
- **By Endpoint**:
  - POST /groups (group creation rate)
  - POST /groups/{id}/submissions (submission rate)
  - GET /groups/{id}/free-time (polling rate)
  - DELETE /groups/{id}/submissions/{id} (deletion rate)

#### Error Metrics
- **5xx Error Rate**: Percentage of server errors
  - Alert: >1% or >5 errors/min
- **4xx Error Rate**: Percentage of client errors
  - Monitor: Indicates API misuse
- **Error by Type**: Count of specific error codes
  - 408 Timeout (OCR timeout)
  - 410 Gone (Expired group)
  - 429 Too Many Requests

### Application Metrics

#### OCR Processing
- **Success Rate**: Percentage of successful OCR parses
  - Alert: <95% success rate
- **Latency**: Time to parse image
  - Mean: Usually 1-2 seconds
  - Alert: P95 > 3 seconds
- **Queue Depth**: Number of pending OCR jobs
  - Alert: >10 pending

#### Calculation Performance
- **Duration**: Time to compute free-time intersection
  - Target: <1 second for 50 participants
  - Alert: >2 seconds
- **Cache Hit Rate**: Percentage of results served from cache
  - Target: >80% (same calculation within cache window)

#### Database Metrics
- **Connection Pool Usage**: Active/idle connections
  - Alert: >90% utilization
- **Query Latency**: Slow query tracking
  - Alert: >1s for any single query
- **Index Hit Rate**: Percentage of queries using indexes
  - Target: >95%
  - Low hit rate indicates missing indexes
- **Database Size**: Total data consumption
  - Alert: Growing >10% month-over-month
- **Replication Lag**: (If using replicas)
  - Alert: >10 seconds behind primary

#### Batch Deletion
- **Last Run**: When batch job last completed
  - Alert: >30 minutes without completion
- **Groups Deleted**: Count per run
  - Typical: 50-200 groups per day
- **Success Rate**: Percentage of successful deletions
  - Alert: <95% success
- **Failure Retries**: Groups needing retry
  - Alert: >10 groups in retry queue >1hr

### System Metrics

#### Server Resources
- **CPU Usage**: Percentage utilization
  - Alert: >80% sustained (1min average)
- **Memory Usage**: Percentage of available memory
  - Alert: >85% usage
- **Disk Usage**: Database + logs storage
  - Alert: >90% full
- **Network I/O**: Bytes in/out per second
  - Monitor: Baseline for capacity planning

#### Availability
- **Uptime**: Percentage of time service is available
  - Target: 99.5% (4.3 hours downtime/month)
- **MTTF** (Mean Time To Failure): Average time between incidents
  - Target: >7 days
- **MTTR** (Mean Time To Recovery): Average recovery time
  - Target: <15 minutes

---

## Monitoring Dashboard Template

### Grafana Dashboard Configuration

#### Panel 1: Response Time Heatmap
```json
{
  "title": "Response Times by Endpoint (P95)",
  "targets": [
    {
      "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) by (endpoint)"
    }
  ],
  "alert": {
    "name": "SlowResponse",
    "condition": "avg() > 1",  // 1 second target
    "evaluateFor": "5m"
  }
}
```

#### Panel 2: Error Rate (%)
```json
{
  "title": "Error Rate by Endpoint",
  "targets": [
    {
      "expr": "rate(http_requests_total{status=~'5..'}[5m]) / rate(http_requests_total[5m]) * 100"
    }
  ],
  "alert": {
    "name": "HighErrorRate",
    "condition": "avg() > 1",  // 1% threshold
    "evaluateFor": "5m"
  }
}
```

#### Panel 3: OCR Performance
```json
{
  "title": "OCR Processing",
  "targets": [
    {
      "expr": "rate(ocr_parse_duration_seconds_sum[5m])"
    },
    {
      "expr": "rate(ocr_parse_errors_total[5m])"
    }
  ]
}
```

#### Panel 4: Database Connection Pool
```json
{
  "title": "Database Connections",
  "targets": [
    {
      "expr": "sqlalchemy_pool_connections_active",
      "legend": "Active"
    },
    {
      "expr": "sqlalchemy_pool_connections_idle",
      "legend": "Idle"
    },
    {
      "expr": "sqlalchemy_pool_size",
      "legend": "Max Size"
    }
  ]
}
```

#### Panel 5: Batch Deletion Status
```json
{
  "title": "Batch Deletion (Last 24h)",
  "targets": [
    {
      "expr": "increase(deletion_jobs_total[24h])"
    },
    {
      "expr": "increase(deletion_jobs_failed_total[24h])"
    },
    {
      "expr": "increase(groups_deleted_total[24h])"
    }
  ]
}
```

---

## Alert Configuration

### Critical Alerts (Page Oncall)

#### 1. Application Down
```yaml
alert: ApplicationDown
expr: up{job="gonggang-api"} == 0
for: 2m
labels:
  severity: critical
annotations:
  summary: "Gonggang API is down"
  action: "Check Kubernetes pod status: kubectl get pods -n gonggang"
```

#### 2. High Error Rate
```yaml
alert: HighErrorRate
expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.01
for: 5m
labels:
  severity: critical
annotations:
  summary: "Error rate > 1%"
  action: "Check logs: kubectl logs -l app=gonggang-api -n gonggang"
```

#### 3. Database Connection Pool Exhausted
```yaml
alert: DBConnectionPoolExhausted
expr: sqlalchemy_pool_connections_active / sqlalchemy_pool_size > 0.9
for: 2m
labels:
  severity: critical
annotations:
  summary: "DB connection pool exhausted"
  action: "Increase pool_size or restart: kubectl rollout restart deployment/gonggang-api"
```

### High Priority Alerts (Page after 30min if not acknowledged)

#### 4. Slow API Response
```yaml
alert: SlowAPIResponse
expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{endpoint=~"/groups.*"}[5m])) > 2
for: 10m
labels:
  severity: high
annotations:
  summary: "API P95 response time > 2s"
  action: "Check database slow queries or OCR latency"
```

#### 5. Batch Deletion Failed
```yaml
alert: BatchDeletionFailed
expr: time() - timestamp(deletion_last_run_timestamp) > 1800
for: 5m
labels:
  severity: high
annotations:
  summary: "Batch deletion hasn't run in 30min"
  action: "Check cronjob status: kubectl describe cronjob gonggang-batch-deletion -n gonggang"
```

### Medium Priority Alerts (Slack notification)

#### 6. OCR Timeout Rate Elevated
```yaml
alert: OCRTimeouts
expr: rate(ocr_parse_timeout_total[5m]) > 0.1
for: 10m
labels:
  severity: medium
annotations:
  summary: "OCR timeout rate > 10%"
  action: "Increase OCR_TIMEOUT_SECONDS or reduce OCR_MAX_CONCURRENT"
```

---

## Logging Strategy

### Structured Logging Format
All logs should be in JSON format for parsing:
```json
{
  "timestamp": "2026-02-20T10:30:45.123456Z",
  "level": "INFO",
  "logger": "src.api.groups",
  "message": "Group created successfully",
  "request_id": "req_123abc",
  "user_ip": "203.0.113.45",
  "endpoint": "POST /groups",
  "status_code": 201,
  "duration_ms": 45,
  "group_id": "550e8400-e29b-41d4-a716-446655440000",
  "group_name": "study_group_2026",
  "context": {
    "display_unit_minutes": 30
  }
}
```

### Log Levels and Usage

| Level | When to Use | Example |
|-------|-----------|---------|
| DEBUG | Detailed development info | "Database query executed: SELECT ..." |
| INFO | Important business events | "Group created", "Submission success" |
| WARNING | Potentially problematic | "OCR slow (2.5s)", "Group about to expire" |
| ERROR | Error conditions | "OCR timeout after 3s", "DB connection failed" |
| CRITICAL | System failure | "All DB connections lost", "Disk full" |

### Log Retention
- **Application logs**: 30 days in centralized logging (Datadog, Loki, etc.)
- **Audit logs**: 90 days (deletion events, GDPR requests)
- **Debug logs**: 7 days (verbose SQL, cache hits, etc.)

---

## Custom Metrics (Prometheus)

### Define Custom Metrics
```python
# src/metrics.py
from prometheus_client import Counter, Histogram, Gauge

# Counter: Total requests by endpoint
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

# Histogram: Request duration
http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    ['endpoint'],
    buckets=[0.01, 0.05, 0.1, 0.5, 1, 2, 5]
)

# Gauge: OCR queue depth
ocr_queue_depth = Gauge(
    'ocr_queue_depth',
    'Current OCR jobs queued'
)

# Counter: Groups deleted
groups_deleted_total = Counter(
    'groups_deleted_total',
    'Total groups deleted',
    ['reason']  # 'expired', 'manual', 'error_cleanup'
)
```

### Expose Metrics Endpoint
```python
# src/main.py
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(
        generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )
```

---

## SLA and SLO

### Service Level Objectives (SLOs)

| Metric | Objective | Notes |
|--------|-----------|-------|
| Availability | 99.5% | 4.3 hours downtime/month allowed |
| Response Time (P99) | <2s | For normal operations |
| Error Rate | <0.5% | 5xx errors only |
| Group Deletion | <72h + 5min tolerance | Lazy check + batch job |
| OCR Success | >98% | Parseable image requirement |

### Tracking SLO Compliance
```sql
-- Calculate monthly availability
SELECT 
  DATE_TRUNC('month', timestamp) as month,
  SUM(CASE WHEN status = 'up' THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as availability_pct
FROM health_check_log
GROUP BY month
ORDER BY month DESC;
```

---

**Document Version**: 1.0  
**Last Updated**: 2026-02-20  
**Metrics Contact**: metrics@example.com
