# Feature Specification: Meet‑Match (공통 빈시간 계산 및 공유)

**Feature Branch**: `meet-match`  
**Created**: 2026-02-13  
**Status**: Final (v0.3 - All 10 User Clarifications + Planning Phase)  
**Input**: 
- 친구 그룹이 이미지를 통해 시간표를 제출 (로그인 없음, 그룹 링크 기반)
- 시스템이 OCR로 이미지 파싱하고 메모리 처리 (디스크 저장 금지)
- 제출 시점에 공통 빈 시간 계산 & DB 저장
- 클라이언트는 2-3초 폴링으로 최신 결과 조회
- 72시간 후 자동 만료

참고: 
- 에이전트 가이드: [.github/agents/speckit.specify.agent.md](.github/agents/speckit.specify.agent.md)
- 스펙 템플릿: [.specify/templates/spec-template.md](.specify/templates/spec-template.md)
- 프로젝트 헌법(프라이버시·보관 규칙 참조): [.specify/memory/constitution.md](.specify/memory/constitution.md)

---

## 요약 (What / Why)

**목적**: 소규모 그룹(최대 50명)이 로그인 없이 공통 빈 시간을 빠르게 찾고 약속을 잡도록 지원.

**핵심 동작**: 
1. 그룹 생성(그룹명 선택 또는 랜덤) → 고유 그룹 링크 발행
2. 참여자 이미지 업로드 → 시스템 OCR 파싱(메모리만, 이미지 폐기) → 랜덤 닉네임(단어 3개) 자동 부여
3. 각 제출 시점에 **공통 빈 시간 계산 & DB 저장** (재계산 로직: 신규 제출 시 기존 결과 AND 신규 시간표 / 삭제 시 전체 재계산)
4. 클라이언트 폴링(서버 강제 2-3초): 최신 계산 결과 조회 (JSON)
5. **자동 만료**: 마지막 활동 + 72시간 후 배치 작업으로 삭제 (요청 시 Lazy 확인)

---

## 핵심 사용자 역할

- **그룹 생성자**: 그룹명 지정(선택) 또는 시스템이 랜덤 생성 → 고유 그룹 링크 발행. 초대 링크 권한 없음(모두 동일).
- **참여자 (Member)**: 초대 링크 접속 → 이미지 업로드 → 시스템이 자동으로 OCR 파싱 & 랜덤 닉네임 부여(단어 3개)
- **뷰어 (Viewer)**: 결과 공유 링크로 최신 계산 결과 조회(폴링 기반).

---

## 사용자 흐름 (E2E)

1. **그룹 생성**
   - 사용자가 "새 그룹 생성" 페이지 접속 → 다음을 설정:
     - 그룹명: 사용자 입력(선택) 또는 시스템 랜덤 생성
     - 결과 조회 단위: 사용자가 선택 (10분, 20분, 30분, 1시간 중 하나, 기본: 30분)
     - 활동 시간대: 00:00~23:59 고정 (사용자 설정 불가)
   - 시스템이 고유 그룹 생성 → 초대 링크 & 결과 공유 링크 발행

2. **참여자 이미지 제출** (참여자 × N, 최대 50명)
   - 참여자가 초대 링크 접속 → 이미지 업로드
   - 시스템이 **메모리만 사용해서 OCR 파싱** (이미지 디스크 저장 금지)
   - 파싱된 intervals(`day_of_week`, `start_minute`, `end_minute`) 추출
   - **자동으로 랜덤 닉네임 부여** (단어 3개 조합, 예: "happy_blue_lion")
   - Submission 및 Interval 데이터 DB 저장
   - **공통 빈 시간 자동 재계산** (기본 로직: 기존 결과 AND 신규 시간표)
     - 신규 제출 시: `기존_공강 ∩ 신규_시간표의_공강`
     - 기존 결과 갱신 & DB 저장
   - 응답: 5초 이내에 `{success, nickname}`

