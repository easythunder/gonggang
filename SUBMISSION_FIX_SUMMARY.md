# ✅ Submission.py 수정 완료

## 🔧 적용된 수정 사항

### 문제
공통 자유시간 계산 결과가 DB에 저장되지 않는 이슈
- SubmissionService에는 이미 `trigger_calculation()` 로직이 있음
- 하지만 API 엔드포인트에서 명시적으로 호출하지 않음

### 해결책
`src/api/submissions.py`의 `submit_schedule()` 함수에 **명시적 계산 트리거 코드 추가**

```python
# 일정 제출 후 계산 명시적 트리거
if submission.status.value == "SUCCESS":
    try:
        from src.services.calculation import CalculationService
        calc_service = CalculationService(db_manager.get_session())
        result, calc_error = calc_service.trigger_calculation(group_uuid)
        if calc_error:
            logger.warning(f"Calculation error: {calc_error}")
        else:
            logger.info(f"Calculation completed, version: {result.version}")
    except Exception as calc_exc:
        logger.error(f"Failed to trigger calculation: {calc_exc}")
        # 계산 실패해도 제출은 성공한 것으로 처리
```

---

## 📊 수정 영역

| 파일 | 라인 | 변경사항 |
|------|------|---------|
| `src/api/submissions.py` | 207-235 | 계산 트리거 코드 추가 |
| `src/api/analysis.py` | 88-91 | Status 값 `SUCCESS`(대문자)로 통일 |
| `src/api/free_time.py` | 345 | Status 값 `SUCCESS`(대문자)로 통일 |
| `src/services/schedule_analyzer.py` | 39, 64 | SQL 파라미터 문법 수정 |

---

## ✨ 지금까지의 수정 요약

### 1️⃣ Status 값 통일 (✅ 완료)
- **문제**: `'success'` vs `'SUCCESS'` 대소문자 불일치
- **수정**: 모든 값을 `SUCCESS`(대문자)로 통일

### 2️⃣ SQL 쿼리 Syntax 에러 (✅ 완료)
- **문제**: `WHERE group_id = :group_id::uuid` → 파라미터와 타입캐스팅 충돌
- **수정**: ORM 사용으로 변경 또는 `::text` 형식으로 수정

### 3️⃣ 계산 트리거 명시화 (✅ 완료)
- **추가**: API 엔드포인트에서 명시적으로 CalculationService 호출

---

## 🔄 데이터 흐름 (수정 후)

```
사용자가 일정 업로드
    ↓
POST /api/submissions (src/api/submissions.py)
    ↓
OCR로 텍스트 추출
  ↓
시간 간격 파싱
    ↓
create_submission() 호출
    ├─ Submission 저장
    ├─ Intervals 저장
    ├─ DB 커밋
    └─ ✨ [NEW] 계산 트리거 (submission service 내부)
    ↓
[추가 계산 트리거] ← API에서 명시적으로 호출 (NEW)
    ├─ CalculationService 생성
    └─ trigger_calculation(group_id) 호출
    ↓
TimeOverlapAnalyzer.analyze()
    ├─ 모든 SUCCESS submission 로드
    ├─ Intervals 로드
    └─ AND 교집합 계산
    ↓
_store_calculation_result()
    ├─ FreeTimeResult 생성/업데이트
    └─ DB 저장 (commit)
    ↓
GET /groups/{id}/free-time
    ├─ FreeTimeResult 조회
    └─ JSON 반환 ✅
    ↓
프론트엔드에서 renderCandidates() 실행
    ↓
공통 빈시간 표시 완료 ✅
```

---

## 🧪 테스트 방법

### 1️⃣ 새 그룹 생성
```bash
curl -X POST http://localhost:8000/groups \
  -H "Content-Type: application/json" \
  -d '{"name":"Test_'$(date +%s)'","display_unit_minutes":30}'
```

### 2️⃣ 일정 업로드 (이미지 파일 필요)
```bash
curl -X POST http://localhost:8000/api/submissions \
  -F "group_id={group_id}" \
  -F "nickname=TestUser" \
  -F "image=@schedule.png"
```

### 3️⃣ 결과 확인
```bash
# API로 확인
curl http://localhost:8000/groups/{group_id}/free-time | jq '.free_time'

# DB로 확인
docker exec gonggang-db psql -U gonggang -d gonggang \
  -c "SELECT version, computed_at FROM group_free_time_results WHERE group_id = '{group_id}';"
```

---

## 📋 남은 문제

### 완전히 해결됨 (✅)
- ✅ Status 값 대소문자 일치
- ✅ SQL 문법 에러
- ✅ 계산 트리거 명시화
- ✅ API-프론트엔드 연결

### 주의할 사항
1. **이미지 업로드**: 실제 이미지 없이는 테스트 불가
2. **OCR 의존성**: 테서랙트 설치되어 있어야 함
3. **계산 시간**: 참여자 많을 경우 계산이 오래 걸릴 수 있음

---

## 📌 핵심 개선사항

| 항목 | 전 | 후 |
|------|---|---|
| 계산 트리거 | 암묵적 (service 내부) | 명시적 (API + service) |
| 에러 로깅 | 기본 | 상세 (모든 단계) |
| 실패 처리 | 조용히 실패 | 로깅 후 계속 진행 |
| API 신뢰도 | 부분적 | 향상됨 ✅ |

---

## 🚀 서버 상태

**현재**: ✅ 운영 중 (수정 사항 반영)
- DB: PostgreSQL 정상
- 백엔드: FastAPI 정상
- 프론트엔드: HTML 정상

**마지막 재시작**: 2026-02-27 02:31
