# 프로젝트 메서드 정리 문서

> **프로젝트명**: Meet-Match (공통 빈시간 계산 및 공유)  
> **작성일**: 2026-02-25  
> **목적**: 프로젝트 전체 메서드를 체계적으로 분류 및 정리

## 📋 목차

1. [서비스 계층 (Services)](#서비스-계층)
2. [저장소 계층 (Repositories)](#저장소-계층)
3. [모델 계층 (Models)](#모델-계층)
4. [유틸리티/라이브러리 (Utils & Libraries)](#유틸리티라이브러리)
5. [API 엔드포인트](#api-엔드포인트)
6. [메서드 호출 체인](#메서드-호출-체인)

---

## 서비스 계층

서비스 계층은 비즈니스 로직을 담당하며, 저장소 계층과 상호작용합니다.

### 1. CalculationService (`src/services/calculation.py`)

**목적**: Complement 연산을 통한 겹치지 않는 시간 계산 (모든 참여자가 동시에 없는 시간)

| 메서드 | 파라미터 | 반환값 | 설명 |
|--------|---------|--------|------|
| `__init__` | session, submission_repo, interval_repo, free_time_result_repo | - | 계산 서비스 초기화 |
| `trigger_calculation` | group_id: UUID | (FreeTimeResult, error_code) | 그룹의 모든 성공 제출을 여집합 연산으로 계산 |
| `recalculate_on_submission` | group_id: UUID | bool | 새 제출 후 재계산 수행 |
| `_calculate_and_intersection` | submission_intervals: Dict | Dict[int, List] | 제출자들의 겹치지 않는 시간 여집합 계산 |
| `_calculate_time_complement` | intervals: List | List[Tuple] | 24시간에서 주어진 간격을 제외한 여집합 계산 |
| `_store_calculation_result` | group_id, free_time_by_day | FreeTimeResult | 계산 결과 저장 |
| `_create_empty_result` | group_id | FreeTimeResult | 빈 검색 결과 생성 |

**핵심 로직** (Complement - 여집합):
```
1. 그룹의 모든 성공 제출 조회
2. 각 제출의 시간 간격(Interval) 추출
3. 모든 제출자의 간격을 합침 (Union)
4. 24시간에서 합쳐진 간격을 제외 (Complement = 여집합)
5. 최소 1명 이상이 없는 시간(겹치지 않는 시간) 반환
6. 결과 저장 및 버전 관리
```

### 2. GroupService (`src/services/group.py`)

**목적**: 그룹 생성, 조회, 관리

| 메서드 | 파라미터 | 반환값 | 설명 |
|--------|---------|--------|------|
| `__init__` | session: Session | - | 그룹 서비스 초기화 |
| `create_group` | group_name, display_unit_minutes | (Group, error_code) | 새 그룹 생성 (토큰/URL 자동 생성) |
| `get_group` | group_id: UUID | (Group, error_code) | 만료 검사 포함 그룹 조회 |
| `get_group_by_invite_url` | invite_url: str | (Group, error_code) | 초대 URL로 그룹 검색 |
| `get_group_by_share_url` | share_url: str | (Group, error_code) | 공유 URL로 그룹 검색 |
| `check_expiry` | group_id: UUID | bool | 그룹 만료 여부 확인 |
| `update_last_activity` | group_id: UUID | Optional[Group] | 마지막 활동 시간 업데이트 (72h 연장) |
| `get_group_stats` | group_id: UUID | Optional[dict] | 그룹의 통계 조회 |
| `_group_name_exists` | group_name: str | bool | 그룹명 중복 확인 |

**그룹 속성 생성**:
- **admin_token**: 관리자 전용 토큰 (그룹 삭제 권한)
- **invite_url**: 참여자 초대 링크
- **share_url**: 결과 공유 링크
- **expires_at**: 72시간 후 자동 삭제

### 3. SubmissionService (`src/services/submission.py`)

**목적**: 사용자 제출(스케줄 이미지) 관리

| 메서드 | 파라미터 | 반환값 | 설명 |
|--------|---------|--------|------|
| `__init__` | session, repos... | - | 제출 서비스 초기화 |
| `create_submission` | group_id, nickname, intervals, ocr_success, error_reason | (Submission, error_code) | 새 제출 생성 + 자동 계산 트리거 |
| `get_submission` | submission_id: UUID | Optional[Submission] | 제출 조회 |
| `get_group_submissions` | group_id: UUID | List[Submission] | 그룹의 모든 제출 조회 |
| `get_successful_submissions` | group_id: UUID | List[Submission] | 그룹의 성공한 제출만 조회 |
| `get_submission_count` | group_id: UUID | int | 그룹 제출 수 |
| `get_successful_count` | group_id: UUID | int | 그룹의 성공 제출 수 |
| `delete_submission` | submission_id: UUID | bool | 제출 삭제 |
| `_store_intervals` | submission_id, intervals | None | 제출의 시간 간격 저장 |

**제출 상태**:
- `SUCCESS`: OCR 파싱 성공 + 간격 저장
- `FAILED`: OCR 파싱 실패

### 4. OCRService (`src/services/ocr.py`)

**목적**: 이미지에서 스케줄 정보 추출

| 메서드 | 파라미터 | 반환값 | 설명 |
|--------|---------|--------|------|
| `parse_image` | image_bytes | (List[IntervalData], error_msg) | 이미지 파싱 → 시간 간격 추출 |
| `preprocess_image` | image: PIL.Image | PIL.Image | 이미지 전처리 (밝기, 회전 등) |
| `extract_text_with_tesseract` | image | str | Tesseract OCR 실행 |

**관련 클래스: EverytimeScheduleParser**:
- `parse(text)`: OCR 텍스트 파싱 → 스케줄 항목 추출
- `_extract_times_from_line(line)`: 라인에서 시간 쌍 추출

### 5. DeletionService (`src/services/deletion.py`)

**목적**: Lazy 삭제 및 만료 검사

| 메서드 | 파라미터 | 반환값 | 설명 |
|--------|---------|--------|------|
| `check_expiry` | group: Group | bool | 그룹 만료 여부 확인 |
| `check_expiry_by_id` | db, group_id | bool | ID로 만료 여부 확인 |
| `mark_soft_deleted` | db, group_id | None | 만료 그룹 Soft-삭제 표시 |
| `is_soft_deleted` | db, group_id | bool | Soft-삭제 여부 확인 |

**삭제 흐름**:
1. **Lazy Deletion** (요청 시): 폴링 요청 시 만료 확인 → 410 Gone
2. **Batch Deletion** (5-15분마다): Cron 작업으로 자동 삭제
3. **Retry Logic**: 최대 3회 재시도 (1분, 5분, 15분)

### 6. DeletionMetrics (`src/services/deletion_metrics.py`)

**목적**: 삭제 작업 모니터링 및 통계

| 메서드 | 파라미터 | 반환값 | 설명 |
|--------|---------|--------|------|
| `get_deletion_stats` | db, hours | Dict | N시간 동안의 삭제 통계 |
| `log_batch_run` | db, stats, run_duration | None | 배치 실행 로그 기록 |
| `get_failure_alerts` | db | Dict | 실패율 높은 삭제 작업 알림 |

**반환 메트릭**:
```
{
  "total_deleted": 총 삭제 그룹 수,
  "successful_deletions": 성공 건수,
  "failed_deletions": 재시도 건수,
  "success_rate": 성공률(%),
  "avg_submissions_per_group": 평균 제출 수,
  "avg_retry_count": 평균 재시도 횟수
}
```

### 7. IntervalExtractor (`src/services/interval_extractor.py`)

**목적**: 시간 간격 데이터 변환 및 정규화

| 메서드 | 파라미터 | 반환값 | 설명 |
|--------|---------|--------|------|
| `extract` | raw_schedule_data | List[IntervalData] | 원본 데이터 → 정규화된 간격 |
| `normalize_slot` | start_min, end_min, unit | (start, end) | 시간 슬롯 정규화 |

---

## 저장소 계층

저장소 계층은 데이터베이스 접근을 담당합니다.

### BaseRepository (`src/repositories/base.py`)

**목적**: 모든 저장소의 기본 CRUD 작업

| 메서드 | 파라미터 | 반환값 | 설명 |
|--------|---------|--------|------|
| `create` | **kwargs | T | 새 엔티티 생성 |
| `get_by_id` | entity_id | Optional[T] | ID로 조회 |
| `list_all` | limit, offset | List[T] | 페이징과 함께 전체 조회 |
| `update` | entity_id, **kwargs | Optional[T] | 엔티티 업데이트 |
| `delete` | entity_id | bool | ID로 삭제 |
| `delete_instance` | instance: T | bool | 인스턴스 삭제 |
| `find_by_id` | entity_id | Optional[T] | ID로 조회 (별칭) |
| `commit` | - | None | 트랜잭션 커밋 |
| `rollback` | - | None | 트랜잭션 롤백 |

### GroupRepository (`src/repositories/group.py`)

**상속**: BaseRepository[Group]

| 메서드 | 파라미터 | 반환값 | 설명 |
|--------|---------|--------|------|
| `create_group` | name, display_unit_minutes | Group | 그룹 생성 (토큰/URL 포함) |
| `find_by_invite_url` | invite_url | Optional[Group] | 초대 URL로 검색 |
| `find_by_share_url` | share_url | Optional[Group] | 공유 URL로 검색 |
| `find_by_name` | name | Optional[Group] | 그룹명으로 검색 |
| `list_expired` | before_time | List[Group] | 만료된 그룹 조회 |
| `list_by_creator` | creator_id | List[Group] | 생성자별 그룹 조회 |

### SubmissionRepository (`src/repositories/submission.py`)

**상속**: BaseRepository[Submission]

| 메서드 | 파라미터 | 반환값 | 설명 |
|--------|---------|--------|------|
| `create_submission` | group_id, nickname, status, error_reason | Submission | 제출 생성 |
| `list_by_group` | group_id | List[Submission] | 그룹의 모든 제출 |
| `list_successful_by_group` | group_id | List[Submission] | 성공한 제출만 조회 |
| `find_by_group_and_nickname` | group_id, nickname | Optional[Submission] | 그룹 내 닉네임 중복 검사 |
| `count_by_group` | group_id | int | 그룹 제출 수 |
| `count_successful_by_group` | group_id | int | 성공 제출 수 |
| `delete_by_group` | group_id | int | 그룹의 모든 제출 삭제 |

### IntervalRepository (`src/repositories/interval.py`)

**상속**: BaseRepository[Interval]

| 메서드 | 파라미터 | 반환값 | 설명 |
|--------|---------|--------|------|
| `create_interval` | submission_id, day_of_week, start_minute, end_minute | Interval | 시간 간격 생성 |
| `list_by_submission` | submission_id | List[Interval] | 제출의 모든 간격 |
| `list_by_group` | group_id | List[Interval] | 그룹의 모든 간격 |
| `delete_by_submission` | submission_id | int | 제출의 간격 삭제 |
| `delete_by_group` | group_id | int | 그룹의 모든 간격 삭제 |

### FreeTimeResultRepository (`src/repositories/free_time_result.py`)

**상속**: BaseRepository[FreeTimeResult]

| 메서드 | 파라미터 | 반환값 | 설명 |
|--------|---------|--------|------|
| `create_result` | group_id, candidate_slots, version | FreeTimeResult | 결과 생성 |
| `get_latest_by_group` | group_id | Optional[FreeTimeResult] | 그룹의 최신 결과 |
| `list_by_group` | group_id, limit | List[FreeTimeResult] | 그룹의 결과 히스토리 |
| `delete_by_group` | group_id | int | 그룹의 모든 결과 삭제 |

### DeletionLogRepository (`src/repositories/deletion_log.py`)

**상속**: BaseRepository[DeletionLog]

| 메서드 | 파라미터 | 반환값 | 설명 |
|--------|---------|--------|------|
| `log_deletion` | group_id, submission_count, error_code, retry_count | DeletionLog | 삭제 로그 기록 |
| `list_by_time_range` | start_time, end_time | List[DeletionLog] | 시간 범위 로그 조회 |
| `list_failed` | hours | List[DeletionLog] | N시간 내 실패 로그 |

---

## 모델 계층

### Group (`src/models/models.py`)

```python
class Group(Base):
    """그룹 데이터 모델"""
    # 주요 속성
    id: UUID
    name: str
    display_unit_minutes: int  # 10, 20, 30, 60
    created_at: datetime
    last_activity_at: datetime
    expires_at: datetime  # last_activity_at + 72h
    admin_token: str  # 관리자 전용 토큰
    invite_url: str
    share_url: str
    max_participants: int = 50
    
    # 관계
    submissions: List[Submission]
    
# 메서드
def is_expired() -> bool:
    """그룹이 만료되었는지 확인"""
def __repr__() -> str:
    """디버깅용 표현"""
```

### Submission (`src/models/models.py`)

```python
class Submission(Base):
    """사용자 제출 데이터 모델"""
    # 주요 속성
    id: UUID
    group_id: UUID (FK)
    nickname: str  # 참여자 3단어 무작위 닉네임
    status: SubmissionStatus  # SUCCESS / FAILED
    error_reason: Optional[str]
    created_at: datetime
    
    # 관계
    group: Group
    intervals: List[Interval]
```

**SubmissionStatus Enum**:
- `SUCCESS`: OCR 파싱 성공
- `FAILED`: OCR 파싱 실패

### Interval (`src/models/models.py`)

```python
class Interval(Base):
    """시간 간격 데이터 모델"""
    id: UUID
    submission_id: UUID (FK)
    day_of_week: int  # 0=Monday, 6=Sunday
    start_minute: int  # 0~1440 (24h)
    end_minute: int
    
    # 관계
    submission: Submission
```

### FreeTimeResult (`src/models/models.py`)

```python
class FreeTimeResult(Base):
    """계산된 공통 빈시간"""
    id: UUID
    group_id: UUID (FK)
    candidate_slots: JSON  # 후보 시간 리스트
    version: int  # 계산 버전
    calculated_at: datetime
    
    # 관계
    group: Group
```

### DeletionLog (`src/models/models.py`)

```python
class DeletionLog(Base):
    """삭제 작업 감사 로그"""
    id: UUID
    group_id: UUID
    deleted_at: datetime
    submission_count: int
    error_code: Optional[str]  # None = 성공
    retry_count: int
```

---

## 유틸리티/라이브러리

### 1. Nickname Generator (`src/lib/nickname.py`)

| 함수 | 파라미터 | 반환값 | 설명 |
|------|---------|--------|------|
| `generate_nickname` | - | str | 3단어 무작위 닉네임 생성 |

**예**: "행운한 파란 달"

### 2. SlotUtils (`src/lib/slot_utils.py`)

| 함수 | 파라미터 | 반환값 | 설명 |
|------|---------|--------|------|
| `normalize_slot` | start_min, end_min, unit_min | (int, int) | 시간 슬롯 정규화 |
| `get_conflicting_slots` | intervals1, intervals2 | List[Interval] | 두 시간 집합의 교집합 |
| `merge_adjacent_slots` | intervals | List[Interval] | 인접한 슬롯 병합 |
| `round_to_unit` | value, unit | int | 값을 단위로 반올림 |

### 3. IntervalData (`src/services/interval_extractor.py`)

```python
@dataclass
class IntervalData:
    """추출된 시간 간격 데이터"""
    day_of_week: int  # 0-6
    start_minute: int
    end_minute: int
```

---

## API 엔드포인트

### 1. Groups API (`src/api/groups.py`)

| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/groups` | POST | 새 그룹 생성 |
| `/groups/<group_id>` | GET | 그룹 상세 조회 |
| `/groups/<group_id>/stats` | GET | 그룹 통계 조회 |

**응답 예**:
```json
{
  "id": "uuid",
  "name": "그룹명",
  "invite_url": "https://.../invite/...",
  "share_url": "https://.../share/...",
  "display_unit_minutes": 30,
  "expires_at": "2026-02-28T10:00:00Z"
}
```

### 2. Submissions API (`src/api/submissions.py`)

| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/groups/<id>/submissions` | POST | 이미지 제출 + OCR 파싱 |
| `/groups/<id>/submissions` | GET | 그룹의 제출 조회 |
| `/submissions/<id>` | DELETE | 제출 삭제 |

### 3. FreeTime API (`src/api/free_time.py`)

| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/groups/<id>/free-time` | GET | 폴링 + 공통 빈시간 결과 반환 |

**응답 예** (겹치지 않는 시간 - Complement):
```json
{
  "candidate_slots": [
    {
      "day_of_week": 0,
      "start_minute": 0,     // 00:00
      "end_minute": 540,     // 09:00 (참여자 A가 도착 전)
      "overlap_count": 0,
      "availability_percentage": 0
    },
    {
      "day_of_week": 0,
      "start_minute": 720,   // 12:00
      "end_minute": 1440,    // 24:00 (모두 퇴근 후)
      "overlap_count": 0,
      "availability_percentage": 0
    }
  ],
  "version": 1,
  "calculated_at": "2026-02-25T10:30:00Z"
}
```

### 4. Health API (`src/api/health.py`)

| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/health` | GET | 헬스 체크 |

---

## 메서드 호출 체인

### 시나리오 1: 그룹 생성 → 이미지 제출 → 결과 조회

```
POST /groups
├── GroupService.create_group()
│   ├── GroupRepository.create_group()
│   │   ├── 토큰, URL 생성
│   │   └── DB 저장
│   └── Session.commit()
└── 응답: Group 객체

POST /groups/<id>/submissions (이미지 파일)
├── SubmissionService.create_submission()
│   ├── OCRService.parse_image()
│   │   ├── 이미지 전처리
│   │   ├── Tesseract OCR 실행
│   │   └── EverytimeScheduleParser.parse()
│   ├── IntervalExtractor.extract()
│   │   └── 시간 슬롯 정규화
│   ├── SubmissionRepository.create_submission()
│   ├── IntervalRepository.create_interval()
│   └── CalculationService.trigger_calculation()
│       ├── SubmissionRepository.list_successful_by_group()
│       ├── IntervalRepository.list_by_submission()
│       ├── 모든 참여자 시간 합침 (Union)
│       ├── _calculate_time_complement() - 여집합 계산
│       └── FreeTimeResultRepository.create_result()
└── 응답: Submission 객체

GET /groups/<id>/free-time (폴링)
├── DeletionService.check_expiry_by_id()
├── GroupService.get_group()
├── FreeTimeResultRepository.get_latest_by_group()
└── 응답: FreeTimeResult 객체
   (최소 1명 이상이 없는 시간 반환)
```

### 시나리오 2: 배치 삭제 작업

```
K8s CronJob (10분마다)
├── GroupRepository.list_expired()
└── 각 그룹마다:
    ├── SubmissionRepository.delete_by_group()
    ├── IntervalRepository.delete_by_group()
    ├── FreeTimeResultRepository.delete_by_group()
    ├── GroupRepository.delete()
    ├── DeletionLogRepository.log_deletion()
    └── 실패 시: retry_count++, 1분 후 재시도
```

### 시나리오 3: Lazy 삭제

```
GET /groups/<id>/free-time (폴링)
├── DeletionService.check_expiry_by_id()
├── 만료됨?
│   └── 410 Gone 응답 + 배치 작업 표시
└── 정상
    └── 결과 반환
```

---

## 메서드 복잡도 분석

### O(n × m) 복잡도:
- `CalculationService._calculate_and_intersection()`: n = 참여자 수, m = 간격 수
  - 이전(AND): O(n × m²) → 현재(Complement): O(n × m) ⭐ **성능 개선**
- `CalculationService._calculate_time_complement()`: m = 합쳐진 간격 수

### O(n) 복잡도:
- `IntervalRepository.list_by_group()`: n = 그룹의 간격 수
- `SubmissionRepository.list_successful_by_group()`: n = 제출 수
- `CalculationService.trigger_calculation()`: n = 참여자 수

### O(1) 복잡도:
- `GroupRepository.create_group()`
- `SubmissionService.create_submission()`
- `DeletionService.check_expiry()`

### O(n log n) 복잡도:
- `SlotUtils.merge_adjacent_slots()`: 정렬이 포함됨

---

## 에러 코드 매핑

| 에러 코드 | 설명 | HTTP 상태 |
|---------|------|---------|
| `GROUP_NOT_FOUND` | 그룹 없음 | 404 |
| `GROUP_EXPIRED` | 그룹 만료 | 410 |
| `INVALID_DISPLAY_UNIT` | 잘못된 표시 단위 | 400 |
| `DUPLICATE_SUBMISSION` | 중복 닉네임 | 409 |
| `SUBMISSION_NOT_FOUND` | 제출 없음 | 404 |
| `DATABASE_ERROR` | DB 오류 | 500 |
| `CALCULATION_ERROR` | 계산 실패 | 500 |
| `OCR_ERROR` | OCR 파싱 실패 | 422 |

---

## 성능 목표

| 메트릭 | 목표 | 확인 방법 |
|-------|------|---------|
| 이미지 업로드 → 결과 반환 | < 5초 | 로드 테스트 |
| 자유시간 계산 | < 1초 | 프로파일링 |
| 폴링 응답 | < 500ms | 모니터링 |
| 삭제 성공률 | 100% (재시도 3회) | 배치 시뮬레이션 |
| 테스트 커버리지 | 85%+ | pytest --cov |

---

## 추가 리소스

- 전체 API 스펙: `specs/001-meet-match/contracts/openapi.yaml`
- 아키텍처: `docs/ARCHITECTURE.md`
- 테스트: `tests/` 디렉토리
- 배포: `docs/DEPLOYMENT.md`