3. **시간표 제외** (선택사항)
   - 특정 submission 삭제 요청
   - 시스템이 **전체 그룹 시간표에서 해당 항목 제거**
   - **전체 재계산** (모든 남은 시간표로 공강 계산)
   - 결과 DB 갱신

4. **결과 폴링** (뷰어)
   - 클라이언트가 `GET /groups/{groupId}/free-time` 호출
   - 서버가 **강제로 2-3초 폴링 간격 적용** (클라이언트 요청 간격 무시)
   - 응답: 
     ```json
     {
       "group_id": "...",
       "participant_count": 3,
       "free_time": [
         {"day": "MONDAY", "start": "14:00", "end": "15:30", "duration_minutes": 90}
       ],
       "computed_at": "2026-02-13T10:30:00Z",
       "expires_at": "2026-02-16T10:30:00Z"
     }
     ```

5. **자동 만료 및 삭제**
   - Lazy Deletion: 폴링/접근 요청 시 `expires_at` 확인 → 만료면 **HTTP 410 Gone** 반환
   - 배치 작업: 5~15분 마다 만료된 그룹 스캔 → Cascade 삭제 (Group, Submission, Interval, FreeTimeResult)
   - 배치 실패 시 예외 처리 (재시도 로직, 로그 기록)

---

## 기능적 요구사항

### 그룹 생성 및 관리

- **FR-001 (MUST)**: 그룹 생성 시 사용자가 다음을 입력하거나 선택해야 한다:
  - `group_name`: 사용자 입력 (선택사항), 미입력 시 시스템이 랜덤 생성 (예: "joyful_bright_morning")
  - `display_unit_minutes`: 결과 표시 단위 선택 (10, 20, 30, 60분 중 선택, 기본: 30분)
  - (활동 시간대는 00:00~23:59 고정, 사용자 선택 불가)
  
- **FR-002 (MUST)**: 그룹 생성 후 고유의 초대 링크(`invite_url`)와 공유 링크(`share_url`)를 발행한다.
  - 초대 링크: 이미지 업로드 전용
  - 공유 링크: 결과 조회 전용 (폴링)

- **FR-003 (MUST)**: 그룹 정보는 최소한 다음을 포함해야 한다:
  - `group_id`, `group_name`, `created_at`, `last_activity_at`, `expires_at`, `invite_url`, `share_url`, `max_participants` (50)
  - `display_unit_minutes`

### 참여자 제출 및 닉네임 자동 부여

- **FR-004 (MUST)**: 참여자는 이미지만 업로드할 수 있다 (닉네임 입력 불가).
  - 사용자가 이미지 파일 선택/업로드
  - 시스템이 OCR로 파싱 및 자동 닉네임 부여

- **FR-005 (MUST)**: 자동 닉네임은 **랜덤 단어 3개의 조합**으로 생성한다:
  - 형식: `{adjective}_{adjective}_{noun}`
  - 예: "happy_blue_forest", "swift_silver_mountain"
  - 같은 그룹 내 중복 없이 

- **FR-006 (MUST)**: 각 제출마다 다음을 DB에 저장한다:
  - `submission_id`, `group_id`, `nickname`, `created_at`, `status` (success|failed)

- **FR-007 (MUST)**: 제출할 때마다 `group.last_activity_at`을 갱신한다. (만료 시계 리셋)

### 이미지 파싱 및 정규화

- **FR-008 (MUST)**: 이미지 수신 시 다음 프로세스를 실행한다 (**5초 이내 응답 목표포함**):
  1. 이미지를 **메모리만 사용해서 처리** (디스크 저장 금지)
  2. **OCR 엔진 사용** (예: Tesseract, PaddleOCR)으로 바쁜 시간(busy intervals) 추출
  3. 추출한 intervals를 **5분 슬롯 기준으로 정규화**
     - 정규화 규칙: 보수적 방식 (시작은 ceiling, 종료는 floor)
     - 예: 9:15~9:45 → 정규화 후 없음 (9:10, 9:15 경계선)
  4. 정규화된 intervals를 `Interval` 테이블에 저장 (하나의 submission마다 여러 interval)
  5. 이미지 파일은 메모리에서만 사용 후 **즉시 폐기** (디스크 저장 안 함)

