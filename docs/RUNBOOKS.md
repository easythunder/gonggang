# Operational Runbooks (T097)

## Common Operational Tasks

### 1. Manual Group Deletion

**Scenario**: Need to immediately delete a group (user request, data corruption)

#### Via CLI
```bash
# Using CLI (recommended)
python -m src.cli.batch_deletion \
  --group-id <group-uuid> \
  --force \
  --reason "user_request"

# Dry-run to preview
python -m src.cli.batch_deletion \
  --group-id <group-uuid> \
  --dry-run
```

#### Via Database (Emergency Only)
```bash
# Connect to database
psql $DATABASE_URL

-- Get group ID
SELECT id, name, expires_at FROM groups WHERE name ILIKE '%search_term%';

-- Delete group (cascades to submissions/intervals/results)
DELETE FROM groups WHERE id = 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx';

-- Verify deletion
SELECT COUNT(*) FROM groups WHERE id = 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx';  -- Should be 0
```

---

### 2. Retry Failed Batch Deletion

**Scenario**: Batch deletion failed for some groups; need to retry

#### Check Failed Deletions
```bash
psql $DATABASE_URL

-- Find groups with failed deletion attempts
SELECT 
  dr.group_id,
  dr.failure_count,
  dr.last_failure_at,
  dr.next_retry_at,
  g.name
FROM deletion_retries dr
LEFT JOIN groups g ON dr.group_id = g.id
WHERE failure_count > 0 AND next_retry_at <= NOW()
ORDER BY next_retry_at ASC;
```

#### Trigger Retry
```bash
# Kubernetes - trigger job immediately
kubectl create job --from=cronjob/gonggang-batch-deletion \
  gonggang-batch-deletion-manual-$(date +%s) \
  -n gonggang

# Docker - run container
docker run --rm \
  -e DATABASE_URL=$DATABASE_URL \
  gonggang:0.1.0 \
  python -m src.cli.batch_deletion

# Standalone
python -m src.cli.batch_deletion --force
```

#### Monitor Retry Progress
```bash
# Watch logs
kubectl logs -f -l job=gonggang-batch-deletion-manual-* -n gonggang

# Check remaining failures
psql $DATABASE_URL -c "
  SELECT COUNT(*) as pending_retries
  FROM deletion_retries
  WHERE failure_count > 0 AND failure_count < 3
"
```

---

### 3. Update OCR Library

**Scenario**: Switch from Tesseract to PaddleOCR, or upgrade version

#### Update Dependencies
```bash
# Edit requirements.txt
# From: pytesseract==0.3.10
# To:   paddleocr==2.7.0.3

pip install -r requirements.txt

# Verify new library works
python -c "
from src.services.ocr import OCRService
ocr = OCRService()
print(f'OCR Library: {ocr.library}')
"
```

#### Update Environment Configuration
```bash
# Change OCR library
export OCR_LIBRARY=paddleocr  # was 'tesseract'
export OCR_TIMEOUT_SECONDS=5  # PaddleOCR usually slower

# Restart application
docker restart gonggang-api
# or
kubectl rollout restart deployment/gonggang-api -n gonggang
```

#### Validate on Test Group
```bash
# Create test group and upload test image
curl -X POST http://localhost:8000/groups \
  -H "Content-Type: application/json" \
  -d '{"display_unit_minutes": 30}'

# Get group_id from response
GROUP_ID="..."

# Upload test image
curl -X POST http://localhost:8000/groups/$GROUP_ID/submissions \
  -F "file=@test_schedule.jpg"

# Verify response
curl http://localhost:8000/groups/$GROUP_ID/free-time
```

---

### 4. Scale OCR Processing

**Scenario**: OCR queue is backing up; users experience timeouts

#### Root Cause Analysis
```bash
# Check OCR failure rate
psql $DATABASE_URL -c "
  SELECT 
    DATE_TRUNC('minute', submitted_at) as minute,
    COUNT(*) as total,
    SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END) as failed,
    ROUND(100.0*SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END)/COUNT(*), 1) as failure_pct
  FROM submissions
  WHERE submitted_at > NOW() - INTERVAL '1 hour'
  GROUP BY minute
  ORDER BY minute DESC;
"

# Check response times
kubectl logs -n gonggang -l app=gonggang-api --tail=1000 | grep "POST /groups" | tail -20
```

#### Increase OCR Concurrency
```bash
# Increase OCR_MAX_CONCURRENT
export OCR_MAX_CONCURRENT=5  # Was 3

# Restart application
docker restart gonggang-api
# or
kubectl set env deployment/gonggang-api \
  OCR_MAX_CONCURRENT=5 \
  -n gonggang

# Monitor change
kubectl logs -f -l app=gonggang-api -n gonggang | grep "OCR"
```

