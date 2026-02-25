# 메서드 호출 관계도 및 데이터 흐름

## 1. E2E 플로우: 그룹 생성 → 이미지 제출 → 결과 조회

```
┌─────────────────────────────────────────────────────────────────┐
│ 단계 1: POST /groups (그룹 생성)                              │
└─────────────────────────────────────────────────────────────────┘

클라이언트 요청
  │
  ├─> API Handler (groups.py)
  │    │
  │    └─> GroupService.create_group(group_name=None, display_unit_minutes=30)
  │         │
  │         ├─> validate display_unit ✓
  │         │
  │         ├─> NicknameGenerator.generate_nickname()
  │         │    └─> 반환: "행운한 파란 달"
  │         │
  │         ├─> GroupService._group_name_exists("행운한 파란 달")
  │         │    └─> GroupRepository.find_by_name()
  │         │         └─> DB Query: SELECT * FROM groups WHERE name='...'
  │         │
  │         └─> GroupRepository.create_group(name, display_unit_minutes)
  │              │
  │              ├─> UUID 4개 생성:
  │              │    ├─ group_id
  │              │    ├─ admin_token
  │              │    └─ (URL 생성)
  │              │
  │              ├─> insert into groups:
  │              │    │
  │              │    ├─ id, name, display_unit_minutes
  │              │    ├─ created_at = NOW()
  │              │    ├─ last_activity_at = NOW()
  │              │    ├─ expires_at = NOW() + 72h
  │              │    ├─ admin_token, invite_url, share_url
  │              │    └─ max_participants = 50
  │              │
  │              └─> Session.commit() ✓ (또는 flush)
  │
  └─> API 응답: 200 OK + Group 객체
       {
         "id": "550e8400-e29b-41d4-a716-446655440000",
         "name": "행운한 파란 달",
         "invite_url": "https://gonggang.example.com/invite/...",
         "share_url": "https://gonggang.example.com/share/...",
         "display_unit_minutes": 30,
         "expires_at": "2026-02-28T10:00:00Z",
         "max_participants": 50
       }
```

---