- **FR-009 (MUST)**: 파싱 실패 시:
  - 응답: `{success: false, reason: "ocr_failed"}` (5초 이내)
  - 참여자는 이미지 재업로드 가능
  - 재시도 횟수 제한 없음

- **FR-010 (SHOULD)**: 파싱 실패는 로그에 기록, 운영자 모니터링 가능. (메트릭: 파싱 실패율)

### 공통 공강 계산 엔진

- **FR-011 (MUST)**: 시스템은 참여자의 제출 또는 수정이 발생할 때마다 공통 공강을 **자동으로 재계산**한다.

- **FR-012 (MUST)**: 계산 대상은 **제출 완료한 참여자만** 포함한다. (미제출자는 제외)

- **FR-013 (MUST)**: 계산에 사용하는 다음 파라미터는 **그룹 생성 시 설정된 값**을 사용한다:
  - `slot_minutes` (슬롯 단위)
  - `min_duration_minutes` (최소 모임 시간)
  - `activity_window` (활동 시간대)

- **FR-014 (MUST)**: 바쁜 시간(busy intervals) 정규화는 **보수적(conservative)** 방식으로 수행:
  - 시작 시각: 슬롯 경계로 **올림(ceiling)** → 해당 슬롯 포함 X
  - 종료 시각: 슬롯 경계로 **내림(floor)** → 해당 슬롯 포함 X
  - 예: `9:15~9:45` 바쁨, 30분 슬롯 → 정규화 후 없음 (9:30 슬롯 미포함)

- **FR-015 (MUST)**: 계산 출력은 다음 두 가지를 모두 포함해야 한다:
  1. **전체 그리드** (`availability_grid`): 슬롯별로 `{ slot_id, time_window, availability_count, is_common }` 인코딩
  2. **후보 리스트** (`candidates`): 연속 공강 구간을 병합한 구간 목록

- **FR-016 (MUST)**: 후보 구간은 **연속 가능한 슬롯을 병합**하여 생성하고, `min_duration_minutes` 이상인 구간만 반환한다.

- **FR-017 (MUST)**: 후보 정렬 기준은 사용자가 선택 가능해야 한다. 제공되는 기준:
  - `duration_desc`: 길이 내림차순 (기본값)
  - `start_time_asc`: 시작 시각 오름차순
  - `overlap_count_desc`: 겹침 인원 내림차순
  - `preference`: 사용자 지정 선호(TODO)

- **FR-018 (MUST)**: 정렬된 후보 중 Top N (기본 5개)를 제공한다.

- **FR-019 (MUST)**: 가능한 공강 시간이 없을 경우:
  - "가능한 시간이 없습니다" 메시지 표시
  - 대안 제시: 
    - "최소 모임 시간을 줄여보세요"
    - "슬롯 단위를 늘려보세요"
    - "활동 시간대를 조정해보세요"

- **FR-020 (MUST)**: 계산 API는 다음을 반환해야 한다:
  - `status`: `pending|computing|completed|failed`
  - `version`: 계산 결과 버전 (재계산 시 증가)
  - `computed_at`: 마지막 계산 시각
  - `result`: 그리드 + 후보 리스트 (status=completed일 때만)
  - `error_code`: 실패 원인 코드 (status=failed일 때만)

### 결과 페이지 시각화 및 인터랙션

- **FR-021 (MUST)**: 결과 페이지는 다음 두 가지를 함께 제공해야 한다:
  1. **후보 카드 목록** (Top N): 요일, 시작/종료 시각, 길이, 겹침 인원수 표시
  2. **주간 그리드**: 슬롯 단위 시각화

- **FR-022 (MUST)**: 주간 그리드는 슬롯별 **공통 공강 가능 인원 수(겹침 정도)** 를 시각화한다 (heatmap).
  - 색상 범위: 0명 (불가능) ~ N명(모든 제출자, 가능), 그래디언트로 표현

