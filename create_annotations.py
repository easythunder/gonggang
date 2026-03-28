#!/usr/bin/env python3
"""Interactive annotation creator for OCR training dataset."""

import json
from pathlib import Path

def create_annotations():
    """Interactively create annotation files."""
    images_dir = Path("data/everytime_samples/images")
    annotations_dir = Path("data/everytime_samples/annotations")
    
    image_files = sorted(images_dir.glob("*.PNG"))
    
    print("="*70)
    print("📝 Everytime Schedule OCR Annotation Creator")
    print("="*70)
    print(f"\n✅ Found {len(image_files)} images\n")
    
    processed = 0
    
    for idx, img_path in enumerate(image_files[:5], 1):  # Start with first 5
        print(f"\n[{idx}/{len(image_files)}] {img_path.name}")
        print("-" * 70)
        
        # Create annotation filename
        ann_name = img_path.stem + ".json"
        ann_path = annotations_dir / ann_name
        
        if ann_path.exists():
            print(f"⏭️  Already exists: {ann_name}")
            continue
        
        print("\n📌 Enter schedule information (or 'skip' to skip):")
        
        schedule = []
        day_order = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"]
        
        for day_name in day_order:
            day_input = input(f"{day_name} (e.g., '09:00-11:00 수학' or 'none'): ").strip()
            
            if day_input.lower() in ['none', '', 'skip']:
                continue
            
            # Parse format: "09:00-11:00 수학"
            try:
                time_part, class_name = day_input.rsplit(' ', 1)
                start_time, end_time = time_part.split('-')
                
                schedule.append({
                    "day": day_name,
                    "start": start_time.strip(),
                    "end": end_time.strip(),
                    "class_name": class_name.strip()
                })
            except:
                print(f"  ❌ Invalid format. Use: HH:MM-HH:MM classname")
                continue
        
        # Difficulty level
        difficulty = input("Difficulty (easy/medium/hard) [medium]: ").strip().lower()
        if difficulty not in ['easy', 'medium', 'hard']:
            difficulty = 'medium'
        
        # Notes
        notes = input("Notes (optional): ").strip()
        
        # Create annotation
        annotation = {
            "image_file": img_path.name,
            "extracted_text": "\n".join([f"{s['day']} {s['start']}-{s['end']} {s['class_name']}" for s in schedule]),
            "schedule": schedule,
            "difficulty": difficulty,
            "notes": notes
        }
        
        # Save
        with open(ann_path, 'w', encoding='utf-8') as f:
            json.dump(annotation, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Saved: {ann_name}\n")
        processed += 1
    
    print("\n" + "="*70)
    print(f"📊 Summary: {processed} annotations created")
    print("="*70)

if __name__ == "__main__":
    try:
        create_annotations()
    except KeyboardInterrupt:
        print("\n\n⏹️  Cancelled by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
