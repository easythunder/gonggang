#!/usr/bin/env python3
"""
annotation1.txt를 JSON 형식으로 변환하여 IMG_2777.json에 저장
그리고 OCR trainer로 평가 수행
"""

import json
import os
from pathlib import Path

# Paths
annotation_txt = "data/everytime_samples/annotations/annotation1.txt"
output_json = "data/everytime_samples/annotations/IMG_2777.json"
image_file = "IMG_2777.png"

# annotation1.txt 읽기
print(f"📖 Reading {annotation_txt}...")
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
        print(f"Content: {content[:200]}")
        exit(1)

# schedule_data를 ocr_trainer 호환 형식으로 변환
annotation_json = {
    "image_file": image_file,
    "extracted_text": "",  # OCR 출력 (비워두고 나중에 테스트)
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
print(f"\n📊 Schedule Summary:")
print(f"   - Image: {image_file}")
print(f"   - Total Entries: {len(annotation_json['schedule'])}")
print(f"   - Days Covered: {set(e['day'] for e in annotation_json['schedule'])}")
print(f"\n📝 Class Schedule:")
for entry in annotation_json['schedule']:
    print(f"   {entry['day']} {entry['start']}-{entry['end']}: {entry['class_name']}")

# 이제 OCR trainer로 첫 번째 이미지 평가
print("\n" + "="*60)
print("🚀 Running OCR Evaluation on first image...")
print("="*60)

from src.tools.ocr_trainer import OCRTrainer
from pathlib import Path

trainer = OCRTrainer(data_dir=Path("data/everytime_samples"))

# IMG_2777.png 평가
image_path = trainer.images_dir / image_file
annotation_path = trainer.annotations_dir / "IMG_2777.json"
result = trainer.evaluate_single(image_path, annotation_path)

print(f"\n📈 Evaluation Results for {image_file}:")
print(f"   Text Similarity: {result['text_similarity']:.2%}")
print(f"   Schedule Accuracy: {result['schedule_accuracy']:.2%}")
print(f"   OCR Extracted: {len(result.get('ocr_schedule', []))} entries")
print(f"   Ground Truth: {len(result.get('gt_schedule', []))} entries")

if result.get('ocr_schedule'):
    print(f"\n   OCR Output:")
    for entry in result.get('ocr_schedule', []):
        print(f"      {entry['day']} {entry['start']}-{entry['end']}: {entry['class_name']}")
else:
    print(f"\n   ⚠️  OCR produced 0 schedule entries")

print(f"\n   Ground Truth:")
for entry in result.get('gt_schedule', []):
    print(f"      {entry['day']} {entry['start']}-{entry['end']}: {entry['class_name']}")
