# 데이터베이스 스키마 (Database Schema)

> **작성일**: 2026-02-25  
> **목적**: Meet-Match 프로젝트의 PostgreSQL 테이블 구조 및 관계 상세 문서  
> **버전**: 1.0

---

## 📋 목차

1. [테이블 관계도](#테이블-관계도)
2. [groups 테이블](#1-groups-테이블)
3. [submissions 테이블](#2-submissions-테이블)
4. [intervals 테이블](#3-intervals-테이블-참여자-시간표)
5. [group_free_time_results 테이블](#4-group_free_time_results-테이블)
6. [deletion_logs 테이블](#5-deletion_logs-테이블)
7. [인덱스 전략](#인덱스-전략)
8. [쿼리 예시](#쿼리-예시)
9. [캐스케이드 삭제](#캐스케이드-삭제-cascade-delete)

---

## 테이블 관계도

```
groups (1)
  ├─ (1:N) submissions
  │   └─ (1:N) intervals ← 참여자 시간표!
  ├─ (1:1) group_free_time_results (UNIQUE)
  └─ (1:N) deletion_logs
```

### 관계 설명
- **groups → submissions**: 한 그룹에 여러 참여자 제출
- **submissions → intervals**: 한 제출에 여러 시간 간격
- **groups → group_free_time_results**: 한 그룹에 최신 계산 결과 1개
- **groups → deletion_logs**: 한 그룹의 삭제 히스토리

---

## 1. **groups** 테이블

**목적**: 그룹 기본 정보 및 메타데이터 저장

### 스키마

```sql
CREATE TABLE groups (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL UNIQUE,
    display_unit_minutes INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    last_activity_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    admin_token VARCHAR(255) NOT NULL UNIQUE,
    invite_url VARCHAR(500) NOT NULL UNIQUE,
    share_url VARCHAR(500) NOT NULL UNIQUE,
    max_participants INTEGER NOT NULL DEFAULT 50,
    CHECK (display_unit_minutes IN (10, 20, 30, 60))
);

CREATE INDEX ix_groups_expires_at ON groups(expires_at);
CREATE INDEX ix_groups_last_activity ON groups(last_activity_at);
```

### 필드 설명

| 필드 | 타입 | NULL | 설명 |
|------|------|------|------|
| `id` | UUID | NO | 그룹 고유 ID (자동 생성) |
| `name` | VARCHAR(255) | NO | 그룹명 (중복 불가) |
| `display_unit_minutes` | INTEGER | NO | 시간 표시 단위 (10/20/30/60분) |
| `created_at` | TIMESTAMP | NO | 생성 시간 |
| `last_activity_at` | TIMESTAMP | NO | 마지막 활동 시간 (제출/조회) |
| `expires_at` | TIMESTAMP | NO | 자동 삭제 예정 시간 (72h 후) |
| `admin_token` | VARCHAR(255) | NO | 관리자 토큰 (중복 불가) |
| `invite_url` | VARCHAR(500) | NO | 참여자 초대 링크 (중복 불가) |
| `share_url` | VARCHAR(500) | NO | 결과 공유 링크 (중복 불가) |
| `max_participants` | INTEGER | NO | 최대 참여자 수 (기본값: 50) |

### 실제 데이터 예시

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "회의실 예약",
  "display_unit_minutes": 30,
  "created_at": "2026-02-25T08:00:00Z",
  "last_activity_at": "2026-02-25T10:35:00Z",
  "expires_at": "2026-02-28T08:00:00Z",
  "admin_token": "adm-abc123xyz456",
  "invite_url": "/invite/inv-abc123",
  "share_url": "/share/shr-abc123",
  "max_participants": 50
}
```

### 생명주기

```
생성 (created_at)
  ↓
활동 (last_activity_at 업데이트) ← 제출 또는 폴링 요청
  ↓
만료 (expires_at 도달)
  ├─ Lazy Deletion: 폴링 요청 시 410 Gone 반환
  └─ Batch Deletion: 10분마다 자동 삭제 (cascade)
```

---

## 2. **submissions** 테이블

**목적**: 각 참여자의 제출 정보 저장

### 스키마

```sql
CREATE TABLE submissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    group_id UUID NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    nickname VARCHAR(255) NOT NULL,
    submitted_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    status submission_status NOT NULL DEFAULT 'pending',
    error_reason VARCHAR(500),
    UNIQUE(group_id, nickname)
);

CREATE INDEX ix_submissions_group_id ON submissions(group_id);
CREATE INDEX ix_submissions_status ON submissions(status);
```

### 필드 설명

| 필드 | 타입 | NULL | 설명 |
|------|------|------|------|
| `id` | UUID | NO | 제출 고유 ID |
| `group_id` | UUID | NO | 소속 그룹 ID (FK) |
| `nickname` | VARCHAR(255) | NO | 참여자 닉네임 (3단어, 예: "행운한 파란 달") |
| `submitted_at` | TIMESTAMP | NO | 제출 시간 |
| `status` | ENUM | NO | 상태 (pending, success, failed) |
| `error_reason` | VARCHAR(500) | YES | 실패 사유 (OCR 오류 등) |

### Status 값

```
'pending'   → 제출 접수 중
'success'   → OCR 파싱 성공 + 간격 저장됨
'failed'    → OCR 파싱 실패
```

### UNIQUE 제약

```python
# (group_id, nickname) 조합은 유일해야 함
# 같은 그룹 내에서 중복 닉네임 방지
UNIQUE(group_id, nickname)
```

### 실제 데이터 예시

```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440001",
    "group_id": "550e8400-e29b-41d4-a716-446655440000",
    "nickname": "행운한 파란 달",
    "submitted_at": "2026-02-25T08:30:00Z",
    "status": "success",
    "error_reason": null
  },
  {
    "id": "550e8400-e29b-41d4-a716-446655440002",
    "group_id": "550e8400-e29b-41d4-a716-446655440000",
    "nickname": "용감한 빨강 별",
    "submitted_at": "2026-02-25T08:45:00Z",
    "status": "success",
    "error_reason": null
  }
]
```

### 캐스케이드 삭제

```
groups 삭제
  └─ submissions 자동 삭제 (ON DELETE CASCADE)
     └─ intervals 자동 삭제 (ON DELETE CASCADE)
```

---

## 3. **intervals** 테이블 (참여자 시간표)

**목적**: 각 참여자의 바쁜 시간(예약/일정) 저장 ⭐

### 스키마

```sql
CREATE TABLE intervals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    submission_id UUID NOT NULL REFERENCES submissions(id) ON DELETE CASCADE,
    day_of_week INTEGER NOT NULL CHECK (day_of_week >= 0 AND day_of_week <= 6),
    start_minute INTEGER NOT NULL CHECK (start_minute >= 0 AND start_minute <= 1435),
    end_minute INTEGER NOT NULL CHECK (end_minute >= 5 AND end_minute <= 1440),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CHECK (start_minute < end_minute),
    CHECK (start_minute % 5 = 0),
    CHECK (end_minute % 5 = 0)
);

CREATE INDEX ix_intervals_submission_id ON intervals(submission_id);
CREATE INDEX ix_intervals_day_slot ON intervals(day_of_week, start_minute, end_minute);
```

### 필드 설명

| 필드 | 타입 | NULL | 설명 |
|------|------|------|------|
| `id` | UUID | NO | 간격 고유 ID |
| `submission_id` | UUID | NO | 제출 ID (FK) |
| `day_of_week` | INTEGER | NO | 요일 (0=월, 1=화, ..., 6=일) |
| `start_minute` | INTEGER | NO | 시작 시간 (분 단위, 5분 배수) |
| `end_minute` | INTEGER | NO | 종료 시간 (분 단위, 5분 배수) |
| `created_at` | TIMESTAMP | NO | 생성 시간 |

### 제약조건

```
✓ day_of_week: 0~6 범위
✓ start_minute: 0~1435 범위 (5분 배수)
✓ end_minute: 5~1440 범위 (5분 배수)
✓ start_minute < end_minute (앞이 뒤보다 먼저)
✓ 5분 정렬: 09:15 → 09:15로 저장 (정규화됨)
```

### 실제 데이터 예시

```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440100",
    "submission_id": "550e8400-e29b-41d4-a716-446655440001",
    "day_of_week": 0,
    "start_minute": 540,     // 09:00
    "end_minute": 660,       // 11:00
    "created_at": "2026-02-25T08:30:00Z"
  },
  {
    "id": "550e8400-e29b-41d4-a716-446655440101",
    "submission_id": "550e8400-e29b-41d4-a716-446655440001",
    "day_of_week": 0,
    "start_minute": 840,     // 14:00
    "end_minute": 1080,      // 18:00
    "created_at": "2026-02-25T08:30:00Z"
  }
]
```

### 분(minute) 계산 공식

```
시간 → 분 변환
  09:00 = 9 × 60 = 540
  14:30 = 14 × 60 + 30 = 870
  18:00 = 18 × 60 = 1080
  23:59 = 23 × 60 + 59 = 1439 (최대값 1440은 다음날 00:00)
```

### 실제 조회 예시

**월요일 09:00~11:00 바쁜 사람 찾기**:

```sql
SELECT s.nickname, i.start_minute, i.end_minute
FROM intervals i
JOIN submissions s ON i.submission_id = s.id
WHERE i.day_of_week = 0  -- 월요일
  AND i.start_minute <= 540   -- 09:00
  AND i.end_minute >= 540;
```

---

## 4. **group_free_time_results** 테이블

**목적**: 계산된 여집합 결과 저장 (최신 version만 저장)

### 스키마

```sql
CREATE TABLE group_free_time_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    group_id UUID NOT NULL UNIQUE REFERENCES groups(id) ON DELETE CASCADE,
    version INTEGER NOT NULL DEFAULT 1,
    availability_by_day JSONB,
    free_time_intervals JSONB,
    computed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    status submission_status NOT NULL DEFAULT 'pending',
    error_code VARCHAR(100)
);

CREATE INDEX ix_free_time_group ON group_free_time_results(group_id);
CREATE INDEX ix_free_time_computed ON group_free_time_results(computed_at);
```

### 필드 설명

| 필드 | 타입 | NULL | 설명 |
|------|------|------|------|
| `id` | UUID | NO | 결과 고유 ID |
| `group_id` | UUID | NO | 그룹 ID (UNIQUE - 그룹당 1개 결과만) |
| `version` | INTEGER | NO | 계산 버전 (제출/삭제마다 증가) |
| `availability_by_day` | JSONB | YES | 가용성 그리드 (미사용) |
| `free_time_intervals` | JSONB | YES | 기본 여집합 시간 리스트 (**≥10분**) ⭐ |
| `free_time_intervals_30min` | JSONB | YES | 여집합 중 **≥30분 이상** 시간 리스트 |
| `free_time_intervals_60min` | JSONB | YES | 여집합 중 **≥60분 이상** 시간 리스트 |
| `computed_at` | TIMESTAMP | NO | 계산 완료 시간 |
| `status` | ENUM | NO | 상태 (pending, success, failed) |
| `error_code` | VARCHAR(100) | YES | 오류 코드 |

### free_time_intervals* 구조 (3가지 필터 버전)

```json
{
  "free_time_intervals": {
    "0": [
      {"start_minute": 0, "end_minute": 540},       // 00:00~09:00 (540min)
      {"start_minute": 1200, "end_minute": 1440}    // 20:00~24:00 (240min)
    ],
    "1": [...]  // 화요일
  },
  
  "free_time_intervals_30min": {
    "0": [
      {"start_minute": 0, "end_minute": 540}        // 540min ≥ 30min ✅
      // 240min < 30min이면 제외되지 않음 (제외 기준: <30min만)
    ],
    "1": [...]
  },
  
  "free_time_intervals_60min": {
    "0": [
      {"start_minute": 0, "end_minute": 540}        // 540min ≥ 60min ✅
      // 240min < 60min이면 제외
    ],
    "1": [...]
  }
}
```

**필터링 규칙**:
- `free_time_intervals`: **≥10분** 자유시간 (기본값)
- `free_time_intervals_30min` **≥30분** 자유시간
- `free_time_intervals_60min`: **≥60분** 자유시간

**예시**:
```
자유시간: [09:00-09:15(15분), 12:00~13:00(60분), 14:00~15:30(90분)]

10분 기준: [09:00-09:15, 12:00~13:00, 14:00~15:30]  (3개)
30분 기준: [12:00~13:00, 14:00~15:30]                (2개)
60분 기준: [12:00~13:00, 14:00~15:30]                (2개)
```

### 버전 관리

```
제출 1 추가 (A, B, C)
  └─ version = 1 저장
  
제출 2 추가 (D 추가)
  └─ version = 2로 업데이트 (자동 증가)
  
제출 3 삭제 (A 제거)
  └─ version = 3으로 업데이트 (자동 재계산)
```

### 실제 데이터 예시

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440200",
  "group_id": "550e8400-e29b-41d4-a716-446655440000",
  "version": 2,
  "computed_at": "2026-02-25T10:35:00Z",
  "status": "success",
  "free_time_intervals": {
    "0": [
      {"start_minute": 0, "end_minute": 540},       // 00:00~09:00
      {"start_minute": 780, "end_minute": 840},     // 13:00~14:00
      {"start_minute": 1200, "end_minute": 1440}    // 20:00~24:00
    ]
  }
}
```

### 업데이트 로직

```python
if existing_result:
    # 기존 결과 업데이트 (version 자동 증가)
    update_result(group_id, free_time_intervals)
else:
    # 새 결과 생성 (version = 1)
    create_result(group_id, free_time_intervals)
```

---

## 5. **deletion_logs** 테이블

**목적**: 삭제 작업 감사 로그 (compliance & debugging)

### 스키마

```sql
CREATE TABLE deletion_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    group_id UUID REFERENCES groups(id) ON DELETE SET NULL,
    deleted_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    reason VARCHAR(100) NOT NULL,
    submission_count INTEGER,
    asset_count INTEGER,
    error_code VARCHAR(100),
    retry_count INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX ix_deletion_logs_group ON deletion_logs(group_id);
CREATE INDEX ix_deletion_logs_deleted_at ON deletion_logs(deleted_at);
CREATE INDEX ix_deletion_logs_reason ON deletion_logs(reason);
```

### 필드 설명

| 필드 | 타입 | NULL | 설명 |
|------|------|------|------|
| `id` | UUID | NO | 로그 고유 ID |
| `group_id` | UUID | YES | 삭제된 그룹 ID (SET NULL on delete) |
| `deleted_at` | TIMESTAMP | NO | 삭제 시간 |
| `reason` | VARCHAR(100) | NO | 삭제 사유 (expired, manual) |
| `submission_count` | INTEGER | YES | 삭제된 제출 수 |
| `asset_count` | INTEGER | YES | 삭제된 간격 수 |
| `error_code` | VARCHAR(100) | YES | 오류 코드 (NULL = 성공) |
| `retry_count` | INTEGER | NO | 재시도 횟수 |

### Reason 값

```
'expired'   → 72시간 만료
'manual'    → 관리자 삭제
'failed'    → 삭제 실패 (재시도 후)
```

### 실제 데이터 예시

```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440300",
    "group_id": "550e8400-e29b-41d4-a716-446655440000",
    "deleted_at": "2026-02-28T08:00:00Z",
    "reason": "expired",
    "submission_count": 3,
    "asset_count": 15,
    "error_code": null,
    "retry_count": 0
  }
]
```

### 감사 쿼리 예시

```sql
-- 지난 7일 삭제 통계
SELECT 
  reason,
  COUNT(*) as count,
  AVG(submission_count) as avg_submissions
FROM deletion_logs
WHERE deleted_at > NOW() - INTERVAL '7 days'
GROUP BY reason;

-- 실패한 삭제 조회
SELECT * FROM deletion_logs
WHERE error_code IS NOT NULL
  AND retry_count > 0;
```

---

## 인덱스 전략

### 📊 인덱스 목록

| 테이블 | 인덱스명 | 필드 | 목적 |
|--------|---------|------|------|
| groups | `ix_groups_expires_at` | expires_at | 배치 삭제 스캔 (10분마다) |
| groups | `ix_groups_last_activity` | last_activity_at | 활동 시간 조회 |
| submissions | `ix_submissions_group_id` | group_id | 그룹별 제출 빠른 조회 |
| submissions | `ix_submissions_status` | status | 상태별 필터링 |
| intervals | `ix_intervals_submission_id` | submission_id | 제출별 간격 조회 |
| intervals | `ix_intervals_day_slot` | (day, start, end) | 요일별 시간 범위 조회 |
| free_time_results | `ix_free_time_group` | group_id | 그룹별 최신 결과 조회 |
| free_time_results | `ix_free_time_computed` | computed_at | 계산 시간 범위 조회 |
| deletion_logs | `ix_deletion_logs_group` | group_id | 그룹별 삭제 히스토리 |
| deletion_logs | `ix_deletion_logs_deleted_at` | deleted_at | 시간 범위 감사 |
| deletion_logs | `ix_deletion_logs_reason` | reason | 삭제 사유별 통계 |

### 성능 최적화

```python
# ❌ 느린 쿼리 (인덱스 미사용)
SELECT * FROM intervals 
WHERE start_minute = 540;  # 범위 검색 필요

# ✅ 빠른 쿼리 (인덱스 사용)
SELECT * FROM intervals
WHERE day_of_week = 0 
  AND start_minute >= 540 
  AND start_minute <= 660;  # 복합 인덱스 활용
```

---

## 쿼리 예시

### 1️⃣ 그룹 생성

```sql
INSERT INTO groups (
    name, display_unit_minutes, created_at, last_activity_at,
    expires_at, admin_token, invite_url, share_url
) VALUES (
    '회의실 예약', 30, NOW(), NOW(),
    NOW() + INTERVAL '72 hours', 'adm-xxx', 'inv-xxx', 'shr-xxx'
) RETURNING id;
```

### 2️⃣ 제출 추가 + 시간 저장

```sql
-- 1. 제출 생성
INSERT INTO submissions (group_id, nickname, status)
VALUES ('group-uuid', '행운한 파란 달', 'success')
RETURNING id;

-- 2. 시간 간격 추가
INSERT INTO intervals (submission_id, day_of_week, start_minute, end_minute)
VALUES 
  ('submission-uuid', 0, 540, 660),    -- 월 09:00-11:00
  ('submission-uuid', 0, 840, 1080);   -- 월 14:00-18:00
```

### 3️⃣ 자유시간 계산 결과 조회

```sql
-- 그룹의 최신 자유시간 조회
SELECT 
  version,
  free_time_intervals,
  computed_at
FROM group_free_time_results
WHERE group_id = 'group-uuid'
ORDER BY version DESC
LIMIT 1;
```

### 4️⃣ 모든 참여자의 시간 조회

```sql
-- 월요일에 9-11시 일정 있는 사람 찾기
SELECT DISTINCT s.nickname
FROM intervals i
JOIN submissions s ON i.submission_id = s.id
WHERE i.day_of_week = 0
  AND i.start_minute < 660  -- 11:00
  AND i.end_minute > 540;   -- 09:00
```

### 5️⃣ 배치 삭제 대상 조회

```sql
-- 72시간 이상 지난 그룹 조회
SELECT id, name, submission_count
FROM groups g
LEFT JOIN (
  SELECT group_id, COUNT(*) as submission_count
  FROM submissions
  GROUP BY group_id
) sub ON g.id = sub.group_id
WHERE expires_at < NOW()
  AND NOT EXISTS (
    SELECT 1 FROM deletion_logs 
    WHERE group_id = g.id AND error_code IS NULL
  );
```

---

## 캐스케이드 삭제 (CASCADE DELETE)

### 삭제 흐름

```
DELETE FROM groups WHERE id = 'group-uuid'
  │
  ├─► submissions (자동 삭제)
  │   ON DELETE CASCADE
  │   └─► intervals (자동 삭제)
  │       ON DELETE CASCADE
  │
  ├─► group_free_time_results (자동 삭제)
  │   ON DELETE CASCADE
  │
  └─► deletion_logs (SET NULL)
      ON DELETE SET NULL (group_id만 NULL)
```

### 삭제 순서

```
1️⃣ groups 삭제 시작
   └─ group_id 외래키 확인

2️⃣ submissions 자동 삭제
   └─ 해당 그룹의 모든 제출

3️⃣ intervals 자동 삭제
   └─ 제출별 모든 시간 간격

4️⃣ group_free_time_results 자동 삭제
   └─ 그룹의 계산 결과

5️⃣ deletion_logs SET NULL
   └─ group_id만 NULL로 설정 (로그 유지)

6️⃣ 완료
   └─ groups 행 삭제
```

### 트랜잭션 안전성

```python
try:
    # 트랜잭션 시작
    session.begin()
    
    # 그룹 삭제 (cascade 발동)
    db.query(Group).filter(Group.id == group_id).delete()
    
    # 커밋
    session.commit()
except Exception as e:
    # 실패 시 전체 롤백
    session.rollback()
    raise
```

---

## 마이그레이션 실행

### 스키마 생성

```bash
# PostgreSQL에 스키마 적용
psql -U gonggang -d gonggang -f migrations/schema.sql

# 결과 확인
psql -U gonggang -d gonggang -c "\dt"
```

### 검증 쿼리

```sql
-- 모든 테이블 확인
SELECT tablename FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY tablename;

-- 인덱스 확인
SELECT schemaname, tablename, indexname 
FROM pg_indexes 
WHERE schemaname = 'public'
ORDER BY tablename, indexname;

-- 외래키 확인
SELECT * FROM information_schema.table_constraints 
WHERE table_schema = 'public' 
  AND constraint_type = 'FOREIGN KEY';
```

---

## 성능 고려사항

### 최적화 팁

✅ **DO**:
- 날짜 범위 쿼리에 인덱스 활용
- 배치 삭제 시 LIMIT 사용 (부하 분산)
- 폴링 요청 시 캐싱 활용

❌ **DON'T**:
- intervals 테이블에 선택 없이 전체 조회
- group_free_time_results에서 모든 버전 히스토리 유지 (UNIQUE 제약)
- 트랜잭션 없이 cascade 삭제 실행

---

## 추가 리소스

- SQL 스키마: [migrations/schema.sql](../migrations/schema.sql)
- 모델 정의: [src/models/models.py](../src/models/models.py)
- 저장소 레이어: [src/repositories/](../src/repositories/)
- 아키텍처: [docs/ARCHITECTURE.md](./ARCHITECTURE.md)

