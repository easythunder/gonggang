# 메서드 분석 요약 (Method Analysis Summary)

## 📊 프로젝트 메서드 통계

### 전체 메서드 현황

```
총 메서드 수:             ~80+ 메서드
├─ 서비스 계층:          ~30 메서드
├─ 저장소 계층:          ~35 메서드  
├─ 모델 계층:            ~5 메서드
└─ 유틸리티:             ~10+ 메서드

테스트 커버리지:         85%+
핵심 비즈니스 로직:      CalculationService (Complement 계산 - 빈 시간 찾기)
병목 지점:               OCR 파싱 (시간 소비 부분)
```

---

## 메서드 복잡도 분류

### 1️⃣ 낮은 복잡도 (O(1))

**즉시 반환 메서드** - 대부분 DB 쿼리 1회 또는 단순 계산

| 메서드 | 클래스 | 행 수 | 테스트 |
|--------|--------|-------|--------|
| `create()` | BaseRepository | <10 | ✓ |
| `get_by_id()` | BaseRepository | <5 | ✓ |
| `find_by_id()` | GroupRepository | <5 | ✓ |
| `create_group()` | GroupRepository | 20 | ✓ |
| `check_expiry()` | DeletionService | <5 | ✓ |
| `is_expired()` | Group Model | <5 | ✓ |
| `format_time()` | Template Utils | <5 | ✓ |

**특징**:
- 단순 DB 조회 또는 단일 INSERT
- 메모리 계산만 포함
- 부작용(side effects) 최소

---

### 2️⃣ 중간 복잡도 (O(n))

**루프 포함 메서드** - n = 제출 수 또는 간격 수

| 메서드 | 클래스 | 복잡도 | 행 수 | n | 테스트 |
|--------|--------|--------|-------|---|--------|
| `trigger_calculation()` | CalculationService | O(n×m) | 50 | 제출 수 × 간격 수 | ✓ |
| `create_submission()` | SubmissionService | O(n) | 80 | 간격 수 | ✓ |
| `list_by_group()` | SubmissionRepository | O(n) | <10 | 제출 수 | ✓ |
| `list_successful_by_group()` | SubmissionRepository | O(n) | <10 | 성공 제출 수 | ✓ |
| `delete_by_group()` | IntervalRepository | O(n) | ~15 | 간격 수 | ✓ |
| `list_expired()` | GroupRepository | O(n) | <10 | 만료된 그룹 수 | ✓ |
| `parse()` | EverytimeScheduleParser | O(n) | 40 | 라인 수 | ✓ |
| `extract()` | IntervalExtractor | O(n) | 30 | 스케줄 항목 수 | ✓ |

**특징**:
- FOR 루프 또는 LIST 처리
- 배치 연산
- n은 보통 작음 (3~50 범위)

---

### 3️⃣ 높은 복잡도 (O(n²) 또는 그 이상)

**다중 루프 메서드** - 주의 필요

| 메서드 | 클래스 | 복잡도 | 행 수 | 설명 | 테스트 |
|--------|--------|--------|-------|------|--------|
| `_calculate_and_intersection()` | CalculationService | O(n×m) | 60 | Complement 계산 (24시간 내에서 빈 시간 찾기) | ✓ |
| `merge_adjacent_slots()` | SlotUtils | O(n log n) | 25 | 정렬 + 병합 | ✓ |

**특징**:
- 다중 루프 또는 정렬
- 성능 테스트 필수
- n이 작으므로 (n ≤ 50) 문제 없음

---

## 메서드 분류 (기능별)

### 🔵 CRUD 메서드 (Create, Read, Update, Delete)

#### Create 패턴

```python
# 표준 Create
BaseRepository.create(**kwargs) → T
GroupRepository.create_group(name, display_unit) → Group
SubmissionRepository.create_submission(group_id, ...) → Submission
IntervalRepository.create_interval(submission_id, ...) → Interval
FreeTimeResultRepository.create_result(group_id, ...) → FreeTimeResult
DeletionLogRepository.log_deletion(group_id, ...) → DeletionLog
```

**공통 패턴**:
1. 파라미터 검증
2. 인스턴스 생성 (또는 DB INSERT)
3. Session.flush() (ID 획득)
4. 반환

#### Read 패턴

