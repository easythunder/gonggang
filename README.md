# Meet-Match (공통 빈시간 계산 및 공유)

Schedule coordination tool for finding common free time in small groups without login.

## Quick Start

### Requirements
- Python 3.11+
- PostgreSQL 14+
- Tesseract OCR

### Setup

1. Clone and create virtual environment:
```bash
python3.11 -m venv venv
source venv/bin/activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Setup database:
```bash
createdb gonggang
export DATABASE_URL="postgresql://user:password@localhost/gonggang"
alembic upgrade head
```

4. Run application:
```bash
uvicorn src.main:app --reload
```

Server runs on `http://localhost:8000`

---

## API Examples

### Create a group
```bash
curl -X POST http://localhost:8000/groups \
  -H "Content-Type: application/json" \
  -d '{
    "display_unit_minutes": 30
  }'

# Response:
# {
#   "group_id": "uuid",
#   "group_name": "happy_blue_lion",
#   "created_at": "2026-02-13T10:30:00Z",
#   "expires_at": "2026-02-16T10:30:00Z",
#   "invite_url": "https://example.com/invite/uuid",
#   "share_url": "https://example.com/share/uuid"
# }
```

### Upload schedule image
```bash
curl -X POST http://localhost:8000/groups/{groupId}/submissions \
  -F "file=@schedule.jpg"

# Response:
# {
#   "submission_id": "uuid",
#   "nickname": "swift_silver_mountain",
#   "success": true
# }
```

### Submit schedule URL
```bash
curl -X POST http://localhost:8000/api/submissions/url \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": "uuid",
    "nickname": "happy_blue_lion",
    "url": "https://everytime.kr/@abc123"
  }'

# Response:
# {
#   "submission_id": "uuid",
#   "nickname": "happy_blue_lion",
#   "group_id": "uuid",
#   "type": "link",
#   "status": "success",
#   "url": "https://everytime.kr/@abc123",
#   "created_at": "2026-03-16T10:30:00Z"
# }
```

### Poll results
```bash
curl -X GET "http://localhost:8000/groups/{groupId}/free-time?interval_ms=2000"

# Response:
# {
#   "group_id": "uuid",
#   "participant_count": 3,
#   "free_time": [
#     {
#       "day": "MONDAY",
#       "start": "14:00",
#       "end": "15:30",
#       "duration_minutes": 90,
#       "overlap_count": 3
#     }
#   ],
#   "computed_at": "2026-02-13T10:30:00Z",
#   "expires_at": "2026-02-16T10:30:00Z"
# }
```

### Delete a submission
```bash
curl -X DELETE http://localhost:8000/groups/{groupId}/submissions/{submissionId}
# Response: 204 No Content
```

---

## Testing

Run all tests with coverage:
```bash
pytest
```

Run specific test type:
```bash
pytest -m unit       # Unit tests only
pytest -m integration  # Integration tests only
pytest -m contract   # API contract tests only
pytest -m performance # Performance tests only
```

With verbose output:
```bash
pytest -vv
```

---

## Development

### Code Quality

Format code:
```bash
black src/ tests/
isort src/ tests/
```

Run linters:
```bash
flake8 src/ tests/
pylint src/
```

### Database

Create migration:
```bash
alembic revision --autogenerate -m "description"
```

Apply migrations:
```bash
alembic upgrade head
```

Rollback:
```bash
alembic downgrade -1
```

---

## Docker

### Local Development
```bash
docker-compose up -d
```

Includes PostgreSQL and optional Tesseract service.

### Build Image
```bash
docker build -f docker/Dockerfile -t gonggang:latest .
```

---

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for design decisions and system overview.

See [specs/001-meet-match/](specs/001-meet-match/) for complete specification and implementation plan.

---

## Status

**Phase**: Implementation (Week 1 - Setup & Foundation)  
**Branch**: `001-meet-match`  
**Spec**: [Final v0.3](specs/001-meet-match/spec.md)  
**Tasks**: [100 tasks](specs/001-meet-match/tasks.md)  

See [CONTRIBUTING.md](docs/CONTRIBUTING.md) for developer guidelines.
