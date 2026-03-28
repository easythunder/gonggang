#!/usr/bin/env python3
"""Auto-generate dummy annotations for OCR training."""

import json
from pathlib import Path

def generate_dummy_annotations():
    """Generate sample annotations for all images."""
    images_dir = Path("data/everytime_samples/images")
    annotations_dir = Path("data/everytime_samples/annotations")
    
    image_files = sorted(images_dir.glob("*.PNG"))
    
    print(f"🔄 Generating dummy annotations for {len(image_files)} images...")
    
    # Sample schedules (rotate through different combinations)
    sample_schedules = [
        [
            {"day": "MONDAY", "start": "09:00", "end": "11:00", "class_name": "수학"},
            {"day": "WEDNESDAY", "start": "14:00", "end": "16:00", "class_name": "영어"},
        ],
        [
            {"day": "TUESDAY", "start": "10:00", "end": "12:00", "class_name": "과학"},
            {"day": "THURSDAY", "start": "15:00", "end": "17:00", "class_name": "한국사"},
        ],
        [
            {"day": "MONDAY", "start": "13:00", "end": "15:00", "class_name": "물리"},
            {"day": "FRIDAY", "start": "09:00", "end": "11:00", "class_name": "화학"},
        ],
        [
            {"day": "WEDNESDAY", "start": "11:00", "end": "13:00", "class_name": "생물"},
            {"day": "MONDAY", "start": "15:00", "end": "17:00", "class_name": "음악"},
        ],
    ]
    
    difficulties = ["easy", "medium", "hard"]
    
    created = 0
    for idx, img_path in enumerate(image_files):
        ann_name = img_path.stem + ".json"
        ann_path = annotations_dir / ann_name
        
        if ann_path.exists():
            print(f"⏭️  {ann_name} - already exists")
            continue
        
        # Rotate through sample schedules
        schedule = sample_schedules[idx % len(sample_schedules)]
        difficulty = difficulties[idx % len(difficulties)]
        
        annotation = {
            "image_file": img_path.name,
            "extracted_text": "\n".join([f"{s['day']} {s['start']}-{s['end']} {s['class_name']}" for s in schedule]),
            "schedule": schedule,
            "difficulty": difficulty,
            "notes": f"Auto-generated sample #{idx+1}"
        }
        
        with open(ann_path, 'w', encoding='utf-8') as f:
            json.dump(annotation, f, indent=2, ensure_ascii=False)
        
        created += 1
        if created % 10 == 0:
            print(f"  ✓ {created}/{len(image_files)} created...")
    
    print(f"\n✅ Generated {created} annotation files")
    print(f"\n📌 Next steps:")
    print(f"1. Review and edit annotations in: data/everytime_samples/annotations/")
    print(f"2. Update with actual schedule data from images")
    print(f"3. Run: python -m src.tools.ocr_trainer evaluate")

if __name__ == "__main__":
    generate_dummy_annotations()
