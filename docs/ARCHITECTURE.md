"""
Architecture and design decisions (T090)

Documents the high-level architecture, key design decisions,
and rationale for the Meet-Match system.
"""

# Architecture and Design Decisions

## System Architecture

### High-Level Overview

Meet-Match is a stateless, horizontally scalable FastAPI application that performs:
1. **Group Management** - Create groups with optional names and display units
2. **Image Processing** - OCR parsing of schedule images (memory-only, no disk)
3. **Calculation** - Real-time AND logic calculation of free time across participants
4. **Results API** - Server-enforced polling with JSON responses
5. **Cleanup** - Automatic 72-hour expiration with batch deletion

### Key Components

#### API Layer (src/api/)
- **groups.py** - Group CRUD endpoints
- **submissions.py** - Image upload and processing
- **free_time.py** - Results polling with lazy expiration checks

#### Service Layer (src/services/)
- **GroupService** - Group lifecycle management
- **SubmissionService** - Submission creation with OCR parsing
- **CalculationService** - Free-time intersection logic
- **CandidateExtractor** - Converts intervals to ranked candidates
- **AvailabilityGridService** - Weekly grid generation for UI
- **BatchDeletionService** - Scheduled cleanup with retry logic
- **DeletionService** - Lazy deletion checks

#### Data Access Layer (src/repositories/)
- Repository pattern for CRUD operations on models
- Session management with database connection pooling

#### Infrastructure (src/lib/)
- **database.py** - PostgreSQL connection management
- **slot_utils.py** - Time slot normalization (5-min granularity, conservative)
- **nickname.py** - 3-word adjective+noun generation
- **polling.py** - Server-enforced polling interval (2-3 seconds)
- **logging.py** - JSON structured logging with PII masking
- **utils.py** - Response formatting, error codes

---

## Design Decisions and Rationale

### 1. Memory-Only Image Processing
**Decision**: Images are never saved to disk. Parsed during request and discarded.

**Rationale**:
- **Privacy**: No persistent storage of potentially sensitive schedule data
- **Cost**: Eliminates need for object storage (S3, GCS)
- **Simplicity**: Reduces deployment complexity and cleanup requirements

**Trade-offs**: Larger request body processing, but acceptable for <5MB images

---

### 2. AND Logic for Free Time Calculation
**Decision**: Free time = intersection of ALL participant schedules

**Rationale**:
- **Correctness**: Only times when everyone is free should be suggested
- **Simplicity**: Mathematically clean - (A ∪ B ∪ C)^c = A^c ∩ B^c ∩ C^c
- **Conservative**: Defaults to "everyone must be available"

**Algorithm**:
```
For each time slot:
  available_count = sum(participants not busy in slot)
  is_free = (available_count == total_participants)
```

**Complexity**: O(n_participants × slots_per_week)

---

### 3. 5-Minute Slot Granularity
**Decision**: Normalize all times to 5-minute boundaries (ceiling start, floor end)

**Rationale**:
- **Practicality**: Most schedulers use 15-30min units; 5min is reasonable sub-unit
- **Conservative**: Ceiling for start time ensures we don't over-count availability
- **Grid Size**: 7 days × 288 slots (1440 min / 5) = 2,016 total slots (manageable)

**Example**:
- Busy 9:15-9:45 → rounds to 9:15-9:45 (no free slots for 30-min interval)
- Busy 9:00-9:12 → rounds to 9:00-9:15 (loses 3 min overlap, conservative)

---

### 4. Server-Enforced Polling (2-3 seconds)
**Decision**: Server rejects client `interval_ms` parameter and enforces 2000-3000ms range

**Rationale**:
- **API Contract**: Prevents abusive polling rates (>1 req/sec from single client)
- **User Experience**: 2-3s is responsive enough for web/mobile
- **Consistency**: All clients get same update cadence

**Implementation**: `X-Poll-Wait` header and rate limiting per client IP

---

### 5. Lazy Deletion + Batch Job
**Decision**: Two-stage deletion process:
1. **Lazy**: Check `expires_at` on access, return 410 Gone if expired
2. **Batch**: Periodic job (every 5-15 min) scans and cascade-deletes

**Rationale**:
- **Performance**: Lazy deletion avoids TTL indices; batch handles cleanup
- **Reliability**: Batch job handles edge cases (partial failures, retries)
- **Observability**: DeletionLog tracks when/why deletions occur

**Retry Strategy**: Exponential backoff at 1min, 5min, 15min intervals (max 3 retries)

---

### 6. Cascade Deletion
**Decision**: Deleting a Group cascades to Submissions → Intervals → Results

**Rationale**:
- **Data Integrity**: Prevents orphaned submissions/intervals
- **Simplicity**: Single DELETE query (via FK constraints)
- **GDPR**: Ensures all participant data is removed

**Database**:
```sql
ALTER TABLE submissions ADD CONSTRAINT fk_group_id
  FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE
```

---

### 7. Nickname Auto-Generation
**Decision**: 3-word random "adjective_adjective_noun" format (e.g., "happy_blue_lion")

**Rationale**:
- **Collision Resistance**: 10,000+ combinations, acceptable collision rate
- **Anonymity**: Pseudonymous but memorable (vs UUIDs)
- **User-Friendly**: Easier to reference in conversation ("use happy_blue_lion's times")

**Collision Handling**: Retry up to 3 times if duplicate detected

---

### 8. Version Control for Results
**Decision**: Increment `version` counter on each calculation, store `computed_at` timestamp

