---
name: Performance Issue 🚀
about: Report performance degradation or optimization opportunities
title: "[PERF] "
labels: "performance"
assignees: ""
---

## Description
<!-- Description of the performance issue -->

## Affected Endpoint/Component
- [ ] POST /groups
- [ ] POST /submissions
- [ ] GET /free-time
- [ ] GET /deletion-logs
- [ ] Other: _______________

## Current Behavior
```
Actual response time: XXXms
Current P95: XXXms
Current P99: XXXms
Error rate: X%
```

## Expected Behavior
```
Target response time: XXXms
Target P95: XXXms
Target P99: XXXms
Target error rate: X%
```

## Performance Metrics
- **Test Setup**: (concurrent users, request rate, etc)
- **Database**: PostgreSQL version, connection pool size
- **Deployment**: Docker / Kubernetes / Local
- **Load**: (peak requests/sec, typical load, etc)

## Reproduction
```bash
# Command to reproduce the issue
# Example: ab -n 1000 -c 50 http://localhost:8000/free-time
```

## Profiling Data
<!-- Attach any profiling data, flame graphs, or benchmarks -->
```
Example output from src/metrics.py or profiling tool
```

## Root Cause Analysis (if known)
<!-- Have you identified the bottleneck? -->
- [ ] Database query
- [ ] OCR processing
- [ ] API response time
- [ ] Memory usage
- [ ] Other: _______________

## Proposed Solution
<!-- How would you fix this? -->

## Environment
- **OS**: [e.g., macOS 14.1]
- **Python Version**: [e.g., 3.11.6]
- **FastAPI Version**: [e.g., 0.104.1]
- **PostgreSQL Version**: [e.g., 14.2]
- **Deployment**: [Docker / Kubernetes / Local]

## Related Issues
<!-- Link any related issues with #123 -->