```
┌─────────────────────────────────────────────────────────────────┐
│ 단계 2: POST /groups/{id}/submissions (이미지 제출)           │
│        + OCR 파싱 + 시간 정규화 + 계산 트리거               │
└─────────────────────────────────────────────────────────────────┘

클라이언트 요청 (이미지 파일 + group_id)
  │
  ├─> API Handler (submissions.py)
  │    │
  │    ├─> GroupService.get_group(group_id)
  │    │    │
  │    │    ├─> GroupRepository.find_by_id(group_id)
  │    │    │    └─> DB Query: SELECT * FROM groups WHERE id='...'
  │    │    │
  │    │    └─> Group.is_expired()? 만료됨 → 410 Gone ✗
  │    │         └─> 정상 → 계속 진행 ✓
  │    │
  │    └─> SubmissionService.create_submission(
  │         group_id, nickname='방문자', intervals=[], ocr_success=TODO)
  │         │
  │         ├─ Step 1: OCR 파싱 ────────────────────────────────
  │         │  │
  │         │  ├─> OCRService.parse_image(image_bytes)
  │         │  │    │
  │         │  │    ├─> ImagePreprocessor.preprocess_image()
  │         │  │    │    │
  │         │  │    │    ├─ PIL.Image.open(image_bytes)
  │         │  │    │    ├─ ImageOps.autocontrast() - 명도 조정
  │         │  │    │    ├─ ImageOps.exif_transpose() - 회전 보정
  │         │  │    │    └─ ImageEnhance.Sharpness() - 선명도 향상
  │         │  │    │
  │         │  │    ├─> pytesseract.image_to_string()
  │         │  │    │    └─ "월 09:00~11:00"
  │         │  │    │       "화 14:00~16:00"
  │         │  │    │       ...
  │         │  │    │
  │         │  │    └─> EverytimeScheduleParser.parse(ocr_text)
  │         │  │         │
  │         │  │         ├─ split by '\n'
  │         │  │         ├─ 요일 검색 (월/화/수...)
  │         │  │         ├─ 시간 추출 (regex: \d{1,2}:\d{2})
  │         │  │         │
  │         │  │         └─ 반환: [
  │         │  │              {day: 'MONDAY', start: '09:00', end: '11:00'},
  │         │  │              {day: 'TUESDAY', start: '14:00', end: '16:00'},
  │         │  │              ...
  │         │  │            ]
  │         │  │
  │         │  ├─ Step 2: 시간 정규화 ─────────────────────────
  │         │  │  │
  │         │  │  ├─> IntervalExtractor.extract(raw_schedule)
  │         │  │  │    │
  │         │  │  │    ├─ for each schedule entry:
  │         │  │  │    │    │
  │         │  │  │    │    ├─ start_str='09:00' → start_min=540
  │         │  │  │    │    ├─ end_str='11:00' → end_min=660
  │         │  │  │    │    │
  │         │  │  │    │    └─> SlotUtils.normalize_slot(
  │         │  │  │    │         540, 660, display_unit=30)
  │         │  │  │    │         │
  │         │  │  │    │         ├─ start_aligned = align(540, 30)
  │         │  │  │    │         │                  = 540 (divisible)
  │         │  │  │    │         ├─ end_aligned = align(660, 30)
  │         │  │  │    │         │               = 660 (divisible)
  │         │  │  │    │         │
  │         │  │  │    │         └─ 반환: (540, 660)
  │         │  │  │    │
  │         │  │  │    └─ 생성: [
  │         │  │  │         IntervalData(day=0, start=540, end=660),
  │         │  │  │         IntervalData(day=1, start=840, end=960),
  │         │  │  │         ...
  │         │  │  │       ]
  │         │  │
  │         │  ├─ Step 3: Submission 저장 ────────────────────
  │         │  │  │
  │         │  │  ├─> NicknameGenerator.generate_nickname()
  │         │  │  │    └─> "희망 초록 사과"
  │         │  │  │
  │         │  │  ├─> SubmissionRepository.find_by_group_and_nickname()
  │         │  │  │    └─> 중복? → DuplicateSubmissionError ✗
  │         │  │  │    └─> 정상 → 계속 ✓
  │         │  │  │
  │         │  │  ├─> SubmissionRepository.create_submission(
  │         │  │  │     group_id, nickname='희망 초록 사과',
  │         │  │  │     status=SUCCESS, error_reason=None)
  │         │  │  │    │
  │         │  │  │    └─> insert into submissions:
  │         │  │  │         id, group_id, nickname, status=SUCCESS,
  │         │  │  │         created_at=NOW()
  │         │  │  │
  │         │  │  ├─> Session.flush() (ID 획득)
  │         │  │  │
  │         │  │  ├─> IntervalRepository 반복 저장 (각 간격):
  │         │  │  │    └─> create_interval(
  │         │  │  │         submission_id, day_of_week=0,
  │         │  │  │         start_minute=540, end_minute=660)
  │         │  │  │
  │         │  │  └─> Session.commit() ✓
  │         │  │
  │         │  ├─ Step 4: 자동 계산 트리거 ─────────────────
  │         │  │  │
  │         │  │  └─> CalculationService.trigger_calculation(group_id)
  │         │  │       │
  │         │  │       ├─> SubmissionRepository.list_successful_by_group(group_id)
  │         │  │       │    └─> DB Query: SELECT * FROM submissions WHERE group_id=? AND status='SUCCESS'
  │         │  │       │    └─> 반환: [submission1, submission2, ...]
  │         │  │       │
  │         │  │       ├─ for each submission:
  │         │  │       │    │
  │         │  │       │    └─> IntervalRepository.list_by_submission(submission_id)
  │         │  │       │         └─> DB Query: SELECT * FROM intervals WHERE submission_id=?
  │         │  │       │         └─> 반환: [interval1, interval2, ...]
  │         │  │       │
  │         │  │       ├─> 데이터 구조:
  │         │  │       │    {
  │         │  │       │      submission_id_1: [Interval(...), ...],
  │         │  │       │      submission_id_2: [Interval(...), ...],
  │         │  │       │      ...
  │         │  │       │    }
  │         │  │       │
  │         │  │       ├─> CalculationService._calculate_and_intersection()
  │         │  │       │    │
  │         │  │       │    ├─ for day in 0..6:  # 월~일
  │         │  │       │    │    │
  │         │  │       │    │    └─ 모든 제출자의 day별 간격 수집 (Complement)
  │         │  │       │    │         Submission 1: [(540, 660), (900, 1080)]
  │         │  │       │    │         Submission 2: [(540, 720), (840, 1140)]
  │         │  │       │    │
  │         │  │       │    ├─ 모든 간격 병합:
  │         │  │       │    │    SlotUtils.merge_adjacent_slots()
  │         │  │       │    │    [(540, 660), (540, 720), (840, 1140), (900, 1080)]
  │         │  │       │    │    → 병합 결과: [(540, 1140)]
  │         │  │       │    │
  │         │  │       │    ├─ Complement 계산 (24시간 내 빈 시간):
  │         │  │       │    │    _calculate_time_complement([(540, 1140)])
  │         │  │       │    │    → 반환: [(0, 540), (1140, 1440)]
  │         │  │       │    │
  │         │  │       │    └─ 반환:
  │         │  │       │         {
  │         │  │       │           0: [(0, 540), (1140, 1440)],
  │         │  │       │           1: [(0, 540), (720, 840), (1140, 1440)],
  │         │  │       │           ...
  │         │  │       │         }
  │         │  │       │
  │         │  │       ├─> CalculationService._store_calculation_result()
  │         │  │       │    │
  │         │  │       │    ├─> CandidateSlot 생성:
  │         │  │       │    │    [
  │         │  │       │    │      CandidateSlot(
  │         │  │       │    │        day_of_week=0,
  │         │  │       │    │        start_minute=0,
  │         │  │       │    │        end_minute=540,
  │         │  │       │         │        gap_count=1,
  │         │  │       │    │        total_participants=2,
  │         │  │       │    │        availability_percentage=100%
  │         │  │       │    │      ),
  │         │  │       │    │      ...
  │         │  │       │    │    ]
  │         │  │       │    │
  │         │  │       │    └─> FreeTimeResultRepository.create_result(
  │         │  │       │         group_id, candidate_slots, version=1)
  │         │  │       │
  │         │  │       └─> Session.commit() ✓
  │
  └─> API 응답: 201 Created + Submission 객체
       {
         "id": "submission_uuid",
         "group_id": "group_uuid",
         "nickname": "희망 초록 사과",
         "status": "SUCCESS",
         "created_at": "2026-02-25T10:30:00Z"
       }
```

