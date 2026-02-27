# API 통합 맵 및 데이터 흐름

## 1️⃣ 공통 자유시간 계산 & 조회 플로우

### 프론트엔드 → API → DB → 렌더링 연결도

```
┌─────────────────────────────────────────────────────────────────┐
│                     📱 프론트엔드                                  │
│  (src/templates/index.html)                                     │
│                                                                 │
│  showResults(groupId)                                           │
│  └─> fetch('/groups/{groupId}/free-time')                     │
│      └─> renderCandidates(freeTimeData)                         │
└──────────────────────────────────────┬──────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────┐
│              🔌 API 엔드포인트 (FastAPI)                          │
│  (src/api/free_time.py)                                         │
│                                                                 │
│  GET /groups/{groupId}/free-time                                │
│  ├─ check_group_expiration()                                   │
│  ├─ Get FreeTimeResult from DB                                │
│  ├─ Get Submissions (participants)                             │
│  └─ Return FreeTimeResponse (JSON)                             │
└──────────────────────────────────────┬──────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                  🗄️ 데이터베이스 (PostgreSQL)                    │
│  (src/models/models.py)                                         │
│                                                                 │
│  ├─ FreeTimeResult (계산 결과)                                  │
│  │  ├─ free_time_intervals (≥10분)                             │
│  │  ├─ free_time_intervals_30min (≥30분)                       │
│  │  ├─ free_time_intervals_60min (≥60분)                       │
│  │  ├─ availability_by_day (JSONB 그리드)                      │
│  │  └─ computed_at (계산 시간)                                 │
│  │                                                              │
│  └─ Submission (참여자들의 일정)                                │
│     └─ Interval (각 참여자의 빈시간 슬롯)                        │
└──────────────────────────────────────────────────────────────────┘
```

---

## 2️⃣ 공통 자유시간 계산 로직

### 어디서 계산되는가?

| 계산 단계 | 담당 모듈 | 위치 |
|---------|---------|------|
| **1. 시간 겹침 분석** | `TimeOverlapAnalyzer` | `src/services/schedule_analyzer.py` |
| **2. 공통 빈시간 추출** | `FreeTimeFinder` | `src/services/calculation.py` |
| **3. 후보 시간 순위화** | `CandidateExtractor` | `src/services/candidates.py` |
| **4. 가용성 그리드 생성** | `AvailabilityGrid` | `src/services/availability_grid.py` |
| **5. 결과 저장** | `FreeTimeService` | `src/services/free_time.py` |

### 계산 트리거
```python
# API: POST /api/submissions
새로운 일정 제출 
  ↓
create_submission() 
  ↓
계산 서비스 실행 (여기서 공통 빈시간이 계산됨)
  ↓
FreeTimeResult 데이터베이스에 저장
```

---

## 3️⃣ 분석 API와 결과 API 비교

### 두 가지 API 엔드포인트

#### 1️⃣ **분석 API (설명용)** 
- **엔드포인트**: `GET /analysis/groups/{group_id}/overlaps`
- **목적**: 시간 겹침 분석 상세 정보 (JSON)
- **결과**: 
  ```json
  {
    "group_id": "uuid",
    "participant_count": 3,
    "participants": ["Alice", "Bob", "Carol"],
    "total_overlapping_slots": 45,
    "total_free_minutes": 180,
    "free_times_count": 3,
    "summary": "Alice, Bob, Carol 3명이 모두 가능한 시간..."
  }
  ```
- **사용처**: 콘솔에서 확인용, 내부 분석용

#### 2️⃣ **결과 조회 API (프론트 연결)** 
- **엔드포인트**: `GET /groups/{groupId}/free-time`
- **목적**: UI에 표시할 공통 빈시간 정보 (JSON)
- **결과**:
  ```json
  {
    "group_id": "uuid",
    "group_name": "스터디 모임",
    "participant_count": 3,
    "participants": [
      {"nickname": "Alice", "submitted_at": "2026-02-27T..."},
      {"nickname": "Bob", "submitted_at": "2026-02-27T..."}
    ],
    "free_time": [
      {
        "day": "MONDAY",
        "start_minute": 540,
        "end_minute": 600,
        "duration_minutes": 60,
        "overlap_count": 3
      }
    ]
  }
  ```
- **사용처**: **프론트엔드 메인 사용 엔드포인트** ✅

#### 3️⃣ **HTML 뷰 API (시각화)**
- **엔드포인트**: `GET /groups/{groupId}/view`
- **목적**: HTML 페이지로 직접 렌더링된 시각화
- **결과**: HTML 페이지 (weekly grid heatmap + candidate cards)
- **사용처**: 직접 브라우저에서 URL 접속시