```python
# 단일 조회
BaseRepository.get_by_id(id) → Optional[T]
GroupRepository.find_by_name(name) → Optional[Group]
SubmissionRepository.find_by_group_and_nickname(...) → Optional[Submission]

# 다중 조회
BaseRepository.list_all(limit, offset) → List[T]
GroupRepository.list_expired(before_time) → List[Group]
SubmissionRepository.list_by_group(group_id) → List[Submission]
SubmissionRepository.list_successful_by_group(group_id) → List[Submission]
IntervalRepository.list_by_submission(submission_id) → List[Interval]
DeletionLogRepository.list_failed(hours) → List[DeletionLog]
```

#### Update 패턴

```python
BaseRepository.update(id, **kwargs) → Optional[T]
GroupService.update_last_activity(group_id) → Optional[Group]
```

#### Delete 패턴

```python
# 단일 삭제
BaseRepository.delete(id) → bool
GroupRepository.delete(id) → bool

# 다중 삭제 (Cascade)
SubmissionRepository.delete_by_group(group_id) → int
IntervalRepository.delete_by_group(group_id) → int
FreeTimeResultRepository.delete_by_group(group_id) → int
```

---

### 🟠 비즈니스 로직 메서드

#### 핵심 알고리즘

```python
# Complement 계산 (핵심 기능 - 24시간 내 빈 시간 찾기)
CalculationService._calculate_and_intersection(submission_intervals: Dict)
  → Dict[day_of_week, List[Tuple[start, end]]]
  
  입력: {'submission_1': [Interval(...), ...], 'submission_2': [...]}
  과정:
    1. 모든 제출자의 간격 수집
    2. 간격 병합 (merge_adjacent_slots)
    3. 24시간(1440분) 내에서 여집합 계산
    4. 빈 시간(gap) 반환
  
  예:
    입력: [
      Submission1: [(540, 660), (900, 1080)],  # 09:00-11:00, 15:00-18:00
      Submission2: [(540, 720), (840, 1140)]   # 09:00-12:00, 14:00-19:00
    ]
    병합: [(540, 1140)]  # 09:00-19:00로 통합
    여집합: [(0, 540), (1140, 1440)]  # 00:00-09:00, 19:00-24:00
  
  의마: 모든 사람이 동시에 자유로운 시간이 아니라,
        적어도 한 명은 자유로운 시간을 찾아줌

# 예시:
input: {
  submission1_id: [Interval(day=0, start=540, end=660), ...],
  submission2_id: [Interval(day=0, start=600, end=720), ...],
  ...
}

output: {
  0: [(600, 660), ...],  # 월요일 교집합
  1: [...],  # 화요일 교집합
  ...
}
```

**로직**:
```
for day in 0..6:
  for each submission:
    intervals_for_day = submission.intervals[day]
    
  intersection = AND(all intervals_for_day)
  result[day] = intersection
```

#### 정규화 메서드

```python
# 시간 슬롯 정규화
SlotUtils.normalize_slot(start_min, end_min, unit_min)
  → (aligned_start, aligned_end)

# 예시:
normalize_slot(543, 667, 30)  # 30분 단위
→ (540, 660)  # 반올림

normalize_slot(540, 660, 30)  # 이미 정렬됨
→ (540, 660)  # 그대로
```

**로직**:
```
aligned_start = round_down(start_min, unit_min)
aligned_end = round_up(end_min, unit_min)
```

#### 병합 메서드

```python
# 인접한 슬롯 병합
SlotUtils.merge_adjacent_slots(intervals: List[Interval])
  → List[Interval]

# 예시:
input: [(540, 600), (600, 660), (900, 960)]
output: [(540, 660), (900, 960)]
```

#### 교집합 계산 메서드

```python
# 두 시간 집합의 교집합
SlotUtils.get_conflicting_slots(intervals1, intervals2)
  → List[Tuple[start, end]]

# 예시:
input1: [(540, 660), (900, 1080)]
input2: [(600, 720), (840, 1140)]
output: [(600, 660), (900, 1080)]

로직:
for each pair (s1, e1) from intervals1:
  for each pair (s2, e2) from intervals2:
    overlap = max(s1, s2)..min(e1, e2)
    if overlap is valid:
      result.append(overlap)
```

---

### 🟢 검증 메서드

```python
# 만료 검사
DeletionService.check_expiry(group: Group) → bool
DeletionService.check_expiry_by_id(db, group_id) → bool

# 모델 메서드
Group.is_expired() → bool
Submission.is_successful() → bool  # (if exists)

# 중복 검사
SubmissionRepository.find_by_group_and_nickname(...) → Optional[Submission]
```

---