---

```
┌─────────────────────────────────────────────────────────────────┐
│ 단계 3: GET /groups/{id}/free-time (폴링 + 결과 조회)         │
└─────────────────────────────────────────────────────────────────┘

클라이언트 요청 (group_id)
  │
  ├─> API Handler (free_time.py)
  │    │
  │    ├─ Step 1: Lazy 삭제 검사 ─────────────────────────
  │    │  │
  │    │  ├─> DeletionService.check_expiry_by_id(db, group_id)
  │    │  │    │
  │    │  │    ├─> db.query(Group).filter(id=group_id).first()
  │    │  │    │    └─> Group 객체 획득 또는 None
  │    │  │    │
  │    │  │    └─> Group.expires_at <= NOW()?
  │    │  │         └─> True (만료됨)
  │    │  │              └─> return True
  │    │  │              └─> API 응답: 410 Gone ✗
  │    │  │         └─> False (정상)
  │    │  │              └─> return False
  │    │  │              └─> 계속 진행 ✓
  │    │  │
  │    │  ├─ Step 2: 마지막 활동 시간 업데이트 ──────────
  │    │  │  │
  │    │  │  └─> GroupService.update_last_activity(group_id)
  │    │  │       │
  │    │  │       ├─> last_activity_at = NOW()
  │    │  │       ├─> expires_at = NOW() + 72h (연장)
  │    │  │       └─> DB Update + commit
  │    │  │
  │    │  ├─ Step 3: 최신 계산 결과 조회 ───────────────
  │    │  │  │
  │    │  │  └─> FreeTimeResultRepository.get_latest_by_group(group_id)
  │    │  │       │
  │    │  │       └─> DB Query:
  │    │  │            SELECT * FROM free_time_results
  │    │  │            WHERE group_id=?
  │    │  │            ORDER BY version DESC
  │    │  │            LIMIT 1
  │    │  │
  │    │  │       └─> FreeTimeResult 객체 또는 None
  │    │  │
  │    │  └─> API 응답: 200 OK + 결과
  │    │       {
  │    │         "candidate_slots": [
  │    │           {
  │    │             "day_of_week": 0,
  │    │             "start_minute": 540,
  │    │             "end_minute": 660,
  │    │             "overlap_count": 2,
  │    │             "availability_percentage": 100
  │    │           },
  │    │           ...
  │    │         ],
  │    │         "version": 1,
  │    │         "calculated_at": "2026-02-25T10:30:00Z"
  │    │       }
```

