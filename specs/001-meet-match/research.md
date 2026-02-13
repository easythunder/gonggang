# Research: Meet-Match Clarifications & Best Practices

**Feature**: Meet-Match (공통 빈시간 계산 및 공유)  
**Phase**: 0 (Research & Clarifications)  
**Date**: 2026-02-13  
**Status**: Final (10 user clarifications resolved)

---

## Executive Summary

모든 기술적 불확실성이 사용자 답변(10개)을 통해 해소되었습니다. 아래 섹션은 각 답변의 기술적 함의와 구현 방법을 정리합니다.

---

## 1. OCR 파싱 구현

**결정**: Tesseract 또는 PaddleOCR 사용

### 기술적 함의
- **처리**: 메모리 기반 (디스크 저장 금지)
- **입력**: 이미지 파일 (JPEG, PNG)
- **출력**: Busy intervals `{day_of_week: int(0-6), start_minute: int, end_minute: int}`
- **성능**: 5초 이내 (단일 이미지)

### 구현 선택지
- **Tesseract**: OCR만 지원, 시간표 구조 파싱은 별도 로직 필요
- **PaddleOCR**: 더 정확하나 무거움
- **추천**: Tesseract + 커스텀 시간표 파싱 로직 (휴리스틱 기반)

### 실패 처리
- OCR 실패 → 사용자에게 재업로드 옵션 제공
- 로그: 파싱 실패율 메트릭

---

## 2. 시간대 관리: 00:00~23:59 고정

**결정**: 사용자 시간대 설정 불가, 서버 UTC 기준

### 기술적 함의
- **장점**: 만료 시계 계산 단순화, DB 저장 명확
- **제약**: 다중 타임존 사용자 불가 (MVP)
- **비고**: 향후 타임존 지원은 별도 기능

### 구현
- 모든 timestamp: UTC 저장
- 클라이언트 시간대는 UI 렌더링만 (계산 X)
- 만료: `last_activity_at (UTC) + 72시간`

---

## 3. 공강 계산 시점: 제출 시 DB 저장

**결정**: 폴링 시 재계산 X, 제출 시점에 계산 & 저장

### 재계산 로직
- 신규 제출: `기존_결과 ∩ 신규_시간표_공강` (AND 연산)
- 기존 수정: 모든 submission 기반 전체 재계산
- 삭제: 해당 submission 제외, 전체 재계산

### 기술적 함의
- **저장 공간**: GroupFreeTimeResult 테이블 사용
- **폴링**: DB 조회만 (계산 X) → 응답 5초 이내
- **버전**: 재계산마다 version 증가 (change tracking)

### 구현 고려사항
- 계산 중 다중 제출: 큐 또는 락 메커니즘
- 부분 실패 (일부 계산 성공): 롤백 vs 부분 저장

---

## 4. 슬롯 단위: 5분 (내부), 사용자 10/20/30/60분

**결정**: 내부는 5분 고정, 사용자 조회 단위는 선택 가능

### 슬롯 설계
- **내부**: 00:00~23:59 = 288슬롯 (각 5분)
- **사용자**: 10, 20, 30, 60분 단위로 병합 후 표시
- **정규화**: 5분 기준 (ceiling/floor)

### 기술적 함의
- **저장**: Interval 테이블: `(submission_id, day, start_minute, end_minute)`
- **계산**: 2차원 배열 (7일 × 288슬롯) 사용 가능
- **표시**: 사용자 단위로 재정렬 (병합)

### 예제
```
내부 (5분): [111, 112, 113, 114, 115, 116, 117] (09:15~09:45)
사용자 30분: [09:15, 09:45] → 1개 구간
사용자 10분: [09:10, 09:20, 09:30, 09:40] → 3개 구간 (경계 일관성)
```

---

## 5. 최대 참여자: 50명

**결정**: 하드 제한 50명

