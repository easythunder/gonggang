# Data Model: Meet-Match (공통 빈시간)

**Feature**: Meet-Match  
**Phase**: 1 (Design & Contracts)  
**Date**: 2026-02-13  

---

## 개요

다음은 Meet-Match 서비스의 핵심 데이터 모델입니다. 모든 엔티티는 5분 슬롯 기반 계산과 72시간 자동 삭제를 지원하도록 설계되었습니다.

---

## 엔티티

### Group

```sql
CREATE TABLE groups (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(256) NOT NULL UNIQUE,  -- 사용자 입력 또는 랜덤 생성
  display_unit_minutes INT NOT NULL,  -- 10, 20, 30, 60
  max_participants INT DEFAULT 50,
  
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  last_activity_at TIMESTAMP NOT NULL DEFAULT NOW(),  -- 제출/수정/폴링 시 갱신
  expires_at TIMESTAMP NOT NULL DEFAULT (NOW() + INTERVAL '72 hours'),  -- computed from last_activity_at
  
  -- 링크
  invite_url VARCHAR(512) NOT NULL UNIQUE,
  share_url VARCHAR(512) NOT NULL UNIQUE,
  
  -- 메타
  created_by_ip VARCHAR(45),  -- IPv4/IPv6
  deleted_at TIMESTAMP,  -- soft delete (optional)
  
  CONSTRAINT expires_after_created CHECK (expires_at > created_at)
);

CREATE INDEX idx_groups_expires_at ON groups(expires_at);
CREATE INDEX idx_groups_created_at ON groups(created_at);
```

### Submission

```sql
CREATE TABLE submissions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  group_id UUID NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
  nickname VARCHAR(256) NOT NULL,  -- 자동 생성 (단어 3개)
  
  submitted_at TIMESTAMP NOT NULL DEFAULT NOW(),
  status VARCHAR(50) NOT NULL DEFAULT 'success',  -- success, failed
  error_reason TEXT,  -- 파싱 실패 시 언어 (ocr_failed, etc)
  
  -- 메타
  image_hash VARCHAR(64),  -- 중복 방지용
  
  CONSTRAINT group_nickname_unique UNIQUE (group_id, nickname)
);

CREATE INDEX idx_submissions_group_id ON submissions(group_id);
CREATE INDEX idx_submissions_submitted_at ON submissions(submitted_at);
```

### Interval

```sql
CREATE TABLE intervals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  submission_id UUID NOT NULL REFERENCES submissions(id) ON DELETE CASCADE,
  
  day_of_week INT NOT NULL,  -- 0=Monday, 6=Sunday
  start_minute INT NOT NULL,  -- 0~1439
  end_minute INT NOT NULL,  -- 5~1440 (5분 단위)
  
  -- 메타
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  
  CONSTRAINT valid_time CHECK (start_minute >= 0 AND end_minute <= 1440 AND start_minute < end_minute),
  CONSTRAINT time_alignment CHECK (start_minute % 5 = 0 AND end_minute % 5 = 0)
);

CREATE INDEX idx_intervals_submission_id ON intervals(submission_id);
CREATE INDEX idx_intervals_day_start ON intervals(day_of_week, start_minute);
```

### GroupFreeTimeResult

```sql
CREATE TABLE group_free_time_results (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  group_id UUID NOT NULL UNIQUE REFERENCES groups(id) ON DELETE CASCADE,
  
  version INT NOT NULL DEFAULT 1,  -- 재계산 시 증가
  
  -- 5분 슬롯 기준 availability (JSON)
  availability_by_day JSONB NOT NULL,
  -- {
  --   "MONDAY": [3, 3, 0, 2, ...],  // 각 슬롯별 가능 인원 (0~50)
  --   "TUESDAY": [...],
  --   ...
  -- }
  
  -- 사용자 단위로 병합된 결과 (display_unit_minutes 기준)
  free_time_intervals JSONB NOT NULL,
  -- [
  --   {"day": "MONDAY", "start_minute": 840, "end_minute": 930, "duration_minutes": 90, "overlap_count": 3},
  --   ...
  // ]
  
  participant_count INT NOT NULL,
  
  computed_at TIMESTAMP NOT NULL DEFAULT NOW(),
  
  CONSTRAINT version_positive CHECK (version > 0)
);

CREATE INDEX idx_group_free_time_group_id ON group_free_time_results(group_id);
```

