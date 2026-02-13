# Implementation Plan: Meet-Match (공통 빈시간 계산 및 공유)

**Branch**: `001-meet-match` | **Date**: 2026-02-13 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-meet-match/spec.md`

**Note**: This plan synthesizes the complete design phase (Phase 0 research + Phase 1 design) for implementation (Phase 2).

## Summary

Meet-Match enables small groups (max 50 people) to quickly find common free time without login. Core flow: (1) Create group with optional name & display unit selection; (2) Participants upload schedule images → system OCR parses to 5-min slots (memory-only, no disk storage) → auto-generates random 3-word nicknames; (3) System calculates common free time at submission time using AND logic (`existing_free_time ∩ new_participant_free_time`), stores result in DB; (4) Clients poll results (server-enforced 2-3s intervals); (5) Auto-expires after 72h (lazy deletion on request, batch deletion 5-15min intervals with exponential retry).

**Technical Approach**:
- **Calculation-at-submission model**: Minimize polling overhead by computing free time when data changes, caching result for fast reads
- **Memory-only OCR**: Tesseract/PaddleOCR parses in RAM, image discarded immediately after (<5s total response)
- **Lazy + Batch deletion**: Request-time expiration check (HTTP 410 Gone) + periodic batch with exponential retry (1min, 5min, 15min backoff)
- **Stateless API**: Result pages generated on-demand from group/submission/calculation data (no session state)

## Technical Context

**Language/Version**: Python 3.11+ (Flask 2.3 or FastAPI 0.95) preferred; Node.js 18+ acceptable  
**Primary Dependencies**: 
- Backend: Flask/FastAPI, SQLAlchemy, psycopg2 (PostgreSQL driver)
- OCR: Tesseract 0.3.10 (via pytesseract) or PaddleOCR
- Image processing: Pillow
- Validation: Pydantic

**Storage**: PostgreSQL 14+ with JSONB support (5 core tables: groups, submissions, intervals, group_free_time_results, deletion_logs)  
**Testing**: pytest (Python) targeting 85%+ coverage; unit + integration tests  
**Target Platform**: Linux server (Docker + optional Kubernetes with CronJob for batch cleanup)  
**Project Type**: Backend API + stateless result pages  
**Performance Goals**: 
- Image upload → OCR + calculation → DB result: <5 seconds
- Polling response: <500ms (cached result)
- Free time calculation for 50 people: ~1 second

**Constraints**: 
- 5-minute slot normalization (conservative: ceiling start, floor end)
- 50-participant hard limit per group
- 00:00~23:59 UTC fixed (no user timezone selection in MVP)
- 72-hour retention baseline + TLS required
- Memory-only image processing (no disk/S3 storage)

**Scale/Scope**: 
- Up to 50 concurrent submissions per group
- Batch operations every 5-15 minutes
- <100KB per image (typical scan)
- 6-week implementation (Phase 1A-1F per quickstart.md)

## Constitution Check

*GATE: Must pass before Phase 2 tasks execution*

✅ **Library-First Principle**: Calculation & parsing logic separated into reusable modules (not tied to API layer)  
✅ **CLI Interface**: OCR/calculation logic accessible via internal CLI for testing & scripting  
✅ **Test-First**: Unit tests for slot normalization, AND calculation, OCR parsing (before implementation)  
✅ **Integration Testing**: E2E scenarios: group creation → image submission → free-time calculation → polling  
✅ **Observability/Versioning/Simplicity**: Structured logging (JSON), metrics collection (OCR failure rate, response times), calculation versioning (increment on recalc), minimal dependencies  

**Security/Privacy Compliance**:
- ✅ Data retention: 72h baseline (last_activity_at + 72h), auto-delete with audit log
- ✅ Transmission: TLS required
- ✅ Image storage: Memory-only (no disk/S3), immediate discard after OCR
- ✅ Deletion strategy: Lazy + batch with exponential retry (1min, 5min, 15min)
- ✅ Logging: PII masking (no image URLs, link tokens in logs)

**Gate Result**: ✅ PASS - All principles satisfied. Proceed to Phase 2 tasks.

## Project Structure

### Documentation (this feature)

```text
specs/001-meet-match/
├── plan.md              # This file
├── spec.md              # Full functional + non-functional requirements (37+ FRs, 8 success criteria)
├── research.md          # Technical decision analysis (10 clarifications + rationale)
├── data-model.md        # SQL schema, indexes, constraints, performance analysis
├── quickstart.md        # 6-week implementation checklist + local dev guide + deployment
└── contracts/
    └── openapi.yaml     # API specification (4 endpoints, request/response schemas)