### 성능 분석
- 7일 × 288슬롯 × 50명 = 100,800 데이터 포인트
- AND 연산 (OR 아님): O(n) 선형
- 계산 시간: ~100ms 예상 (DB 쿼리 + 메모리 계산)

### 제약
- 초과 시 HTTP 400 Bad Request 거부
- 향후 확장 시 재아키텍처 필요

---

## 6. 응답 시간: 5초 이내 (파싱 포함)

**결정**: 이미지 파싱 + DB 저장 + 계산까지 전체 5초

### 성능 목표 분해
- OCR 파싱: 3초
- DB 저장 & 쿼리: 500ms
- 계산 & 병합: 500ms
- 버퍼: 1초

### 구현 전략
- 동기 처리 (비동기는 복잡도 증가)
- DB 인덱싱: (group_id, day, start_minute) 필수
- 계산은 메모리 기반

---

## 7. 그룹명: 사용자 입력 또는 시스템 랜덤

**결정**: 선택사항, 미입력 시 랜덤 생성

### 랜덤 생성 형식
- `{adjective}_{adjective}_{noun}` (닉네임과 동일)
- 예: "joyful_bright_mountain"
- 단어 풀: 각 300개 이상 (중복 확률 <0.01%)

### 구현
- 서드파티: faker.js, random-words 등
- 또는 직접 단어 풀 관리

---

## 8. 닉네임: 자동 부여 (단어 3개)

**결정**: 사용자 입력 불가, 시스템이 자동 생성

### 형식
- `{adjective}_{adjective}_{noun}`
- 예: "happy_blue_lion", "swift_silver_dawn"

### 중복 처리
- 같은 그룹 내 중복 확인
- 중복 시: 재생성
- 최대 재시도: 10회 (99.99% 충분)

### 기술적 이점
- PII 미포함 (개인식별 불가)
- 사용자 친화적 (읽기 쉬움)
- 멘탈 모델 단순

---

## 9. 만료 및 삭제: Lazy + Batch + 예외처리

**결정**: Lazy (요청 시 확인only) + Batch (5~15분) + Exception Handling

### Lazy Deletion
- 폴링/초대 링크 접근 시 `expires_at` 확인
- 만료 → HTTP 410 반환
- 실제 삭제는 배치에서 수행

### Batch Deletion
```
매 5~15분마다:
  1. SELECT * FROM groups WHERE expires_at <= NOW()
  2. 각 group마다 transaction:
     - INSERT INTO deletion_log
     - DELETE FROM intervals (FK)
     - DELETE FROM submissions (FK)
     - DELETE FROM group_free_time_result
     - DELETE FROM groups
  3. 예외:
     - 오류 로깅 (group_id, error_code)
     - 재시도: 1분, 5분, 15분 (지수 백오프)
     - 최대 3회, 초과 시 알림
```

### 고민 포인트
- 삭제 중 동시 폴링: Lazy가 이미 HTTP 410 반환했으므로 문제 없음
- 부분 삭제: 트랜잭션으로 원자성 보장
- 배치 장시간 실패: 알림 + 수동 개입

---

## 10. 폴링 간격: 서버 강제 2-3초 (클라이언트 무시)

**결정**: 모든 클라이언트 간격 요청 무시, 서버에서 강제 적용

### 구현
```
GET /groups/{groupId}/free-time?interval=100ms
→ 서버가 무시, 강제 2초 (또는 3초) 간격 적용
```

### 기술적 이점
- 서버 부하 제어 (DOS 방지)
- 일관된 사용자 경험
- 네트워크 대역폭 최적화

### 고려사항
- 2초 vs 3초 선택: 3초 권장 (더 안정적)
- 클라이언트 라이브러리: 무시할 수 없도록 명시

---

## 결론 & 다음 단계

**모든 10개 질문 해소됨 → Phase 1 설계 진행 가능**

다음:
1. Data Model 설계 (고정)
2. API Contracts (OpenAPI)
3. Quickstart & Implementation Checklist