#### If Still Overwhelmed: Use Async Queue (Future Enhancement)
```bash
# Plan: Add Celery/RabbitMQ for async OCR
# Current: POST /submissions blocks on OCR
# Future: POST /submissions → immediate response + async OCR processing + webhook on completion
```

---

### 5. Database Emergency - Connection Pool Exhausted

**Scenario**: All database connections in pool are used; new requests fail

#### Diagnose
```bash
psql $DATABASE_URL -c "
  SELECT count(*) as connections,
         state,
         wait_event
  FROM pg_stat_activity
  GROUP BY state, wait_event
  ORDER BY count(*) DESC;
"

# Check pool size in app
# Expected: pool_size=20 + max_overflow=5
```

#### Short-term Recovery
```bash
# Kill idle connections
psql $DATABASE_URL -c "
  SELECT pg_terminate_backend(pid)
  FROM pg_stat_activity
  WHERE state = 'idle' 
    AND query_start < NOW() - INTERVAL '5 minutes'
    AND pid != pg_backend_pid();
"

# Restart app (reconnect with fresh pool)
docker restart gonggang-api
# or
kubectl rollout restart deployment/gonggang-api -n gonggang
```

#### Long-term Fix
```bash
# Increase pool size in src/lib/database.py
pool_size = 30  # Was 20
max_overflow = 10  # Was 5

# Deploy new version
docker build -t gonggang:0.1.1 .
kubectl set image deployment/gonggang-api gonggang-api=gonggang:0.1.1 -n gonggang
```

---

### 6. PII Data Cleanup (GDPR Right to be Forgotten)

**Scenario**: User requests all their data be deleted

#### Option 1: Delete via Group ID (If you have it)
```bash
# Find group
psql $DATABASE_URL -c "
  SELECT g.id, g.name, COUNT(s.id) as submissions
  FROM groups g
  LEFT JOIN submissions s ON g.id = s.group_id
  WHERE g.name ILIKE '%user_search_term%'
  GROUP BY g.id
  LIMIT 5;
"

# Delete group + all submissions
python -m src.cli.batch_deletion --group-id <group-uuid> --force

# Verify deletion
psql $DATABASE_URL -c "
  SELECT * FROM deletion_logs 
  WHERE group_id = '<group-uuid>'
  ORDER BY deleted_at DESC LIMIT 1;
"
```

#### Option 2: Delete via Submission Nickname (If known)
```bash
psql $DATABASE_URL -c "
  -- Find all groups with this nickname
  SELECT DISTINCT g.id
  FROM groups g
  INNER JOIN submissions s ON g.id = s.group_id
  WHERE s.nickname = 'user_nickname';
"

# Then use Option 1 for each group
```

#### Verification
```bash
psql $DATABASE_URL -c "
  -- Verify no user data remains
  SELECT COUNT(*) FROM submissions WHERE nickname = 'user_nickname';  -- Should be 0
  
  -- Check deletion log was created
  SELECT * FROM deletion_logs WHERE reason = 'gdpr_request' ORDER BY deleted_at DESC;
"
```

---

### 7. Backup and Restore

**Scenario**: Need to restore from backup after data loss

#### Create Backup
```bash
# Full database backup
pg_dump -h postgres.example.com -U gonggang_user -d gonggang | gzip > gonggang_backup_$(date +%Y%m%d_%H%M%S).sql.gz

# Verify backup is readable
gunzip -t gonggang_backup_20260220_102030.sql.gz

# Store securely
aws s3 cp gonggang_backup_20260220_102030.sql.gz s3://backups/gonggang/
```

#### Restore from Backup
```bash
# 1. Stop application to prevent writes
kubectl scale deployment gonggang-api --replicas=0 -n gonggang

# 2. Create new database or drop existing
# WARNING: This deletes all current data
psql -U gonggang_user -c "DROP DATABASE gonggang;"
psql -U gonggang_user -c "CREATE DATABASE gonggang ENCODING UTF8;"

# 3. Restore from backup
gunzip < gonggang_backup_20260220_102030.sql.gz | psql -U gonggang_user -d gonggang

# 4. Verify data integrity
psql -U gonggang_user -d gonggang -c "
  SELECT 
    (SELECT COUNT(*) FROM groups) as groups,
    (SELECT COUNT(*) FROM submissions) as submissions,
    (SELECT COUNT(*) FROM intervals) as intervals,
    (SELECT COUNT(*) FROM group_free_time_results) as results;
"

# 5. Restart application
kubectl scale deployment gonggang-api --replicas=3 -n gonggang
```