```

### Source Code (repository root)

```text
# Option: Monolithic backend (SELECTED for MVP)

src/
├── models/              # SQLAlchemy models (Group, Submission, Interval, FreeTimeResult, DeletionLog)
├── repositories/        # Data access layer (CRUD + complex queries)
├── services/            # Business logic
│   ├── calculation.py   # Free-time AND logic, slot normalization, candidate generation
│   ├── ocr.py          # Image → OCR parsing wrapper (Tesseract/PaddleOCR)
│   └── deletion.py     # Lazy + batch deletion with retry logic
├── api/                 # REST endpoint handlers
│   ├── groups.py       # POST /groups, GET /groups/{id}
│   ├── submissions.py  # POST /groups/{id}/submissions, DELETE /groups/{id}/submissions/{id}
│   └── free_time.py    # GET /groups/{id}/free-time (polling with enforced intervals)
├── cli/                 # Internal CLI (calculate, parse, test-ocr commands)
├── lib/                 # Shared utilities (nickname generation, slot utils, logging)
├── config.py            # Environment configuration
└── main.py              # App initialization (Flask/FastAPI)

tests/
├── unit/                # Unit tests (slot normalization, calculation, parsing, naming)
├── integration/         # E2E scenarios (group creation → submission → results)
├── contract/            # API contract tests (request/response validation vs openapi.yaml)
└── fixtures/            # Test data and utilities

docker/
├── Dockerfile           # Build + runtime config
└── docker-compose.yml   # Local PostgreSQL + app

k8s/
├── deployment.yaml      # Pod spec, resource limits, health checks
├── service.yaml         # Service definition
├── configmap.yaml       # Environment config
└── cronjob.yaml         # Batch deletion CronJob (5-15min interval)