---

## 2. 배치 삭제 흐름 (CronJob)

```
┌─────────────────────────────────────────────────────────────────┐
│ K8s CronJob (5-15분마다)                                        │
│ command: python -m src.cli.batch_deletion --force              │
└─────────────────────────────────────────────────────────────────┘

CronJob 트리거
  │
  ├─> BatchDeletionCLI.execute()
  │    │
  │    ├─ Step 1: 만료된 그룹 조회 ─────────────────────
  │    │  │
  │    │  ├─> GroupRepository.list_expired(before_time=NOW())
  │    │  │    └─> DB Query:
  │    │  │         SELECT * FROM groups
  │    │  │         WHERE expires_at <= NOW()
  │    │  │
  │    │  └─> expired_groups = [Group(...), Group(...), ...]
  │    │
  │    ├─ Step 2: 그룹별 트랜잭션 삭제 ──────────────
  │    │  │
  │    │  └─ for each expired_group:
  │    │       │
  │    │       ├─> Session.begin_transaction()
  │    │       │
  │    │       ├─ Step 2.1: Cascade 삭제 ───────────
  │    │       │  │
  │    │       │  ├─> SubmissionRepository.delete_by_group(group_id)
  │    │       │  │    └─> DELETE FROM submissions WHERE group_id=?
  │    │       │  │
  │    │       │  ├─> IntervalRepository.delete_by_group(group_id)
  │    │       │  │    └─> DELETE FROM intervals
  │    │       │  │         WHERE submission_id IN (
  │    │       │  │           SELECT id FROM submissions WHERE group_id=?
  │    │       │  │         )
  │    │       │  │
  │    │       │  ├─> FreeTimeResultRepository.delete_by_group(group_id)
  │    │       │  │    └─> DELETE FROM free_time_results WHERE group_id=?
  │    │       │  │
  │    │       │  └─> GroupRepository.delete(group_id)
  │    │       │       └─> DELETE FROM groups WHERE id=?
  │    │       │
  │    │       ├─ Step 2.2: 성공 로그 기록 ────────
  │    │       │  │
  │    │       │  └─> DeletionLogRepository.log_deletion(
  │    │       │       group_id, submission_count=5,
  │    │       │       error_code=None, retry_count=0)
  │    │       │       │
  │    │       │       └─> insert into deletion_logs:
  │    │       │            id, group_id, deleted_at=NOW(),
  │    │       │            submission_count, error_code=None, retry_count=0
  │    │       │
  │    │       ├─> Session.commit() ✓
  │    │       │
  │    │       └─> logger.info(f"Deleted group {group_id}")
  │    │
  │    ├─ Step 3: 실패 처리 & 재시도 ────────────
  │    │  │
  │    │  └─ if any exception:
  │    │       │
  │    │       ├─> Session.rollback()
  │    │       │
  │    │       ├─> DeletionLogRepository.log_deletion(
  │    │       │    group_id, submission_count=?,
  │    │       │    error_code=e.__class__.__name__, retry_count=1)
  │    │       │
  │    │       ├─> retry_count < 3?
  │    │       │    ├─ Yes:
  │    │       │    │  ├─ 1회차 실패: 1분 후 재시도
  │    │       │    │  ├─ 2회차 실패: 5분 후 재시도
  │    │       │    │  └─ 3회차 실패: 15분 후 재시도
  │    │       │    │
  │    │       │    └─ No:
  │    │       │       └─> raise alert() # PagerDuty/Slack
  │    │       │
  │    │       └─> logger.error(f"Failed to delete {group_id}: {e}")
  │    │
  │    ├─ Step 4: 통계 기록 ──────────────────────
  │    │  │
  │    │  └─> DeletionMetrics.log_batch_run(
  │    │       db, stats={
  │    │         "total_deleted": 12,
  │    │         "successful": 12,
  │    │         "failed": 0
  │    │       },
  │    │       run_duration_seconds=5.2)
  │    │
  │    └─> logger.info("Batch deletion complete")
```