- **FR-023 (MUST)**: 결과 페이지는 제출을 완료한 모든 참여자의 **닉네임을 표시**해야 한다.

- **FR-024 (SHOULD)**: 닉네임 중복 시 UI에서 구분 표기를 제공한다 (예: "민수#1", "민수#2").

- **FR-025 (MUST)**: 후보 카드를 클릭하면:
  - 주간 그리드에서 해당 시간대로 **자동 스크롤**
  - 해당 구간을 **강조 표시** (색상/테두리)

- **FR-026 (SHOULD)**: 강조 표시는 토글 가능해야 한다 (클릭 시 해제/재강조).

- **FR-027 (MUST)**: 모바일 환경:
  - 주간 그리드는 **세로 스크롤**(vertical scroll)로 탐색 가능해야 한다
  - 요일 헤더는 스크롤 중에도 고정(sticky)되거나 주기적으로 표시되어야 한다

- **FR-028 (MUST)**: 사용자는 결과 페이지에서 후보 **정렬 기준을 변경**할 수 있으며, 선택 즉시 후보 리스트와 그리드가 갱신되어야 한다.

### 만료 및 자동 삭제

- **FR-029 (MUST)**: 그룹의 보관 만료 시점은 **마지막 제출/수정 시각(`last_activity_at`) + 72시간**으로 계산한다.

- **FR-030 (MUST)**: 만료 시 다음을 **모두 삭제**한다:
  - 원본 이미지 파일(s3/storage path)
  - 파싱 산출물(JSON/intervals)
  - 계산 결과(공유 페이지 데이터)
  - 그룹, 멤버, 제출 메타데이터

- **FR-031 (SHOULD)**: 결과 공유 페이지는 **만료 임박 배너**(남은 시간)를 표시한다. (예: "이 페이지는 12시간 후 삭제됩니다")

- **FR-032 (MUST)**: 만료된 링크로 접근 시:
  - 만료 안내 페이지 표시
  - "새 그룹 만들기" CTA 제공

- **FR-033 (MUST)**: 삭제는 두 가지 방식으로 수행된다:
  1. **주기적 배치 작업**: 5~15분 간격으로 실행, 만료된 그룹을 스캔하여 삭제
  2. **Lazy deletion**: 만료된 링크 접근 시 즉시 만료 체크 후 필요 시 삭제

- **FR-034 (SHOULD)**: 삭제 로그를 남긴다 (PII 제외, 감사 추적용):
  - `group_id`, `deleted_at`, `reason` (`expired`|`manual`), `submission_count`, `asset_count`

### 이미지 저장 정책 (보안과의 일치)

- **FR-035 (MUST)**: MVP에서 원본 이미지는 임시 저장(최대 72시간)되고 자동 삭제된다.

- **FR-036 (SHOULD)**: 파싱 후 "무저장" 모드 지원(TODO: 구현 우선순위)이 가능해야 한다.
  - 이 경우 파생 가용성 그리드만 저장

- **FR-037 (MUST)**: 모든 저장 파일은 TLS 전송 후 **플랫폼 기본 암호화** 적용.

---

## 비포함 (Out of Scope for MVP)

- 자동 크롤링/스크래핑을 통한 에브리타임 파싱
- 캘린더 연동(구글 캘린더 등) 및 자동 예약 확정
- 고급 권한/조직 단위 접근 제어
- 투표/설문/선호도 기반 일정 확정
- 사용자 계정 및 히스토리 관리
- 알림/리마인더 기능 (추후 P1 → PR-08)

---

## 성공 기준 (Measurable Outcomes)