docs/
├── README.md            # Local setup, running tests, API examples
├── CONTRIBUTING.md      # Contributing guidelines
└── ARCHITECTURE.md      # High-level design decisions
```

**Structure Decision**: Monolithic backend API with modular service layer (calculation, OCR, deletion isolated for testability & reuse). All deployment targets (local dev, Docker, Kubernetes) supported from single codebase.

## Dependency Graph & Week-by-Week Phases

### Phase 1A: Data Model & Repository (Week 1)
**Dependencies**: None (foundation for all phases)
**Output**: 5 production SQL tables + 5 repository classes
**Test Target**: 100% coverage on model constraints + CRUD operations

### Phase 1B: OCR & Calculation Engine (Week 1-2)
**Dependencies**: Phase 1A (repositories available)
**Output**: OCR wrapper + slot normalization + free-time AND calculation + candidate extraction
**Test Target**: 100% unit test coverage (normalization edge cases, AND logic, candidate generation)

### Phase 1C: API Endpoints (Week 2)
**Dependencies**: Phase 1A, 1B (services available)
**Output**: 4 endpoints (POST /groups, POST /submissions, GET /free-time, DELETE /submissions) with request validation
**Test Target**: Contract tests (OpenAPI compliance) + integration tests (happy path)

### Phase 1D: Batch Deletion & Exception Handling (Week 2-3)
**Dependencies**: Phase 1A, 1C (API available)
**Output**: Lazy deletion (request-time check) + batch cron job (5-15min interval) + exponential retry + deletion_logs audit table
**Test Target**: Batch simulation tests, retry scheduling validation

### Phase 1E: Performance Testing & Optimization (Week 3)
**Dependencies**: Phase 1A-1D (all components)
**Output**: Verified <5s response (50 people), <1s calculation, <500ms polling
**Test Target**: Load test (50 concurrent submissions), response time profiling

### Phase 1F: Security Hardening & Documentation (Week 3)
**Dependencies**: Phase 1A-1E (all code complete)
**Output**: TLS config, log masking, API docs, README, 85%+ test coverage
**Test Target**: Security audit checklist (PII masking, TLS verification), coverage report

## Parallel Execution Opportunities

**Week 1 Parallelization**:
- **Parallel Track A** (Task T001-T003): Data model schema design + SQL migration scripts
- **Parallel Track B** (Task T004-T007): Repository CRUD implementations (no cross-dependencies)
- **Sequential Within Parallel**: Both tracks complete by end of Week 1, enabling Phase 1B

**Week 2 Parallelization**:
- **Parallel Track A** (Task T008-T012): OCR wrapper + slot normalization module + unit tests
- **Parallel Track B** (Task T013-T017): Free-time AND calculation + candidate generation + unit tests
- **Sequential After Both** (Task T018-T022): API endpoint implementations (depend on both services)

**Week 2-3 Parallelization**:
- **Parallel Track A** (Task T023-T027): Batch deletion + retry logic + deletion_logs schema
- **Parallel Track B** (Task T028-T032): Lazy deletion (request-time check) + HTTP 410 responses
- **Sequential Merging**: Both deletion strategies integrate into API layer by mid-Week 3

**Week 3 Parallelization**:
- **Parallel Track A** (Task T033-T037): Performance testing + load test setup
- **Parallel Track B** (Task T038-T042): Security hardening + log masking + TLS config
- **Sequential Meeting Point** (Task T043-T050): Documentation + test coverage reporting

## Implementation Strategy

**MVP Scope** (Weeks 1-3, Phase 1A-1F):
1. Core data model + CRUD operations
2. OCR parsing (memory-only) + slot normalization (conservative logic)
3. Free-time AND calculation + candidate generation
4. All 4 API endpoints (group create, submission, free-time polling, deletion)
5. Lazy + batch deletion (exponential retry)
6. Response time <5s target, 85%+ test coverage, TLS/logging baseline

**Incremental Delivery**:
- **Deliverable 1** (Week 1): Data model + repository layer ✅ independently testable
- **Deliverable 2** (Week 2): OCR + calculation + API layer ✅ independently testable (E2E: upload→calculate→poll)
- **Deliverable 3** (Week 2-3): Batch deletion + performance tuning ✅ independently testable (batch simulation)
- **Deliverable 4** (Week 3): Security + documentation ✅ ready for production

**Not in MVP** (Phase 2/3 Post-Launch):
- Everytime scraping/crawling
- Google Calendar integration
- Advanced permissions/organization management
- User accounts & history
- Notifications/reminders

## Key Metrics & Success Criteria

| Criterion | Target | Measurement |
|-----------|--------|-------------|
| **Response Time (upload→result)** | <5s | Load test with 50 participants |
| **Free-time Calculation** | <1s | Profiling 50-person AND operation |
| **Polling Response** | <500ms | Load test with 10 concurrent clients |
| **Test Coverage** | 85%+ | pytest coverage report |
| **OCR Failure Rate** | <5% | Production monitoring metrics |
| **Deletion Reliability** | 100% | Batch job success rate (no retry exhaustion) |
| **Slot Accuracy** | 100% | Unit test validation (normalization edge cases) |

## Blockers & Assumptions

**Assumptions**:
- ✅ PostgreSQL 14+ available (local + deployment)
- ✅ Tesseract/PaddleOCR can parse course schedule formats (typical image quality)
- ✅ 50-participant limit sufficient (can optimize later if needed)
- ✅ 72-hour retention acceptable (adjustable per constitution review)

**No Known Blockers**: All design decisions finalized via 10 user clarifications. Ready to proceed to Phase 2 tasks.

---

**Next Step**: Execute `/speckit.tasks` to generate week-by-week task breakdown (T001-T050+) per Phase 1A-1F.
