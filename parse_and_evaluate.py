#!/usr/bin/env python3
"""
annotation1.txt를 JSON으로 변환하여 IMG_2777.json에 저장
그리고 직접 OCR 평가 실행
"""

import json
import os
from pathlib import Path
from PIL import Image
import pytesseract

# Paths
annotation_txt = "data/everytime_samples/annotations/annotation1.txt"
output_json = "data/everytime_samples/annotations/IMG_2777.json"
image_file = "IMG_2777.png"
image_path = f"data/everytime_samples/images/{image_file}"

# Step 1: annotation1.txt 읽기 및 JSON 변환
print(f"📖 Step 1: Reading {annotation_txt}...")
with open(annotation_txt, 'r', encoding='utf-8-sig') as f:
    content = f.read().strip()
    
    # 마크다운 ```plaintext ... ``` 블록 제거
    if content.startswith('```'):
        lines = content.split('\n')
        json_lines = [l for l in lines if l and not l.startswith('```')]
        content = '\n'.join(json_lines)
    
    # [{"day": "...", ...}] 형식으로 파싱
    try:
        schedule_data = json.loads(content)
    except json.JSONDecodeError as e:
        print(f"❌ JSON Parse Error: {e}")
        exit(1)

# schedule_data를 ocr_trainer 호환 형식으로 변환
annotation_json = {
    "image_file": image_file,
    "extracted_text": "",  # OCR 출력 (나중에 업데이트)
    "schedule": [
        {
            "day": entry.get("day", ""),
            "start": entry.get("start", ""),
            "end": entry.get("end", ""),
            "class_name": entry.get("title", "")
        }
        for entry in schedule_data
    ],
    "difficulty": "medium",
    "notes": "Manually annotated from HTML schedule"
}

# 저장
os.makedirs(os.path.dirname(output_json), exist_ok=True)
with open(output_json, 'w', encoding='utf-8') as f:
    json.dump(annotation_json, f, ensure_ascii=False, indent=2)

print(f"✅ Saved annotation to {output_json}")
print(f"\n📊 Ground Truth Schedule:")
print(f"   - Image: {image_file}")
print(f"   - Total Entries: {len(annotation_json['schedule'])}")
for entry in annotation_json['schedule']:
    print(f"   {entry['day']} {entry['start']}-{entry['end']}: {entry['class_name']}")

# Step 2: OCR 실행
print("\n" + "="*60)
print("🚀 Step 2: Running OCR on first image...")
print("="*60)

if not os.path.exists(image_path):
    print(f"❌ Image not found: {image_path}")
    exit(1)

try:
    with Image.open(image_path) as img:
        # Tesseract로 텍스트 추출
        ocr_text = pytesseract.image_to_string(img, lang="kor+eng")
        
        print(f"\n📝 OCR Extracted Text (first 500 chars):")
        print(f"---")
        print(ocr_text[:500] if len(ocr_text) > 500 else ocr_text)
        print(f"---")
        print(f"Total: {len(ocr_text)} characters\n")
        
        # extracted_text를 annotation에 추가
        annotation_json["extracted_text"] = ocr_text
        
        # 업데이트된 annotation 저장
        with open(output_json, 'w', encoding='utf-8') as f:
            json.dump(annotation_json, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Updated annotation with OCR text")
        
except Exception as e:
    print(f"❌ OCR Error: {e}")
    exit(1)

# Step 3: 간단한 평가
print("\n" + "="*60)
print("📈 Step 3: Evaluation Summary")
print("="*60)

# OCR에서 시간 패턴 찾기
import re
time_pattern = r'(\d{1,2}):(\d{2})'
times = re.findall(time_pattern, ocr_text)

print(f"\n📊 OCR Analysis:")
print(f"   - Found {len(times)} time patterns")
print(f"   - Expected {len(annotation_json['schedule'])} schedule entries")

# 한글 요일 찾기
days_korean = {'월': 0, '화': 0, '수': 0, '목': 0, '금': 0, '토': 0, '일': 0}
for day in days_korean:
    days_korean[day] = ocr_text.count(day)

days_found = {k: v for k, v in days_korean.items() if v > 0}
print(f"   - Korean days found: {days_found}")

expected_days = set(entry['day'] for entry in annotation_json['schedule'])
print(f"   - Expected days: {expected_days}")

print(f"\n✅ Annotation file ready: {output_json}")
print(f"   Use this to train/evaluate the OCR model")
