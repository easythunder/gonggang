# Quickstart: Meet-Match 개발 및 배포

**Feature**: Meet-Match (공통 빈시간 계산 및 공유)  
**Phase**: 1 (Implementation Kickoff)  
**Date**: 2026-02-13

---

## 1. 개발 환경 설정

### 필수 사항
- Node.js 18+ 또는 Python 3.10+
- PostgreSQL 14+
- Docker (선택사항)

### 의존성 설치

#### Python 권장 (OCR + 계산 로직용)
```bash
# venv 생성
python3 -m venv venv
source venv/bin/activate

# 의존성
pip install flask==2.3.0  # 또는 fastapi==0.95.0
pip install psycopg2-binary==2.9.6
pip install pytesseract==0.3.10  # 또는 paddleocr
pip install pillow==9.5.0
pip install python-dotenv==1.0.0
pip install pytest==7.3.1
```

#### OCR 설치
```bash
# macOS (brew에서 tesseract)
brew install tesseract

# Linux (Ubuntu/Debian)
sudo apt-get install tesseract-ocr

# 또는 PaddleOCR (Python)
pip install paddleocr==2.7.0.2
```

### 데이터베이스 초기화
```bash
# PostgreSQL 서버 시작
psql -U postgres -c "CREATE DATABASE gonggang_meet_match;"

# 스키마 마이그레이션
psql -U postgres -d gonggang_meet_match -f .specify/schemas/001_init.sql
```

---

## 2. 핵심 구현 체크리스트

### Phase 1A: 데이터 모델 & 저장소 (Week 1)

- [ ] **데이터베이스 스키마**
  - [ ] `groups` 테이블
  - [ ] `submissions` 테이블
  - [ ] `intervals` 테이블
  - [ ] `group_free_time_results` 테이블
  - [ ] `deletion_logs` 테이블
  - [ ] 인덱스 & 제약 조건

- [ ] **저장소 레이어 (Repository Pattern)**
  - [ ] `GroupRepository.create()`, `get()`, `update_last_activity()`
  - [ ] `SubmissionRepository.create()`, `delete()`, `find_by_group()`
  - [ ] `IntervalRepository.create()`, `find_by_submission()`
  - [ ] `ResultRepository.get_or_none()`, `save()`, `delete()`

### Phase 1B: 계산 엔진 (Library-First) (Week 1-2)

- [ ] **슬롯 정규화 & 계산**
  - [ ] `normalize_intervals(day, start, end) -> (start, end) [5분 정렬]`
  - [ ] `compute_free_time(submissions: List[Submission], display_unit: int) -> FreeTimeResult`
    - AND 연산 (교집합)
    - 5분 슬롯 → 사용자 단위로 병합
  - [ ] **테스트**: 단위 테스트 100% 커버리지
    - ceiling/floor 경계 케이스
    - 중복 제외, 교집합 정확도

- [ ] **OCR + 파싱**
  - [ ] `parse_image(image_bytes) -> List[Interval]`
    - Tesseract 또는 PaddleOCR 호출
    - 바쁜 시간 구간 추출
    - 오류 시 `{success: False, reason: "ocr_failed"}`
  - [ ] **성능**: 5초 이내
  - [ ] **테스트**: 고화질/저화질 이미지 테스트

- [ ] **랜덤 생성 (닉네임/그룹명)**
  - [ ] 단어 풀 로드 (300+ adjectives, nouns)
  - [ ] `generate_nickname() -> str` (중복 검사 포함)
  - [ ] **테스트**: 중복 확률 < 0.01%

### Phase 1C: API 엔드포인트 (Week 2)

- [ ] **POST /groups** (그룹 생성)
  - [ ] 입력 검증
  - [ ] 그룹명 랜덤 생성 (미입력 시)
  - [ ] 링크 생성 (invite_url, share_url)
  - [ ] 응답: `{group_id, group_name, expires_at, invite_url, share_url}`

- [ ] **POST /groups/{groupId}/submissions** (이미지 제출)
  - [ ] 파일 검증 (크기, 형식)
  - [ ] OCR 파싱 + Interval 저장
  - [ ] 닉네임 자동 생성
  - [ ] 공강 재계산 (`기존 AND 신규`)
  - [ ] 응답 시간: 5초 이내

- [ ] **GET /groups/{groupId}/free-time** (폴링)
  - [ ] 만료 확인 (expires_at) → HTTP 410
  - [ ] 저장된 결과 조회 (DB 조회만, 계산 X)
  - [ ] **서버 강제 폴링 간격**: 응답 헤더에 `X-Poll-Wait: 3000` (밀리초)
  - [ ] 응답 시간: 5초 이내

- [ ] **DELETE /groups/{groupId}/submissions/{submissionId}** (제출 삭제)
  - [ ] 전체 재계산 (모든 submission 기반)
  - [ ] 응답: 204 No Content

- [ ] **테스트**: e2e 시나리오
  - 그룹 생성 → 3명 제출 → 폴링 → 제출 삭제 → 재계산

### Phase 1D: 배치 & 삭제 (Week 2-3)

