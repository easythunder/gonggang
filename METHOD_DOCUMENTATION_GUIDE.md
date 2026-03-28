# 메서드 정리 통합 가이드

> **최종 작성**: 2026-02-25  
> **버전**: 1.0  
> **상태**: 완성 ✅

---

## 📚 생성된 문서 목록

이 프로젝트의 메서드를 정리하기 위해 다음 3개의 문서를 작성했습니다:

### 1. **METHODS_DOCUMENTATION.md** - 메서드 완전 참조 📖
   - **내용**: 모든 메서드의 목록, 파라미터, 반환값, 설명
   - **대상**: 특정 메서드 정보를 빨리 찾아야 할 때
   - **구조**:
     - 서비스 계층 (7개 주요 클래스)
     - 저장소 계층 (6개 저장소)
     - 모델 계층 (5개 모델)
     - 유틸리티/라이브러리
     - API 엔드포인트
     - 메서드 호출 체인 (3가지 시나리오)

### 2. **METHOD_CALL_FLOW.md** - 데이터 흐름 및 상세 플로우 🔄
   - **내용**: 메서드 간 상세한 호출 순서, 타이밍, 데이터 변환
   - **대상**: 전체 흐름을 이해하거나 디버깅할 때
   - **구조**:
     - E2E 플로우 (3단계: 생성 → 제출 → 조회)
     - 배치 삭제 흐름
     - 클래스 간 의존성 그래프
     - 타임라인 기반 데이터 흐름
     - 메서드 호출 매트릭스
     - 에러 처리 경로

### 3. **METHOD_ANALYSIS.md** - 메서드 복잡도 및 성능 분석 📊
   - **내용**: 복잡도, 성능, 테스트, 리팩토링 기회
   - **대상**: 성능 최적화나 코드 개선이 필요할 때
   - **구조**:
     - 복잡도 분류 (O(1), O(n), O(n²))
     - 기능별 분류 (CRUD, 알고리즘, 검증)
     - 호출 빈도 분석
     - 성능 벤치마크
     - 에러 처리 전략
     - 테스트 전략
     - 리팩토링 기회

---

## 🎯 메서드 찾기 가이드

### 상황별 올바른 문서 선택

#### 🔍 "특정 메서드의 역할이 뭐야?"
→ **METHODS_DOCUMENTATION.md** 참고
```
예: CalculationService.trigger_calculation() 찾기
→ "2. CalculationService" 섹션
→ 메서드 역할, 파라미터, 반환값 모두 기록됨
```

#### 🔄 "이미지 업로드부터 결과 반환까지 어떻게 진행되는데?"
→ **METHOD_CALL_FLOW.md** 참고
```
예: E2E 플로우 이해
→ "단계 1: POST /groups"
→ "단계 2: POST /groups/{id}/submissions"
→ "단계 3: GET /groups/{id}/free-time"
→ 각 단계의 상세 호출 순서 확인
```

#### ⚡ "이 메서드가 얼마나 빠른데? 병목은 뭐야?"
→ **METHOD_ANALYSIS.md** 참고
```
예: 성능 벤치마크
→ "메서드 성능 벤치마크" 섹션
→ 메서드별 예상 시간, 최악의 경우, 테스트 여부 확인
```

#### 🐛 "이 메서드에서 에러가 나면 어떻게 되는데?"
→ **METHOD_CALL_FLOW.md** 또는 **METHOD_ANALYSIS.md**
```
예: 에러 처리
→ METHOD_CALL_FLOW.md → "에러 처리 경로" 섹션
→ 또는 METHOD_ANALYSIS.md → "에러 처리 메서드" 섹션
```

#### 📈 "이 메서드는 얼마나 자주 불려?"
→ **METHOD_ANALYSIS.md**
```
예: 호출 빈도
→ "메서드 호출 빈도 분석" 섹션
→ 고빈도/저빈도 메서드 구분
```

#### 🧪 "이 메서드는 어디서 테스트되는데?"
→ **METHOD_ANALYSIS.md**
```
예: 테스트 위치
→ "메서드별 테스트 전략" 섹션
→ 단위/통합/계약/성능 그룹별로 정리
```

---

## 📊 메서드 분류 색인

### 🟦 가장 중요한 5대 핵심 메서드