---

## 3. 클래스 간 의존성 그래프

```
┌─────────────────────────────────────────────────────────────────┐
│                    API 계층 (Handlers)                          │
├─────────────────────────────────────────────────────────────────┤
│  GroupAPI  SubmissionAPI  FreeTimeAPI  HealthAPI              │
└─────────────────────────────────────────────────────────────────┘
        ↓              ↓              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    서비스 계층 (Business Logic)                │
├─────────────────────────────────────────────────────────────────┤
│  GroupService                                                   │
│    ├─ create_group()                                             │
│    ├─ get_group()                                                │
│    └─ update_last_activity()                                     │
│                                                                  │
│  SubmissionService                                              │
│    ├─ create_submission()                                        │
│    ├─ get_group_submissions()                                    │
│    └─ delete_submission()                                        │
│                    ↓                                              │
│    CalcuationService (lazy injection)                           │
│      ├─ trigger_calculation()                                    │
│      └─ _calculate_and_intersection()                            │
│                                                                  │
│  OCRService                                                      │
│    ├─ parse_image()                                              │
│    └─ preprocess_image()                                         │
│                                                                  │
│  DeletionService                                                │
│    ├─ check_expiry_by_id()                                       │
│    └─ mark_soft_deleted()                                        │
│                                                                  │
│  DeletionMetrics                                                │
│    ├─ get_deletion_stats()                                       │
│    ├─ log_batch_run()                                            │
│    └─ get_failure_alerts()                                       │
└─────────────────────────────────────────────────────────────────┘
        ↓              ↓              ↓              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    저장소 계층 (Data Access)                   │
├─────────────────────────────────────────────────────────────────┤
│  BaseRepository                                                  │
│    ├─ create()                                                   │
│    ├─ get_by_id()                                                │
│    ├─ list_all()                                                 │
│    ├─ update()                                                   │
│    ├─ delete()                                                   │
│    └─ commit() / rollback()                                      │
│                                                                  │
│  GroupRepository(BaseRepository[Group])                         │
│    ├─ create_group()                                             │
│    ├─ find_by_invite_url()                                       │
│    ├─ find_by_share_url()                                        │
│    └─ list_expired()                                             │
│                                                                  │
│  SubmissionRepository(BaseRepository[Submission])               │
│    ├─ create_submission()                                        │
│    ├─ list_by_group()                                            │
│    ├─ list_successful_by_group()                                 │
│    ├─ find_by_group_and_nickname()                               │
│    └─ delete_by_group()                                          │
│                                                                  │
│  IntervalRepository(BaseRepository[Interval])                   │
│    ├─ create_interval()                                          │
│    ├─ list_by_submission()                                       │
│    ├─ list_by_group()                                            │
│    └─ delete_by_group()                                          │
│                                                                  │
│  FreeTimeResultRepository (BaseRepository[FreeTimeResult])      │
│    ├─ create_result()                                            │
│    ├─ get_latest_by_group()                                      │
│    └─ delete_by_group()                                          │
│                                                                  │
│  DeletionLogRepository (BaseRepository[DeletionLog])            │
│    ├─ log_deletion()                                             │
│    ├─ list_by_time_range()                                       │
│    └─ list_failed()                                              │
└─────────────────────────────────────────────────────────────────┘
        ↓              ↓              ↓              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    모델 계층 (Data Models)                      │
├─────────────────────────────────────────────────────────────────┤
│  Base (SQLAlchemy declarative)                                  │
│                                                                  │
│  Group (Base)                                                    │
│    - id, name, created_at, expires_at, ...                      │
│    - is_expired() → bool                                         │
│    - submissions → [Submission]                                  │
│                                                                  │
│  Submission (Base)                                              │
│    - id, group_id, nickname, status, ...                        │
│    - group → Group (FK)                                          │
│    - intervals → [Interval]                                      │
│                                                                  │
│  Interval (Base)                                                │
│    - id, submission_id, day_of_week, start_minute, end_minute   │
│    - submission → Submission (FK)                                │
│                                                                  │
│  FreeTimeResult (Base)                                          │
│    - id, group_id, candidate_slots, version, ...                │
│    - group → Group (FK)                                          │
│                                                                  │
│  DeletionLog (Base)                                             │
│    - id, group_id, deleted_at, submission_count, ...            │
└─────────────────────────────────────────────────────────────────┘
        ↓              ↓              ↓              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    데이터베이스 (PostgreSQL)                    │
├─────────────────────────────────────────────────────────────────┤
│  groups (group_id PK, expires_at INDEX)                         │
│  submissions (submission_id PK, group_id FK, status INDEX)      │
│  intervals (interval_id PK, submission_id FK)                   │
│  free_time_results (result_id PK, group_id FK, version)         │
│  deletion_logs (log_id PK, group_id INDEX, deleted_at INDEX)    │
└─────────────────────────────────────────────────────────────────┘

───────────────────────────────────────────────────────────────
        ↓ (보조 라이브러리)
┌─────────────────────────────────────────────────────────────────┐
│                    유틸리티 / 라이브러리                        │
├─────────────────────────────────────────────────────────────────┤
│  NicknameGenerator                                              │
│    └─ generate_nickname() → str                                 │
│                                                                  │
│  IntervalExtractor                                              │
│    └─ extract(raw_data) → List[IntervalData]                    │
│                                                                  │
│  SlotUtils                                                      │
│    ├─ normalize_slot()                                           │
│    ├─ get_conflicting_slots()                                    │
│    ├─ merge_adjacent_slots()                                     │
│    └─ round_to_unit()                                            │
│                                                                  │
│  EverytimeScheduleParser                                        │
│    └─ parse(text) → List[Dict]                                  │
│                                                                  │
│  CandidateSlot (dataclass)                                      │
│    - day_of_week, start_minute, end_minute                      │
│    - overlap_count, availability_percentage                     │
│                                                                  │
│  IntervalData (dataclass)                                       │
│    - day_of_week, start_minute, end_minute                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. 타임라인 기반 데이터 흐름

```
T=0초: 사용자 이미지 업로드
├─ 이미지 메모리 로드 (메모리만, 디스크 저장 안 함)
└─ API 요청 시작