### DeletionLog (감사 용도)

```sql
CREATE TABLE deletion_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  group_id UUID NOT NULL,
  group_name VARCHAR(256),
  deleted_at TIMESTAMP NOT NULL DEFAULT NOW(),
  reason VARCHAR(50) NOT NULL,  -- expired, manual, error_retry
  submission_count INT,
  interval_count INT,
  error_code VARCHAR(128),  -- 배치 실패 시
  retry_count INT DEFAULT 0
);

CREATE INDEX idx_deletion_logs_deleted_at ON deletion_logs(deleted_at);
CREATE INDEX idx_deletion_logs_reason ON deletion_logs(reason);
```

---

## 관계도

```
Group (1)
  ├─ submission (N)
  │   └─ interval (N)
  └─ group_free_time_result (1)

deletion_log (외부)
```

---

## 계산 흐름 (데이터 관점)

### 신규 제출 시
```
1. Group.last_activity_at ← NOW()
2. Group.expires_at ← last_activity_at + 72h
3. Submission 생성 (status='success')
4. Interval 추출 & 저장 (각 제출마다 여러 rows)
5. GroupFreeTimeResult 계산 & 저장
   - 기존 result 로드
   - 신규 intervals AND 기존 result → 새 availability
   - version += 1
```

### 제출 삭제 시
```
1. Submission 행 삭제 (CASCADE → Interval도 삭제)
2. GroupFreeTimeResult 전체 재계산
   - 남은 모든 submissions 기반 새로 계산
   - version += 1
```

### 배치 삭제 시 (매 5~15분)
```
1. SELECT FROM groups WHERE expires_at <= NOW()
2. 각 group마다:
   - DELETE intervals (FK → submissions)
   - DELETE submissions
   - DELETE group_free_time_result
   - DELETE groups
   - INSERT deletion_log
3. 실패 시: retry with exponential backoff (1분, 5분, 15분)
```

---

## 주요 설계 결정

### 1. Interval 분리 테이블
**왜**: 하나의 제출에서 여러 시간대 가능 (예: 월/수/금 09:00~10:00)
- 유연성: 복잡한 시간표 지원
- 인덱싱: (submission_id, day, start_minute)로 빠른 조회

### 2. JSONB 저장 (availability + free_time)
**왜**: 계산 결과는 고정 구조, 성능 최적화
- 읽기: 단순 JSON 조회 (계산 X)
- 쓰기: 계산 후 한 번에 저장

### 3. Soft Delete vs Hard Delete
**선택**: Hard Delete (트랜잭션으로 원자성 보장)
- Soft delete는 감시 복잡도 증가
- deletion_log로 감사 추적 가능

### 4. 5분 슬롯 고정 (정규화)
**왜**: 저장소 절약 + 계산 단순화
- 288슬롯 × 7일 = 2,016 데이터 포인트/group
- AND 연산: O(n) 선형 시간

---

## 성능 고려사항

### 인덱스 전략
```
groups:
  - PRIMARY KEY (id)
  - UNIQUE (name), (invite_url), (share_url)
  - INDEX (expires_at)  -- 배치 삭제용
  - INDEX (created_at)

submissions:
  - PRIMARY KEY (id)
  - FOREIGN KEY (group_id)
  - UNIQUE (group_id, nickname)
  - INDEX (group_id)

intervals:
  - PRIMARY KEY (id)
  - FOREIGN KEY (submission_id)
  - INDEX (submission_id)
  - INDEX (day_of_week, start_minute)

group_free_time_results:
  - PRIMARY KEY (id)
  - UNIQUE (group_id)
```

### 계산 복잡도
- 50명 그룹: 7일 × 288슬롯 × 50명 = 100,800 포인트
- AND 연산: O(n) = ~100ms
- DB 쿼리 + 저장: ~500ms
- 총: ~1초 (여유 있음)

---

## 마이그레이션 & 배포

### 초기 스키마
```bash
$ psql -f schemas/001_init.sql
```

### 이후 구조 변경
- 칼럼 추가 (nullable): 온라인 가능
- 테이블 추가: 즉시
- 인덱스 추가: 가능하나 시간 소요

---

## 다음 단계

1. ✅ 데이터 모델 (이 문서)
2. ⬜ API Contracts (OpenAPI)
3. ⬜ 구현 체크리스트