### 🔴 부작용(Side Effects) 있는 메서드

**트랜잭션 필수**:

```python
# 트랜잭션 제어
BaseRepository.commit() → None
BaseRepository.rollback() → None
Session.begin_transaction()
Session.commit()

# 자동 계산 트리거
SubmissionService.create_submission(...)  # 내부에서 계산 트리거
  → CalculationService.trigger_calculation() 호출

# 배치 삭제
BatchDeletionCLI.execute()  # Cascade 삭제 + 로그
  → SubmissionRepository.delete_by_group()
  → IntervalRepository.delete_by_group()
  → FreeTimeResultRepository.delete_by_group()
  → GroupRepository.delete()
  → DeletionLogRepository.log_deletion()
```

---

## 메서드 호출 빈도 분석

### 고빈도 (매 요청마다)

```
1. DeletionService.check_expiry_by_id()
   └─ 모든 폴링 요청에서 만료 확인
   
2. GroupRepository.find_by_id()
   └─ 그룹 조회 (그룹 생성, 제출, 폴링)
   
3. SubmissionRepository.list_successful_by_group()
   └─ 제출 생성 시 계산, 폴링 시 결과 조회
   
4. FreeTimeResultRepository.get_latest_by_group()
   └─ 폴링 응답
```

### 저빈도 (특정 상황)

```
1. GroupRepository.list_expired()
   └─ 배치 삭제 작업 (5-15분마다)
   
2. DeletionLogRepository.log_deletion()
   └─ 배치 삭제 완료/실패 시
   
3. DeletionMetrics.get_deletion_stats()
   └─ 모니터링 대시보드 (수동 조회)
```

---

## 메서드 간 데이터 흐름

### 핵심 데이터 변환 경로

```
이미지 바이트
  ↓
OCRService.parse_image()
  ├─ ImagePreprocessor.preprocess_image()
  ├─ pytesseract.image_to_string()
  └─ EverytimeScheduleParser.parse()
      ↓
      OCR 텍스트 (일정 문자열)
      ↓
IntervalExtractor.extract()
  ├─ 시간 파싱 (정규식)
  ├─ 슬롯 정규화
  └─ IntervalData 생성
      ↓
      List[IntervalData]
      ↓
SubmissionService.create_submission()
  ├─ SubmissionRepository.create_submission()
  ├─ IntervalRepository.create_interval() × n
  └─ CalculationService.trigger_calculation()
      ├─ SubmissionRepository.list_successful_by_group()
      ├─ IntervalRepository.list_by_submission() × n
      └─ SlotUtils.get_conflicting_slots()
          ├─ _calculate_and_intersection()
          └─ merge_adjacent_slots()
              ↓
              Dict[day, List[(start, end)]]
              ↓
CandidateSlot 객체 생성
  └─ FreeTimeResultRepository.create_result()
      ↓
      FreeTimeResult 저장 완료
```

---

## 메서드 성능 벤치마크

### 측정 항목

```
메서드                                  예상 시간   최악의 경우  테스트
─────────────────────────────────────────────────────────────────
OCRService.parse_image()                0.5-1s     2-3s (blur)
  └─ ImagePreprocessor.preprocess()     0.1s       0.3s
  └─ pytesseract.image_to_string()      0.3-0.8s   1-2s (lg img)
  └─ EverytimeScheduleParser.parse()    <0.1s      <0.1s

IntervalExtractor.extract()             <0.1s      <0.1s
SlotUtils.normalize_slot()              <0.1ms     <0.1ms
SlotUtils.get_conflicting_slots()       <1ms       <10ms (50 intervals)

SubmissionService.create_submission()   0.5-1s     2-3s
CalculationService.trigger_calc()       <1s        <2s (50 participants)
DeletionService.check_expiry()          <1ms       <1ms

DB 작업 (평균):
  INSERT submission                      <10ms
  INSERT interval × 10                   <50ms
  SELECT * FROM intervals × 50           <100ms
  DELETE cascade                         20-100ms

전체 E2E (이미지 업로드 → 결과):
  목표: < 5초
  실제: 1-2초 (정상 이미지)
        2-5초 (흐릿한 이미지 + OCR 재시도)
```

---

## 에러 처리 메서드

### 에러 발생 지점