**Rationale**:
- **Caching**: Clients can skip redundant polling if `X-Calculation-Version` header unchanged
- **Debugging**: Easy to trace when calculations occurred
- **Optimistic Updates**: Future feature - clients request changes since version X

---

### 9. API Response Format
**Decision**: All responses follow:
```json
{
  "status": "success|error",
  "data": { ... } or null,
  "error": "ERROR_CODE" or null,
  "message": "..." (optional)
}
```

**Rationale**:
- **Consistency**: Uniform error handling across all endpoints
- **Structured Logging**: Status field enables analytics
- **Client Parsing**: Easier for mobile/web clients

---

### 10. PostgreSQL + SQLAlchemy 2.0
**Decision**: Use PostgreSQL with SQLAlchemy 2.0 ORM

**Rationale**:
- **Scalability**: PostgreSQL handles concurrent connections well
- **Threading**: Multiple threads can share connection pool
- **Type Safety**: JSONB for grid storage, UUID for IDs
- **SQLAlchemy 2.0**: Async support for future optimization

---

## Performance Targets and Benchmarks

### SLA (Service Level Agreement)
| Operation | Target | Notes |
|-----------|--------|-------|
| POST /groups | <100ms | Simple insert + token generation |
| POST /submissions | <5s | Includes OCR (1-3s) + DB insert |
| GET /free-time | <500ms | Reads cached result, enforces polling delay |
| DELETE /submissions/{id} | <1s | Marks for deletion + recalculation trigger |
| Batch deletion | <5min | Processes expired groups, 1000s per batch |

### Load Benchmarks
- **Concurrent users**: 50 simultaneous submissions
- **Polling rate**: 100 requests/sec across all clients
- **Database**: 10,000 groups with 100 participants each (max capacity: 50,000 groups)

---

## Scalability Considerations

### Horizontal Scaling
1. **Stateless**: No session affinity needed
2. **Load Balancer**: Route requests to multiple app instances
3. **Database**: PostgreSQL connection pooling (one pool per app instance)
4. **Batch Jobs**: Use Kubernetes CronJob or external scheduler (one instance per time)

### Vertical Scaling
1. **OCR**: CPU-bound, benefits from more cores
2. **Calculation**: CPU-bound for large groups
3. **Database**: Disk I/O bottleneck at 50K+ groups

### Future Optimizations
1. **Redis Caching**: Cache FreeTimeResult for 2-5sec
2. **Async OCR**: Queue with Celery/RabbitMQ to avoid blocking
3. **Partial Recalculation**: Update only affected time slots on new submission
4. **Graph Database**: Store relationships for faster interval queries

---

## Error Handling Strategy

### Client Errors (4xx)
- `400 Bad Request` - Invalid input (e.g., bad interval_ms)
- `404 Not Found` - Group/submission doesn't exist
- `410 Gone` - Group has expired (lazy deletion)

### Server Errors (5xx)
- `408 Timeout` - OCR parsing exceeded 3-second timeout
- `500 Internal Server Error` - Unexpected database/OCR failure

### Retry Logic
- **Client**: Retry GET /free-time on 410 by showing "Expired" message
- **Client**: Retry POST /submissions on 408 (with exponential backoff, max 3 times)
- **Server**: Batch deletion uses exponential backoff on failures

---

## Security Considerations

### Data Privacy
1. **No Persistent Storage**: Images discarded after OCR
2. **No User Accounts**: Pseudonymous via nicknames
3. **Token-Based Access**: Group links are secret tokens (via UUID)
4. **PII Masking**: No email/phone in logs or responses

### DDoS Protection
1. **Polling Rate Limiting**: Server enforces 2-3sec minimum interval
2. **Image Size Limit**: Reject >10MB images
3. **Group Limits**: Max 50 participants per group
4. **Rate Limiting**: Per-IP request throttling (100 req/min)

### SQL Injection Protection
1. **SQLAlchemy ORM**: Parameterized queries by default
2. **Input Validation**: Pydantic models validate all inputs
3. **Type Hints**: Mypy/Pylint catch type mismatches

---

## Testing Strategy

### Unit Tests (43+ tests)
- Nickname generation, slot normalization, AND calculation
- Error handling, retry logic

### Integration Tests (12+ tests)
- E2E flows: create group → submit image → poll results → delete

### Contract Tests (30+ tests)
- API endpoint behavior per OpenAPI spec

### Performance Tests (8+ tests)
- Load test 50 concurrent users
- Profile OCR and calculation latency

### Security Tests (5+ tests)
- TLS headers, logging masking, SQL injection prevention

**Target Coverage**: 85%+ of execute paths

---

## Future Enhancements

### Phase 2: Enhanced Scheduling
1. **Availability Heatmap**: Show which times have most overlaps
2. **Weighted Scheduling**: Prioritize certain participants
3. **Recurring Events**: Handle weekly/monthly patterns
4. **Calendar Integration**: iCal export, Google Calendar sync

### Phase 3: Social Features
1. **User Accounts**: Optional persistent profiles
2. **Group Chat**: Discuss alternate times
3. **Announcement**: Notify when meeting time finalized
4. **Public Groups**: Searchable group directory

### Phase 4: Advanced Analytics
1. **Meeting Trends**: Best times by day/season
2. **Friction Metrics**: How many groups fail to find common time
3. **Latency Analytics**: Track OCR + calculation performance

---

**Document Version**: 1.0  
**Last Updated**: 2026-02-20  
**Author**: Development Team