```
1. CalculationService.trigger_calculation()
   └─ 위치: METHODS_DOCUMENTATION.md → "1. CalculationService"
   └─ 역할: Complement 연산으로 빈 시간 계산 (적어도 한 명은 자유로운 시간)
   └─ 복잡도: O(n×m) - METHOD_ANALYSIS.md 참고
   └─ 성능: < 1초 - METHOD_ANALYSIS.md 참고
   └─ 호출: 제출 생성 시 - METHOD_CALL_FLOW.md 참고

2. SubmissionService.create_submission()
   └─ 위치: METHODS_DOCUMENTATION.md → "3. SubmissionService"
   └─ 역할: 사용자 제출 + OCR 파싱 + 계산 트리거
   └─ E2E: METHOD_CALL_FLOW.md → "단계 2" 참고
   
3. OCRService.parse_image()
   └─ 위치: METHODS_DOCUMENTATION.md → "4. OCRService"
   └─ 역할: 이미지 → OCR 파싱 → 시간 추출
   └─ 병목: 0.5-1초 - 성능 최적화 필요
   
4. DeletionService.check_expiry_by_id()
   └─ 위치: METHODS_DOCUMENTATION.md → "5. DeletionService"
   └─ 역할: 만료 검사 (Lazy deletion)
   └─ 빈도: 모든 폴링 요청마다
   
5. CalculationService._calculate_and_intersection()
   └─ 위치: METHOD_ANALYSIS.md → "비즈니스 로직 메서드"
   └─ 역할: 시간 여집합 계산 알고리즘 (빈 시간 찾기)
   └─ 복잡도: O(n×m)
```

---

### 🟩 카테고리별 메서드 빠른 찾기

#### 🔐 보안/검증 메서드
```
METHODS_DOCUMENTATION.md:
  - GroupService.check_expiry()
  - DeletionService.check_expiry()
  - DeletionService.is_soft_deleted()
METHOD_ANALYSIS.md:
  - 검증 메서드 섹션
```

#### 🗄️ 데이터 저장/삭제
```
METHODS_DOCUMENTATION.md:
  - GroupRepository.create_group()
  - SubmissionRepository.create_submission()
  - IntervalRepository.create_interval()
  - ...delete_by_group() 메서드들
METHOD_CALL_FLOW.md:
  - "배치 삭제 흐름" 섹션
```

#### 🧮 계산/알고리즘
```
METHODS_DOCUMENTATION.md:
  - CalculationService.trigger_calculation()
  - SlotUtils.normalize_slot()
  - SlotUtils.get_conflicting_slots()
METHOD_ANALYSIS.md:
  - "비즈니스 로직 메서드" 섹션
  - "메서드 성능 벤치마크" 섹션
```

#### 🖼️ 이미지 처리/OCR
```
METHODS_DOCUMENTATION.md:
  - OCRService.parse_image()
  - EverytimeScheduleParser.parse()
METHOD_CALL_FLOW.md:
  - "단계 2: Step 1: OCR 파싱" 상세 플로우
METHOD_ANALYSIS.md:
  - "메서드 성능 벤치마크" - OCR 부분
```

#### 📡 API/HTTP
```
METHODS_DOCUMENTATION.md:
  - "API 엔드포인트" 섹션
METHOD_CALL_FLOW.md:
  - "E2E 플로우" 전체 (API 호출 기준)
```

---

## 🔥 빠른 참조 테이블

### 메서드별 정보 위치 매핑

| 메서드 | 기본 정보 | 호출 흐름 | 성능/복잡도 | 테스트 위치 |
|--------|---------|---------|-----------|-----------|
| `create_group()` | ✅ METH Doc | 🔄 Flow | 📊 Analysis | unit/int |
| `trigger_calculation()` | ✅ METH Doc | 🔄 Flow | 📊 Analysis | int/perf |
| `create_submission()` | ✅ METH Doc | 🔄 Flow | 📊 Analysis | int/unit |
| `parse_image()` | ✅ METH Doc | 🔄 Flow | 📊 Analysis | unit/perf |
| `check_expiry_by_id()` | ✅ METH Doc | 🔄 Flow | 📊 Analysis | unit |
| `delete_by_group()` | ✅ METH Doc | 🔄 Flow | 📊 Analysis | int |
| `normalize_slot()` | ✅ METH Doc | - | 📊 Analysis | unit |
| `get_conflicting_slots()` | ✅ METH Doc | - | 📊 Analysis | unit |

---

## 📖 읽기 순서 추천