---

### 8. Performance Degradation Investigation

**Scenario**: Application is slow; need to debug

#### Step 1: Identify Slow Queries
```bash
psql $DATABASE_URL -c "
  SELECT 
    mean_exec_time as avg_ms,
    max_exec_time as max_ms,
    calls,
    query
  FROM pg_stat_statements
  ORDER BY mean_exec_time DESC
  LIMIT 10;
"
```

#### Step 2: Check Index Usage
```bash
psql $DATABASE_URL -c "
  SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan as scans,
    idx_tup_read as tuples_read
  FROM pg_stat_user_indexes
  WHERE idx_scan = 0  -- Unused indexes
  ORDER BY pg_relation_size(indexrelid) DESC;
"
```

#### Step 3: Analyze Execution Plan
```bash
psql $DATABASE_URL -c "
  EXPLAIN ANALYZE
  SELECT *
  FROM group_free_time_results
  WHERE group_id = 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'
  ORDER BY version DESC
  LIMIT 1;
"
```

#### Step 4: Get Memory/CPU Usage
```bash
# Kubernetes
kubectl top pod -l app=gonggang-api -n gonggang

# Docker
docker stats gonggang-api --no-stream
```

---

### 9. Emergency Maintenance Window

**Scenario**: Need to perform database maintenance; must take service offline

#### Announce Maintenance
```bash
# Update status page or send notification to users
echo "Scheduled maintenance 2026-02-21 02:00-03:00 UTC for database optimization."
```

#### Execute
```bash
# 1. Stop accepting new requests
kubectl patch deployment gonggang-api -p '{"spec":{"replicas":0}}' -n gonggang

# 2. Wait for in-flight requests to complete (10-30 seconds)
sleep 30

# 3. Perform maintenance
psql $DATABASE_URL -c "
  VACUUM ANALYZE;  -- Update table statistics
  REINDEX INDEX idx_group_expires_at;  -- Rebuild index
  CLUSTER groups USING idx_group_expires_at;  -- Optimize storage
"

# 4. Restart application
kubectl patch deployment gonggang-api -p '{"spec":{"replicas":3}}' -n gonggang

# 5. Verify healthy
curl https://gonggang.example.com/health

# 6. Clear maintenance message
echo "Maintenance complete."
```

---

### 10. Audit: Who Deleted What and When?

**Scenario**: Track deletion history for compliance/debugging

#### Query Deletion Log
```bash
psql $DATABASE_URL -c "
  SELECT 
    group_id,
    deleted_at,
    reason,
    submission_count,
    error_code,
    notes
  FROM deletion_logs
  WHERE deleted_at > NOW() - INTERVAL '7 days'
  ORDER BY deleted_at DESC;
" | column -t -s '|'

# Or with group details
SELECT 
  dl.deleted_at,
  COALESCE(g.name, dl.group_id::text) as group_name,
  dl.submission_count,
  dl.reason,
  dl.retry_count
FROM deletion_logs dl
LEFT JOIN groups g ON dl.group_id = g.id
WHERE dl.deleted_at > NOW() - INTERVAL '30 days'
ORDER BY dl.deleted_at DESC;
```

---

## Alert Response Procedures

### Alert: High Error Rate (>5%)
1. Check logs: `kubectl logs -l app=gonggang-api -n gonggang --tail=100`
2. Identify error pattern (OCR timeout? DB connection? Invalid input?)
3. **OCR Timeout**: Increase OCR_MAX_CONCURRENT or OCR_TIMEOUT_SECONDS
4. **DB Connection**: Check connection pool, restart if needed
5. **Invalid Input**: Check API spec compliance in client

### Alert: Slow Response Time (P95 > 1s)
1. Check database performance: `EXPLAIN ANALYZE SELECT ...`
2. Check server CPU/Memory: `kubectl top pod -n gonggang`
3. Check OCR latency: Look for "OCR" in logs
4. Add database index if needed query is full table scan
5. Scale horizontally if consistently overloaded

### Alert: Batch Deletion Failed (3+ retries)
1. Check deletion_retries table: `SELECT * FROM deletion_retries WHERE failure_count = 3;`
2. Check logs for error messages
3. Manually delete problem group if unrecoverable
4. Investigate root cause (FK constraint? Corrupt data?)

---

**Document Version**: 1.0  
**Last Updated**: 2026-02-20  
**On-Call Rotation**: See Slack #gonggang-oncall