- **SC-001**: 그룹 생성부터 초대 링크 발행까지 **1분 이내** 완료
- **SC-002**: 이미지 업로드 → 파싱 및 그리드 생성까지 **평균 10초 이내** (단일 100KB 이미지 기준)
- **SC-003**: 모든 제출 완료 후 최종 계산 결과 반환까지 **5초 이내**
- **SC-004**: 결과 페이지 렌더링(후보 카드 + 주간 그리드) **2초 이내**
- **SC-005**: 30분 슬롯 기준 공통 공강 계산 정확도 **100%** (단위 테스트 커버리지)
- **SC-006**: 모든 업로드/결과 항목이 72시간 후 **자동 삭제 확인 가능** (삭제 로그)
- **SC-007**: 모바일 환경에서 주간 그리드 **세로 스크롤 부드러움** (60fps 이상)
- **SC-008**: 2명 이상 참여자의 뷰어 동시 접속 시 **응답 시간 증가 없음** (stateless 설계)

---

## 기술적 제약 및 비기능 요구사항

### 보안 & 프라이버시

- **보관 및 삭제**: [.specify/memory/constitution.md](.specify/memory/constitution.md) 준수
  - 기본 72시간 보관, 마지막 활동 기준 자동 삭제
  - 이미지/링크는 임시 저장만, 원본 최대 72시간 후 삭제

- **전송**: TLS (HTTPS) 필수

- **저장**: 플랫폼 기본 암호화 + 민감 데이터(토큰/URL)는 마스킹/암호화

- **접근 제어**:
  - 그룹장: Bearer 토큰 (admin_token in URL)
  - 참여자: 닉네임 기반 (로그인 불필요)
  - 뷰어: 공개 링크 (읽기 전용)

- **로그/모니터링**: 민감 정보(이미지 URL, 링크 텍스트) 마스킹 필수

### 성능

- 단일 그룹 최대 참여자: TODO (기본 50명 추정)
- 슬롯 계산: 선형 시간 복잡도 권장
- 캐싱: 계산 결과는 최종 버전까지 캐싱 가능 (stateless)

### 장애 복구

- 이미지 처리 중 오류 → 참여자에게 수동 입력 옵션 제공
- 계산 타임아웃 → 재시도 또는 "계산 실패" 안내

---

## 품질 기준 (테스트 / 문서 / 리뷰 최소셋)

- **단위 테스트**: 
  - 파싱 로직(경계/중첩 슬롯)
  - 정규화 규칙(보수적 올림/내림)
  - 공통 공강 계산(교집합, 병합, 최소 기간 필터링)
  - 정렬 기준별 순서 검증

- **통합 테스트**:
  - 이미지 업로드 → 파싱 → 재계산 → 결과 조회 (E2E 경로 1개 이상)
  - 만료/삭제 경로 (72시간 배치 시뮬레이션)

- **문서**:
  - README: 로컬 실행 및 테스트 가이드
  - API 스펙(OpenAPI): 계산 엔진 입출력, 이미지 파싱 포맷
  - 시간대/슬롯 정규화 규칙 명시

- **코드 리뷰**:
  - 모든 PR: CI(린트 + 테스트) 통과 필수
  - 보안/프라이버시 변경: 추가 리뷰(보안 담당자)
  - 계산 로직 변경: 코드 리뷰 + 테스트 케이스 검증

---

## User Scenarios & Testing (Acceptance Criteria)

### Scenario 1: 기본 흐름 (모두 완료 후 계산)

**Given**: 그룹장이 새로운 그룹을 생성했다 (30분 슬롯, 최소 60분 모임).  
**When**: 3명의 참여자가 모두 시간표 이미지를 업로드했다.  
**Then**: 
- 그룹장은 "모든 제출 완료" 상태를 보고 "계산" 버튼을 클릭한다.
- 5초 이내 결과 페이지가 생성되고, 후보 카드(Top 5)와 주간 그리드가 표시된다.
- 주간 그리드는 각 슬롯의 겹침 인원수(0~3명)를 색상으로 표현한다.

**Acceptance**: 후보 구간들이 30분 단위로 올바르게 계산되고 정렬된다.

---

### Scenario 2: 이미지 파싱 실패 후 수동 입력