### 🟢 초급자 (프로젝트 처음 접하는 사람)
```
1단계: METHODS_DOCUMENTATION.md
  └─ 전체 서비스 계층 개요 파악
  └─ 각 클래스의 역할 이해 (~20분)

2단계: METHOD_CALL_FLOW.md
  └─ "E2E 플로우" 음독
  └─ 실제 메서드 호출 순서 따라가기 (~30분)

3단계: METHOD_ANALYSIS.md
  └─ "메서드 복잡도 분류" 섹션
  └─ 핵심 알고리즘 이해 (~20분)

✅ 총 70분 → 프로젝트 구조 완전 이해
```

### 🟡 중급자 (일부 기능 수정)
```
1단계: METHODS_DOCUMENTATION.md
  └─ 수정 대상 메서드만 찾기

2단계: METHOD_CALL_FLOW.md
  └─ 해당 메서드의 호출 체인 확인

3단계: METHOD_ANALYSIS.md
  └─ 성능/테스트 영향 범위 확인

✅ 총 20-30분 → 수정 계획 수립
```

### 🔴 고급자 (성능 최적화/리팩토링)
```
1단계: METHOD_ANALYSIS.md
  └─ "메서드 복잡도 분류" 또는 "성능 벤치마크"

2단계: METHOD_CALL_FLOW.md
  └─ 병목 지점의 호출 흐름 검토

3단계: METHODS_DOCUMENTATION.md
  └─ 세부 파라미터 및 반환값 확인

✅ 총 15-20분 → 최적화 전략 수립
```

---

## 🔗 문서 간 교차 참조

### METHODS_DOCUMENTATION.md → 다른 문서 링크
```
GroupService.create_group()
  ├─ See: METHOD_CALL_FLOW.md#단계-1-post-groups
  └─ Performance: METHOD_ANALYSIS.md#메서드-성능-벤치마크

CalculationService.trigger_calculation()
  ├─ See: METHOD_CALL_FLOW.md#단계-2-step-4-자동-계산-트리거
  └─ See: METHOD_ANALYSIS.md#핵심-알고리즘
```

### METHOD_CALL_FLOW.md → 다른 문서 링크
```
"단계 2: Step 1: OCR 파싱"
  ├─ Method Details: METHODS_DOCUMENTATION.md#4-ocrservice
  └─ Performance: METHOD_ANALYSIS.md#메서드-성능-벤치마크

"배치 삭제 흐름"
  ├─ Implementation: METHODS_DOCUMENTATION.md#5-deletionservice
  └─ Error Handling: METHOD_ANALYSIS.md#에러-처리-메서드
```

### METHOD_ANALYSIS.md → 다른 문서 링크
```
"낮은 복잡도 (O(1))"
  └─ Details: METHODS_DOCUMENTATION.md (각 클래스별)

"메서드 호출 빈도 분석"
  └─ Call Chain: METHOD_CALL_FLOW.md
```

---

## 💡 실제 사용 예시

### 사례 1: "새로운 필드를 Group에 추가하려면?"

```
1단계: METHODS_DOCUMENTATION.md → Group 모델 섹션
  └─ 현재 필드 확인

2단계: METHOD_ANALYSIS.md → CRUD 메서드
  └─ GroupRepository.create_group() 영향 범위 확인

3단계: METHOD_CALL_FLOW.md → "단계 1"
  └─ 그룹 생성 시 데이터 흐름 확인

4단계: 필요한 메서드 수정
  ├─ Group 모델 필드 추가
  ├─ GroupRepository.create_group() 파라미터 추가
  ├─ GroupService.create_group() 로직 추가
  └─ API 엔드포인트 업데이트
```

### 사례 2: "OCR이 너무 느린데 어떻게 최적화할까?"

```
1단계: METHOD_ANALYSIS.md → "메서드 성능 벤치마크"
  └─ OCRService.parse_image() 성능 확인
  └─ 병목이 Tesseract OCR (0.3-0.8초)인 것 확인

2단계: METHOD_CALL_FLOW.md → "단계 2: Step 1"
  └─ OCR 호출 흐름 이해

3단계: METHODS_DOCUMENTATION.md → "4. OCRService"
  └─ 관련 메서드 확인
  ├─ preprocess_image() 최적화
  └─ 캐싱 기회 검토

4단계: 최적화 전략
  ├─ 이미지 해상도 감소
  ├─ 또는 캐싱 추가
  └─ 또는 비동기 처리로 변경
```

### 사례 3: "배치 삭제가 실패했는데 왜 실패했을까?"