---

## 4️⃣ 이미지로 표시하는 방식

### 현재 구현 (HTML 기반)

✅ **프론트엔드에서 렌더링**
```javascript
// src/templates/index.html (라인 1130)
renderCandidates(candidates) {
  return candidates.slice(0, 10).map((candidate, idx) => {
    return `
      <div class="candidate-card">
        <div class="candidate-rank">#${idx + 1}</div>
        <div class="candidate-title">${day}</div>
        <div class="candidate-time">${startTime} ~ ${endTime}</div>
        <div class="candidate-duration">${duration}분</div>
      </div>
    `;
  }).join('');
}
```

✅ **백엔드에서 HTML 렌더링**
```python
# src/api/free_time.py (라인 379)
@router.get("/{groupId}/view")
async def view_group_free_time_html(groupId: UUID):
    # render_free_time_template() 호출
    # → HTML weekly grid heatmap 생성
    # → Candidate cards 생성
```

```python
# src/templates/free_time.py
def render_free_time_template(response_data):
    # HTML div 기반 주간 그리드 생성
    # - 각 요일별 시간 슬롯
    # - 가용인원 기반 색상 강도 조정
    # - 클릭 가능한 카드 UI
```

### 🎨 시각화 구성 요소

| 요소 | 구현 방식 | 위치 |
|------|---------|------|
| **후보 카드** | HTML div + CSS | `index.html`, `free_time.py` |
| **주간 그리드** | HTML table/grid + CSS | `free_time.py` (grid-template-columns) |
| **색상 강도** | CSS opacity | `free_time.py` (intensity 계산) |
| **마우스 오버** | CSS transition | `free_time.py` |
| **반응형 디자인** | CSS media queries | `free_time.py` |

---

## 5️⃣ 이미지 생성 메소드 현황

### 현재 상황
❌ **PNG/이미지 파일로 생성하는 메소드 없음**
- matplotlib, plotly, PIL(ImageDraw) 미사용
- 모든 시각화는 **HTML + CSS로 구현**

### 저장된 데이터 구조

```
submissions (테이블)
├─ id (UUID)
├─ group_id (UUID)
├─ nickname (문자열)
├─ submitted_at (타임스탬프)
├─ status (SUCCESS/FAILED)
└─ error_reason (에러 메시지)

intervals (테이블)
├─ id (UUID)
├─ submission_id (외래키)
├─ day_of_week (0-6)
├─ start_minute (0-1439)
└─ end_minute (0-1439)

group_free_time_results (테이블)
├─ id (UUID)
├─ group_id (외래키)
├─ free_time_intervals (JSON - ≥10분)
├─ free_time_intervals_30min (JSON - ≥30분)
├─ free_time_intervals_60min (JSON - ≥60분)
├─ availability_by_day (JSONB - 그리드용)
├─ computed_at (타임스탬프)
└─ version (계산 버전)
```

---

## 6️⃣ 데이터 흐름 예시

### 일정 제출 시스퀀스

```
1. 사용자가 이미지 업로드 (프론트)
   ↓
2. POST /api/submissions
   - OCR로 텍스트 추출
   - 시간 간격 파싱
   - intervals 테이블에 저장
   ↓
3. 계산 서비스 실행 (자동 트리거)
   - TimeOverlapAnalyzer.analyze_group_overlaps()
   - FreeTimeFinder.calculate_free_time()
   - CandidateExtractor.extract_candidates()
   ↓
4. 결과 저장
   - FreeTimeResult 테이블에 계산 결과 저장
   ↓
5. 프론트에서 조회
   - GET /groups/{groupId}/free-time
   - renderCandidates()로 UI 렌더링
```

---

## 7️⃣ API 테스트 방법

```bash
# 1. 그룹 조회
curl http://localhost:8000/groups/{groupId}/free-time

# 2. 분석 조회
curl http://localhost:8000/analysis/groups/{groupId}/overlaps

# 3. HTML 뷰 직접 열기
curl http://localhost:8000/groups/{groupId}/view
```

---

## 결론

| 항목 | 상태 | 비고 |
|------|------|------|
| **공통 빈시간 계산** | ✅ 완료 | TimeOverlapAnalyzer 사용 |
| **API 연결** | ✅ 완료 | /groups/{id}/free-time |
| **프론트엔드 표시** | ✅ 완료 | HTML div + CSS |
| **DB 저장** | ✅ 완료 | FreeTimeResult 테이블 |
| **이미지 생성** | ❌ 없음 | HTML 렌더링만 사용 |
| **HTML 시각화** | ✅ 완료 | 주간 그리드 + 후보 카드 |