T=0.1초: OCR 처리
├─ 이미지 전처리 (PIL)
├─ Tesseract OCR 실행 (한국어)
└─ 텍스트 추출

T=0.5초: 파싱 & 정규화
├─ 스케줄 텍스트 파싱
├─ 시간 슬롯 정규화
└─ IntervalData 객체 생성

T=1초: 데이터베이스 저장
├─ Submission 생성
├─ Interval들 다중 삽입
└─ Transaction commit

T=1.5초: 자동 계산
├─ 모든 성공 Submission 조회
├─ AND 교집합 계산
├─ 후보 시간 생성
└─ FreeTimeResult 저장

T=2초: 응답
└─ JSON 응답 반환 (submission_id + 계산 상태)

T=2~5초: 사용자 폴링
├─ 매초 GET /groups/<id>/free-time
├─ 만료 확인 (Lazy deletion)
├─ 계산 상태 확인
└─ 완료 시 candidate_slots 반환

───────────────────────────────────
T=72시간: 자동 삭제 단계
├─ expires_at <= NOW() 체크
├─ Cascade 삭제:
│  ├─ submissions 테이블
│  ├─ intervals 테이블
│  ├─ free_time_results 테이블
│  └─ groups 테이블
├─ deletion_logs 기록
└─ 재시도 로직 (실패 시)
```

---

## 5. 메서드 상호 호출 매트릭스

```
행(호출자) vs 열(피호출자):

                     Service 메서드