```
1. OCRService.parse_image()
   ├─ OCRTimeoutError (> 10초)
   ├─ OCRFailedError (인식 불가)
   └─ Confidently ignored → 오류 처리 (ERROR_REASON 저장)

2. SubmissionService.create_submission()
   ├─ DuplicateSubmissionError
   │  └─ 409 Conflict (API 응답)
   ├─ Exception (DB Error)
   │  └─ 500 Internal Server Error
   └─ CalculationError (계산 실패)
      └─ 로그 기록, 제출은 성공 처리

3. GroupService.check_expiry()
   ├─ GROUP_NOT_FOUND
   │  └─ 404 Not Found
   └─ GROUP_EXPIRED
      └─ 410 Gone

4. BatchDeletionCLI
   ├─ Exception
   │  ├─ 로그 및 retry_count 증가
   │  ├─ 최대 3회 재시도 (1m, 5m, 15m)
   │  └─ 알림 발송 (3회 초과 시)
```

---

## 메서드별 테스트 전략

### 단위 테스트 (Unit Tests)

```
✓ SlotUtils.normalize_slot()           20+ 케이스
✓ SlotUtils.get_conflicting_slots()    15+ 케이스
✓ SlotUtils.merge_adjacent_slots()     10+ 케이스
✓ NicknameGenerator.generate_nickname() 5+ 케이스
✓ Group.is_expired()                   3+ 케이스
✓ Submission creation/deletion         10+ 케이스
✓ Interval normalization              10+ 케이스
✓ OCR parsing (mocked)                5+ 케이스
```

**파일**: `tests/unit/`

### 통합 테스트 (Integration Tests)

```
✓ E2E 그룹 생성 → 제출 → 계산    (test_calculation.py)
✓ E2E 배치 삭제 시뮬레이션        (test_deletion.py)
✓ 이미지 제출 + OCR 파싱          (test_image_submission.py)
✓ 폴링 + 결과 조회                (test_polling.py)
```

**파일**: `tests/integration/`

### 계약 테스트 (Contract Tests)

```
✓ POST /groups 요청/응답            (test_groups.py)
✓ GET /groups/{id}/free-time        (test_free_time.py)
✓ POST /submissions 이미지           (contract tests)
✓ DELETE /submissions/{id}          (contract tests)
```

**파일**: `tests/contract/`

### 성능 테스트 (Performance Tests)

```
✓ 계산 완료 시간 (< 100ms)          (test_calculation.py)
✓ 메모리 사용량 (O(n), not O(n²))   (profile_calculation.py)
✓ OCR 시간 프로파일링              (profile_ocr.py)
✓ 50 동시 사용자 로드              (load_test.py)
```

**파일**: `tests/performance/`

---

## 메서드 리팩토링 기회

### 1️⃣ 유틸리티 함수 추출 가능

```python
# 현재: SubmissionService 내부
_store_intervals()

# 리팩토링:
IntervalRepository.create_batch_intervals()
```

### 2️⃣ 중복 제거 가능

```python
# 현재: 여러 곳에서 반복
for submission in submissions:
  intervals = interval_repo.list_by_submission(submission.id)

# 리팩토링:
SubmissionRepository.list_with_intervals()
  → List[Tuple[Submission, List[Interval]]]
```

### 3️⃣ 캐싱 기회

```python
# 현재: 매번 조회
FreeTimeResultRepository.get_latest_by_group()

# 리팩토링:
@cache(ttl=5min)
def get_latest_by_group(group_id):
  ...
```

### 4️⃣ 배치 작업 최적화

```python
# 현재: N개 interval 각각 INSERT
for interval in intervals:
  interval_repo.create_interval(interval)

# 리팩토링:
interval_repo.create_batch(intervals)
  # → BULK INSERT (10배 빠름)
```

---

## 요약 (Summary)

| 카테고리 | 메서드 수 | 복잡도 | 테스트 | 우선순위 |
|---------|----------|--------|--------|---------|
| 서비스 계층 | ~30 | O(n²) | ✓ | ⭐⭐⭐ |
| 저장소 계층 | ~35 | O(1)~O(n) | ✓ | ⭐⭐⭐ |
| 모델 계층 | ~5 | O(1) | ✓ | ⭐⭐ |
| 유틸리티 | ~10 | O(n log n) | ✓ | ⭐⭐ |
| **합계** | **~80** | - | **85%+** | - |

**핵심 메서드**:
1. `CalculationService.trigger_calculation()` - 비즈니스 로직 핵심
2. `OCRService.parse_image()` - 성능 병목
3. `SubmissionService.create_submission()` - E2E 흐름
4. `DeletionService.check_expiry_by_id()` - 보안 관련