**Given**: 한 참여자가 저화질 이미지를 업로드했다.  
**When**: 시스템이 파싱을 시도했지만 실패했다.  
**Then**:
- 해당 참여자에게 "이미지 인식 실패, 수동으로 입력해주세요" 메시지 표시.
- 참여자는 수동 시간 입력 UI에서 바쁜 시간을 직접 입력할 수 있다.
- 수동 입력 완료 후 시스템은 자동 재계산을 수행한다.

**Acceptance**: 수동 입력값도 정규화되어 계산 결과에 반영된다.

---

### Scenario 3: 정렬 기준 변경

**Given**: 사용자가 결과 페이지를 열었다.  
**When**: 후보 정렬 기준을 "시작 시각 오름차순"으로 변경한다.  
**Then**: 
- 후보 카드 목록이 즉시 재정렬된다.
- 주간 그리드의 강조 표시도 새로운 정렬 순서를 반영한다.

**Acceptance**: 정렬 변경 후 UI 갱신이 즉각적이고 정확하다.

---

### Scenario 4: 만료된 그룹 접근

**Given**: 그룹 생성 이후 72시간이 경과했다.  
**When**: 사용자가 만료된 그룹의 초대 링크로 접속한다.  
**Then**:
- "이 그룹은 만료되어 더 이상 사용할 수 없습니다" 메시지 표시.
- "새 그룹 만들기" CTA 제공.
- 해당 그룹의 모든 데이터(이미지, 메타데이터, 결과)는 삭제됨.

**Acceptance**: 만료 안내 페이지가 명확하고 새 그룹 생성 경로가 제공된다.

---

## Key Entities & Data Model

```
Group {
  group_id: uuid,
  created_at: timestamp,
  last_activity_at: timestamp,
  expires_at: last_activity_at + 72h,
  admin_token: string,
  invite_url: string,
  share_url: string,
  
  settings: {
    slot_minutes: int (min 15),
    min_duration_minutes: int,
    activity_window: { start: time, end: time }
  }
}

Submission {
  submission_id: uuid,
  group_id: uuid,
  nickname: string,
  type: enum(image | link | manual),
  payload_ref: string (file path or link text),
  parsed_grid: json (normalized availability intervals),
  submitted_at: timestamp,
  status: enum(pending | completed | failed)
}

ComputeResult {
  result_id: uuid,
  group_id: uuid,
  version: int (incremented on recompute),
  availability_grid: json,
  candidates: json (list of free time intervals),
  computed_at: timestamp,
  status: enum(pending | completed | failed),
  error_code?: string
}
```

---

## TODO / 결정 필요 항목

- TOD01: 시간대 정책(기본 KST 고정 vs 클라이언트 제공) 결정
- TODO02: 정렬 기준 확장(사용자 선호도 기반 정렬) 우선순위
- TODO03: 닉네임 충돌 UI 세부 설계(#N 표기 vs full display name)
- TODO04: 참여자 상한(MVP 50명 or 다른 수치) 확정
- TODO05: 이미지 파싱 엔진 선택(OCR/ML 모델, 오픈소스 vs 상용)
- TODO06: "무저장" 모드 구현 우선순위(파싱 후 즉시 삭제)
- TODO07: 모바일 그리드 UI 상세 설계(가로/세로 방향, sticky header)
- TODO08: 만료 배너 표시 시점(24시간 전 vs 1시간 전) 결정

---

## Implementation Notes

- **라이브러리 우선(Library-First)**: 계산 & 파싱 로직을 독립 모듈로 분리하여 재사용성 확보 및 테스트 용이성 강화
- **CLI 인터페이스**: 파싱/계산 로직은 내부 CLI 도구로도 테스트 가능하도록 설계
- **Stateless 설계**: 결과 페이지는 그룹/제출/계산 데이터를 조회하여 실시간 렌더링(캐시 가능)
- **MVP 우선**: 이미지 업로드 기반 파싱이 핵심, 에브리타임 크롤링은 추후 단계

---

**변경 이력**: Draft v0.1 (초안) — 2026-02-11, Chapter 1/2/3 통합 완료