```
1단계: METHOD_CALL_FLOW.md → "배치 삭제 흐름"
  └─ Cascade 삭제 순서 확인

2단계: METHOD_ANALYSIS.md → "에러 처리 메서드"
  └─ 가능한 에러 지점 확인

3단계: METHODS_DOCUMENTATION.md
  └─ 각 Repository의 delete_by_group() 확인
  ├─ 외래키 제약 조건 확인
  └─ 트랜잭션 처리 확인

4단계: 디버깅
  ├─ 로그 확인: deletion_logs 테이블
  ├─ 재시도: retry_count 확인
  └─ Database 제약 조건 학인
```

---

## 📝 문서 유지보수

### 메서드 추가/수정 시 업데이트 체크리스트

```
☐ 새로운 메서드 추가:
  ☐ METHODS_DOCUMENTATION.md에서 클래스별 테이블에 행 추가
  ☐ 메서드명, 파라미터, 반환값, 설명 입력
  
☐ 메서드 수정 (시그니처 변경)
  ☐ METHODS_DOCUMENTATION.md 업데이트
  ☐ METHOD_CALL_FLOW.md에서 호출 흐름 검토
  ☐ METHOD_ANALYSIS.md에서 복잡도 업데이트

☐ 성능 개선
  ☐ METHOD_ANALYSIS.md → "메서드 성능 벤치마크" 업데이트
  ☐ 복잡도 변경 시 "메서드 복잡도 분류" 업데이트
  
☐ 테스트 추가
  ☐ METHOD_ANALYSIS.md → "메서드별 테스트 전략" 업데이트
  ☐ 테스트 파일 위치 기록
```

---

## 🎓 학습 로드맵

### 주간 학습 계획 예시

```
Week 1: 기초 이해
  ┌─ Day 1: METHODS_DOCUMENTATION.md 정독 (서비스 계층)
  ├─ Day 2: METHODS_DOCUMENTATION.md 정독 (저장소 + 모델)
  ├─ Day 3: METHOD_CALL_FLOW.md → E2E 플로우 이해
  ├─ Day 4: METHOD_CALL_FLOW.md → 배치 삭제 흐름
  └─ Day 5: METHOD_ANALYSIS.md → 기본 개념

Week 2: 심화 이해
  ┌─ Day 1: METHOD_ANALYSIS.md → 복잡도 분석
  ├─ Day 2: METHOD_ANALYSIS.md → 성능 벤치마크
  ├─ Day 3: 테스트 코드 읽기 (tests/ 디렉토리)
  ├─ Day 4: 실제 코드 디버깅 (IDE에서)
  └─ Day 5: 이전 학습 복습 + Q&A

Week 3: 실전
  ┌─ Day 1-2: 첫 번째 기능 구현
  ├─ Day 3-4: 성능 최적화
  └─ Day 5: 코드 리뷰 및 개선
```

---

## ✅ 최종 체크리스트

이 문서 세트가 충분한가?

```
✅ 메서드별 정보 (파라미터, 반환값, 설명)
✅ 메서드 간 호출 관계 (호출 순서, 데이터 흐름)
✅ 메서드 성능 분석 (복잡도, 벤치마크)
✅ 에러 처리 전략 (발생 지점, 대응)
✅ 테스트 커버리지 (테스트 파일 위치)
✅ 사용 예시 (실제 사례)
✅ 학습 경로 (초급→중급→고급)
✅ 유지보수 가이드 (업데이트 체크리스트)
```

---

## 📞 추가 질문이 있나요?

### 문서별 주요 답변 섹션

| 질문 | 답변 위치 |
|------|---------|
| "메서드 목록이 뭐야?" | METHODS_DOCUMENTATION.md |
| "__를 호출하는데 왜 이렇게 오래 걸려?" | METHOD_ANALYSIS.md (성능 벤치마크) |
| "이 메서드는 어디서 테스트돼?" | METHOD_ANALYSIS.md (테스트 전략) |
| "이 메서드 호출 흐름 보여줘" | METHOD_CALL_FLOW.md (E2E 플로우) |
| "어떤 메서드가 가장 복잡한데?" | METHOD_ANALYSIS.md (복잡도 분류) |
| "API 응답 구조 뭐야?" | METHODS_DOCUMENTATION.md (API 섹션) |
| "에러가 나면 어떻게 처리돼?" | METHOD_CALL_FLOW.md (에러 처리 경로) |
| "성능 최적화 어디서부터 시작해?" | METHOD_ANALYSIS.md (병목 지점) |

---

**문서 작성 완료**: 2026-02-25  
**총 3개 파일, ~80개 메서드 정리**  
**협업 준비 완료** ✅

