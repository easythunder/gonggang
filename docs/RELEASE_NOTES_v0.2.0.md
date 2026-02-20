# Release Notes Template (T099)

## Release Notes: Meet-Match v0.2.0

**Release Date**: [DATE]  
**Branch**: `main`  
**Deployed to**: Production  

---

## Overview
Brief summary of major changes, new features, and improvements in this release.

Example: "This release focuses on performance optimization and operational hardening. Group expiration now triggers faster batch deletion, and OCR processing can handle 50% more concurrent requests."

---

## New Features ✨

### Feature 1: [Feature Name]
- **Description**: What it does and why it matters
- **API Changes**: Any new endpoints or parameter changes
- **Migration Required**: If database schema changes needed
- **Example**:
  ```bash
  curl -X POST http://localhost:8000/groups \
    -H "Content-Type: application/json" \
    -d '{"group_name": "study_group", "display_unit_minutes": 30}'
  ```

### Feature 2: Caching for Free-Time Results (T079)
- **Description**: GET /free-time results cached for 2 seconds; significant reduction in calculation overhead
- **Impact**: P95 polling response time: 200ms → 50ms
- **Cache Invalidation**: Automatic on new submission or deletion

---

## Improvements 🚀

### Performance
- OCR concurrent processing increased from 3 to 5 (T080)
- Database indexes optimized for common queries (T078)
  - Added: `idx_group_expires_at`
  - Added: `idx_submission_group_nickname`
- Batch deletion now processes 100 groups per cycle (was 50)
- **Result**: Peak load response time reduced 30%

### Observability
- Health check endpoint now includes database status (T095)
- Metrics collection added for all endpoints (T077)
- New health check headers in responses: `X-Response-Time`, `X-Calculation-Version`

### Reliability
- Graceful shutdown: Application drains in-flight requests before stopping (T098)
- Batch deletion retry logic improved with exponential backoff (T069)
- Database connection pool sizing recommendations updated

---

## Bug Fixes 🐛

### Critical
- Fixed: Group expiration check not triggering 410 response in all cases
  - **Impact**: Users couldn't detect expired groups reliably
  - **Fix**: Lazy deletion now always checks expires_at before returning data

### Medium
- Fixed: OCR memory not released after processing large images
  - **Impact**: Memory leak on high-volume submissions
  - **Fix**: Explicit image buffer cleanup in OCRService.parse_schedule()

### Low
- Fixed: Typo in error message for invalid display_unit_minutes
- Fixed: Response time header format not matching spec

---

## Breaking Changes ⚠️

None in this release.

**Note**: If upgrading from v0.1.x, no data migration required.

---

## Deprecations 📌

None in this release.

---

## Database Changes

### New Tables
None

### Schema Changes
```sql
-- Add index for batch deletion performance
CREATE INDEX idx_group_expires_at ON groups(expires_at) WHERE deleted_at IS NULL;
```

### Migration Steps
```bash
# Automatic on startup: alembic upgrade head
# Or manually: psql $DATABASE_URL < migrations/003_add_indexes.sql
```

---

## Deployment Instructions

### Prerequisites
- Python 3.11+
- PostgreSQL 14+
- Tesseract OCR (or PaddleOCR)

### Step 1: Pull New Version
```bash
git fetch origin
git checkout v0.2.0
```

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Run Migrations
```bash
alembic upgrade head
# Or for K8s: kubectl apply -f k8s/migration-job.yaml
```

### Step 4: Deploy
```bash
# Docker
docker build -t gonggang:0.2.0 .
docker push gonggang:0.2.0
docker run -e DATABASE_URL=$DATABASE_URL gonggang:0.2.0

# Kubernetes
kubectl set image deployment/gonggang-api gonggang-api=gonggang:0.2.0 -n gonggang
kubectl rollout status deployment/gonggang-api -n gonggang
```

### Step 5: Verify
```bash
curl https://gonggang.example.com/health
# Expected: {"status": "success", "data": {"status": "healthy", ...}}
```

### Rollback (If Needed)
```bash
# Kubernetes
kubectl rollout undo deployment/gonggang-api -n gonggang

# Or specify previous version
kubectl set image deployment/gonggang-api gonggang-api=gonggang:0.1.0 -n gonggang
```

---

## Known Issues 🔴

### Issue 1: OCR Accuracy with Low-Quality Images
- **Severity**: Medium
- **Workaround**: Upload high-contrast schedule images (JPG/PNG, >800x600px)
- **Fix**: Planned for v0.3.0 (image preprocessing)

### Issue 2: Batch Deletion May Take >5 minutes for 1000+ Groups
- **Severity**: Low
- **Workaround**: Run multiple batch deletion instances in parallel
- **Fix**: Planned for v0.3.0 (async task queue)

---

## Performance Benchmarks

| Operation | v0.1.0 | v0.2.0 | Improvement |
|-----------|--------|--------|-------------|
| POST /submissions (with OCR) | 4.2s | 3.8s | 10% ↓ |
| GET /free-time (P95) | 200ms | 50ms | 75% ↓ |
| Batch delete 100 groups | 15s | 8s | 47% ↓ |
| OCR parse (mean) | 1.8s | 1.6s | 11% ↓ |

---

## Test Coverage

| Component | Coverage v0.1.0 | Coverage v0.2.0 | Target |
|-----------|-----------------|-----------------|--------|
| API Endpoints | 78% | 89% | 85% |
| Services | 62% | 75% | 85% |
| Repositories | 45% | 58% | 85% |
| **Overall** | **62%** | **75%** | **85%** |

---

## Dependency Updates

### Updated
- FastAPI: 0.95.2 → 0.104.1
- SQLAlchemy: 2.0.16 → 2.0.24
- Pydantic: 1.10.7 → 2.5.0

### Added
- prometheus-client==0.19.0 (metrics export)
- python-json-logger==2.0.7 (structured logging)

### Removed
- None

---

## Contributors

- [@developer1](https://github.com/developer1) - Performance optimization
- [@developer2](https://github.com/developer2) - Bug fixes and testing
- [@devops1](https://github.com/devops1) - Deployment and monitoring

---

## Special Thanks

Thanks to all testers and early adopters for feedback on v0.1.0!

---

## Next Steps / Roadmap

### v0.3.0 (Planned for [DATE])
- Async task queue for OCR processing
- Advanced image preprocessing
- Calendar integration (iCal export)
- User accounts and persistent groups

### v0.4.0 (Planned for [DATE])
- Mobile app native support
- Group chat/discussion feature
- Public group discovery
- Email notifications

---

## Support

- **Documentation**: [docs.example.com/gonggang](https://docs.example.com/gonggang)
- **Issues**: [github.com/company/gonggang/issues](https://github.com/company/gonggang/issues)
- **Slack**: #gonggang in Company Slack
- **Email**: gonggang-support@example.com

---

## License

MIT License - See LICENSE file for details

---

**Release Manager**: [@devops-lead](https://github.com/devops-lead)  
**QA Sign-off**: ✅ Approved by [@qa-lead](https://github.com/qa-lead)  
**Product Owner Sign-off**: ✅ Approved by [@product-lead](https://github.com/product-lead)
