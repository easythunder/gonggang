# Everytime Schedule Dataset for OCR Learning

실제 에브리타임 시간표 이미지를 기반으로 OCR 정확도를 개선하는 데이터셋입니다.

## 디렉토리 구조

```
everytime_samples/
├── README.md (이 파일)
├── images/              # 원본 에브리타임 시간표 이미지
│   ├── image_001.jpg
│   ├── image_002.jpg
│   └── ...
├── annotations/         # 정답 레이블 (JSON)
│   ├── image_001.json
│   ├── image_002.json
│   └── ...
└── results/            # OCR 처리 결과 및 성과
    ├── ocr_output.json
    ├── accuracy_report.json
    └── improvements.log
```

## 정답 레이블 포맷 (annotations/*.json)

```json
{
  "image_file": "image_001.jpg",
  "extracted_text": "Monday 9:00 - 11:00...",
  "schedule": [
    {
      "day": "MONDAY",
      "start": "09:00",
      "end": "11:00",
      "class_name": "수학개론"
    },
    {
      "day": "TUESDAY",
      "start": "14:00",
      "end": "16:00",
      "class_name": "영어회화"
    }
  ],
  "notes": "선명한 이미지, 배경 깔끔",
  "difficulty": "easy"
}
```

## 사용 방법

### 1. 이미지 추가
`images/` 폴더에 에브리타임 시간표 이미지를 업로드합니다.

### 2. 정답 레이블 작성
각 이미지에 대해 `annotations/` 폴더에 JSON 파일을 생성합니다.

### 3. OCR 테스트 실행
```bash
python -m src.tools.ocr_trainer evaluate
```

### 4. 성과 확인
```bash
python -m src.tools.ocr_trainer report
```

## 난이도 구분

- **easy**: 선명한 이미지, 단순한 레이아웃
- **medium**: 약간의 손상, 겹쳐진 텍스트
- **hard**: 저해상도, 회전, 기울어짐

## 기여 가이드

1. 실제 에브리타임 캡처본만 사용
2. 개인정보는 모두 가리기 (학생명, 학번 등)
3. 높은 해상도 선호 (800x600 이상)
4. 다양한 스타일/难도의 이미지 수집