- [ ] **배치 작업 (5~15분 간격)**
  - [ ] `SELECT FROM groups WHERE expires_at <= NOW()`
  - [ ] Cascade 삭제 transaction
  - [ ] 예외 처리:
    - [ ] 오류 로깅
    - [ ] 재시도 (1분, 5분, 15분 지수 백오프)
    - [ ] 최대 3회 재시도

- [ ] **Lazy Deletion** (요청 시)
  - [ ] 폴링/초대 링크 접근 시 만료 확인
  - [ ] 만료 → HTTP 410 Gone

- [ ] **삭제 로그**
  - [ ] `deletion_logs` 테이블에 기록
  - [ ] PII 제외

### Phase 1E: 성능 & 메모리 (Week 3)

- [ ] **성능 테스트**
  - [ ] 50명 그룹 계산 < 1초
  - [ ] 폴링 응답 < 5초
  - [ ] 파싱 < 5초
  - [ ] DB 쿼리 < 500ms

- [ ] **메모리 최적화**
  - [ ] 이미지 메모리 처리 (스트림, 삭제 즉시)
  - [ ] 계산 메모리 (288슬롯 배열 재사용)

### Phase 1F: 보안 & 테스트 (Week 3)

- [ ] **보안**
  - [ ] TLS (HTTPS)
  - [ ] 로그 민감 정보 마스킹
  - [ ] 링크 토큰 강화 (UUID는 충분)
  - [ ] CORS & CSRF 설정

- [ ] **테스트 커버리지**
  - [ ] 단위 테스트: 85%+ (계산, 정규화)
  - [ ] 통합 테스트: 주요 경로 (제출 → 폴링 → 삭제)
  - [ ] E2E 테스트: 시나리오 1개 이상
  - [ ] 성능 테스트: 응답 시간 검증

- [ ] **문서**
  - [ ] README: 로컬 실행, 테스트 가이드
  - [ ] API 문서: OpenAPI/Swagger
  - [ ] 개발자 가이드: 데이터 모델, 계산 로직

---

## 3. 로컬 개발 & 테스트

### 로컬 실행

```bash
# 환경 변수 설정
cat > .env << EOF
DATABASE_URL=postgresql://postgres:password@localhost/gonggang_meet_match
FLASK_ENV=development
DEBUG=True
POLL_INTERVAL_MS=3000
EOF

# Flask 스타트 (Python)
python app.py

# 테스트
pytest tests/ -v --cov=src
```

### 통합 테스트 (E2E)

```bash
# 그룹 생성
curl -X POST http://localhost:8080/groups \
  -H "Content-Type: application/json" \
  -d '{"display_unit_minutes": 30}' \
  | jq '.invite_url'  # → https://localhost:8080/groups/{id}/join

# 이미지 제출 (닉네임 자동 부여)
curl -X POST http://localhost:8080/groups/GROUP_ID/submissions \
  -F "image=@schedule.jpg" \
  | jq '.nickname'  # → "happy_blue_lion"

# 폴링
curl -X GET http://localhost:8080/groups/GROUP_ID/free-time?interval=100 \
  -H "X-Poll-Wait: 3000"  # 서버가 강제 적용
  | jq '.free_time'  # → [{day: "MONDAY", start_minute: 840, ...}]

# 제출 삭제
curl -X DELETE http://localhost:8080/groups/GROUP_ID/submissions/SUB_ID
```

---

## 4. 배포

### Docker 빌드

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN apt-get update && apt-get install -y tesseract-ocr \
    && pip install --no-cache-dir -r requirements.txt

COPY . .
EXPOSE 8080
CMD ["python", "app.py"]
```

### Kubernetes 배포 (선택)

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: meet-match-api
spec:
  replicas: 2
  template:
    spec:
      containers:
      - name: api
        image: gonggang/meet-match:0.1.0
        ports:
        - containerPort: 8080
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-credentials
              key: url
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
```

### 배치 작업 (Kubernetes CronJob)

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: meet-match-batch
spec:
  schedule: "*/10 * * * *"  # 10분마다
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: batch
            image: gonggang/meet-match:0.1.0
            command: ["python", "batch_delete.py"]
```

---

## 5. 모니터링 & 운영

### 주요 메트릭
- OCR 파싱 실패율 (목표: <5%)
- API 응답 시간 (목표: p95 <2초)
- 배치 삭제 성공률 (목표: 99%)
- 그룹 동시 활성 수

### 로깅
```python
import logging

logger = logging.getLogger(__name__)

# parsingfailure
logger.warning(f"OCR failed for submission {sid}", extra={"ocr_error": "..."})

# batch failure
logger.error(f"Batch deletion failed for group {gid}", extra={"group_id": gid, "retry_count": 3})

# 폴링
logger.info(f"Poll request from {groupId}", extra={"participant_count": 3, "response_time_ms": 250})
```

---

## 6. 다음 단계

1. ✅ Data Model & Research (완료)
2. ⬜ **코드 작성** (계획 문서 생성 완료 → 실제 개발 시작)
3. ⬜ 테스트 & 배포
4. ⬜ 본격 운영

---

## 문의 & 이슈

- [.specify/memory/constitution.md](.specify/memory/constitution.md) - 프로젝트 원칙
- [.specify/memory/meet-match.spec.md](.specify/memory/meet-match.spec.md) - 전체 요구사항
- [contracts/openapi.yaml](contracts/openapi.yaml) - API 명세
