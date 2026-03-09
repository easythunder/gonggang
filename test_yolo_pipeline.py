#!/usr/bin/env python3
"""Test YOLO-based image processing pipeline."""

import sys
import requests
import json
from pathlib import Path
from typing import Optional

BASE_URL = "http://localhost:8000/api"
GROUPS_URL = "http://localhost:8000/groups"


def create_group(group_name: str = None, display_unit: int = 30) -> Optional[dict]:
    """Create test group."""
    print(f"\n🔧 Creating group...")
    payload = {
        "group_name": group_name or "YOLO 테스트 그룹",
        "display_unit_minutes": display_unit,
    }
    
    response = requests.post(f"{GROUPS_URL}", json=payload)
    
    if response.status_code != 201:
        print(f"❌ Failed to create group")
        print(f"   Status: {response.status_code}")
        print(f"   Error: {response.text}")
        return None
    
    data = response.json()
    print(f"✅ Group created!")
    print(f"   Group ID: {data['group_id']}")
    print(f"   Group Name: {data['group_name']}")
    
    return data


def submit_image_with_yolo(group_id: str, nickname: str, image_path: str) -> Optional[dict]:
    """Submit image using YOLO pipeline."""
    print(f"\n📸 Submitting image with YOLO pipeline...")
    print(f"   Nickname: {nickname}")
    print(f"   Image: {image_path}")
    
    image_path = Path(image_path)
    if not image_path.exists():
        print(f"❌ Image file not found: {image_path}")
        return None
    
    with open(image_path, 'rb') as f:
        files = {'image': f}
        data = {
            'group_id': group_id,
            'nickname': nickname,
        }
        
        response = requests.post(
            f"{BASE_URL}/submissions/image-yolo",
            files=files,
            data=data,
            timeout=60  # YOLO detection can take time
        )
    
    print(f"\nStatus: {response.status_code}")
    
    if response.status_code not in [200, 201]:
        print(f"❌ Submission failed")
        print(f"   Response: {response.text}")
        return None
    
    result = response.json()
    print(f"✅ Submission successful!")
    print(f"   Submission ID: {result.get('submission_id')}")
    print(f"   Interval Count: {result.get('interval_count')}")
    print(f"   Cell Detections: {result.get('metadata', {}).get('cell_detections', 'N/A')}")
    
    # Display extracted schedule
    if result.get('extracted_schedule'):
        print(f"\n📅 Extracted Schedule ({len(result['extracted_schedule'])} entries):")
        for entry in result['extracted_schedule']:
            print(f"   {entry.get('day', '?')} {entry.get('start', '??:??')}-{entry.get('end', '??:??')}: {entry.get('class_name', '?')}")
    
    # Display metadata
    if result.get('metadata'):
        print(f"\n📊 Pipeline Metadata:")
        metadata = result['metadata']
        print(f"   Image Size: {metadata.get('image_size', '?')}")
        print(f"   Crop Size: {metadata.get('crop_size', '?')}")
        print(f"   Cell Grid: {metadata.get('cell_grid', '?')}")
        print(f"   Detection Confidence: {metadata.get('detection_bbox', {}).get('confidence', '?'):.2f}")
        print(f"   OCR Text Length: {metadata.get('ocr_text_length', 0)}")
    
    return result


def main():
    """Main test flow."""
    print("=" * 70)
    print("🎓 YOLO-기반 시간표 이미지 처리 파이프라인 테스트")
    print("=" * 70)
    
    # Step 1: Create group
    group = create_group(group_name="YOLO 파이프라인 테스트")
    if not group:
        print("❌ Failed to create group")
        return
    
    group_id = group['group_id']
    
    # Step 2: Find test image
    test_image_paths = [
        Path("data/everytime_samples/images/IMG_2777.PNG"),
        Path("data/everytime_samples/images/IMG_2778.PNG"),
        Path("tests/fixtures/timetable_sample.png"),
        Path("sample_timetable.png"),
    ]
    
    test_image = None
    for path in test_image_paths:
        if path.exists():
            test_image = path
            print(f"\n📂 Found test image: {path}")
            break
    
    if not test_image:
        print("\n⚠️  No test image found")
        print("\nUsage: python test_yolo_pipeline.py <image_path>")
        print("\nExample:")
        print("  python test_yolo_pipeline.py data/everytime_samples/images/IMG_2777.PNG")
        return
    
    # Step 3: Submit image
    result = submit_image_with_yolo(
        group_id=group_id,
        nickname="YOLO 테스트 사용자",
        image_path=str(test_image)
    )
    
    if not result:
        print("\n❌ Image submission failed")
        return
    
    print("\n" + "=" * 70)
    print("✨ Test completed successfully!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Use provided image path
        print("=" * 70)
        print("🎓 YOLO-기반 시간표 이미지 처리 파이프라인 테스트")
        print("=" * 70)
        
        group = create_group(group_name="YOLO 파이프라인 테스트")
        if not group:
            sys.exit(1)
        
        result = submit_image_with_yolo(
            group_id=group['group_id'],
            nickname="YOLO 테스트 사용자",
            image_path=sys.argv[1]
        )
        
        if not result:
            sys.exit(1)
        
        print("\n" + "=" * 70)
        print("✨ Test completed successfully!")
        print("=" * 70 + "\n")
    else:
        main()