┌──────────────────┬─────┬──────┬─────────┬────┬──────┐
│                  │ GS  │ SS   │ CS      │ OS │ DS   │
├──────────────────┼─────┼──────┼─────────┼────┼──────┤
│ GroupAPI         │ ✓   │      │         │    │      │
│ SubmissionAPI    │ ✓   │ ✓    │         │ ✓  │      │
│ FreeTimeAPI      │ ✓   │      │         │    │ ✓    │
│ HealthAPI        │     │      │         │    │      │
│ BatchDeletionCLI │ ✓   │      │         │    │ ✓    │
└──────────────────┴─────┴──────┴─────────┴────┴──────┘

범례:
GS = GroupService
SS = SubmissionService
CS = CalculationService
OS = OCRService
DS = DeletionService

                     Repository 메서드
┌──────────────────┬────┬───┬────┬────┬──────┐
│                  │ GR │ SR│ IR │ FR │ DLR  │
├──────────────────┼────┬───┬────┬────┬──────┤
│ GroupService     │ ✓  │   │    │    │      │
│ SubmissionSvc    │    │ ✓ │ ✓  │    │      │
│ CalculationSvc   │    │ ✓ │ ✓  │ ✓  │      │
│ DeletionService  │    │   │    │    │      │
│ BatchDeleteCLI   │ ✓  │ ✓ │ ✓  │ ✓  │ ✓    │
└──────────────────┴────┴───┴────┴────┴──────┘

범례:
GR = GroupRepository
SR = SubmissionRepository
IR = IntervalRepository
FR = FreeTimeResultRepository
DLR = DeletionLogRepository
```

---

## 6. 에러 처리 경로

```
try:
  create_submission()
    │
    ├─ DuplicateSubmissionError
    │  └─ 409 Conflict
    │
    ├─ OCR 실패
    │  ├─ 상태: FAILED
    │  ├─ error_reason: "OCR failed"
    │  └─ 200 OK (제출은 저장됨)
    │
    ├─ 계산 실패
    │  ├─ 로그: "Calculation failed"
    │  ├─ 제출 상태: SUCCESS (정상)
    │  └─ 계산은 재시도 (폴링 시)
    │
    └─ Database Error
       └─ 500 Internal Server Error
```

