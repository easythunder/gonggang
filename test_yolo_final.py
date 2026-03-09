#!/usr/bin/env python3
import requests
import json
from pathlib import Path
import sys

BASE_URL = "http://localhost:8000"

def main():
    print("=" * 70)
    print("YOLO Pipeline Test Started")
    print("=" * 70)

    # Step 1: Create Group
    print("\n[1/4] Creating test group...")
    try:
        group_resp = requests.post(
            f"{BASE_URL}/groups",
            json={"group_name": "YOLO Test", "display_unit_minutes": 30},
            timeout=10
        )
        if group_resp.status_code != 201:
            print(f"ERROR: Failed to create group (status {group_resp.status_code})")
            print(group_resp.text)
            return False
        group_id = group_resp.json()['group_id']
        print(f"OK - Group created: {group_id}")
    except Exception as e:
        print(f"ERROR: {e}")
        return False

    # Step 2: Find test image
    print("\n[2/4] Finding test image...")
    test_image = Path("data/everytime_samples/images/IMG_2777.PNG")
    if not test_image.exists():
        print(f"ERROR: Test image not found at {test_image}")
        return False
    size_kb = test_image.stat().st_size / 1024
    print(f"OK - Image found: {test_image} ({size_kb:.1f} KB)")

    # Step 3: Submit to YOLO pipeline
    print("\n[3/4] Submitting image to YOLO pipeline...")
    print(f"     Endpoint: POST /api/submissions/image-yolo")
    try:
        with open(test_image, 'rb') as f:
            files = {'image': f}
            data = {'group_id': str(group_id), 'nickname': 'YOLO Tester'}
            submission_resp = requests.post(
                f"{BASE_URL}/api/submissions/image-yolo",
                files=files,
                data=data,
                timeout=120
            )
        
        print(f"OK - Response status: {submission_resp.status_code}")
        
        if submission_resp.status_code not in [200, 201]:
            print(f"ERROR: Submission failed")
            print(submission_resp.text)
            return False
        
        result = submission_resp.json()
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Step 4: Display results
    print("\n[4/4] Processing Results:")
    print("-" * 70)

    print(f"\nBasic Info:")
    print(f"  Status: {result.get('status', 'N/A')}")
    print(f"  Submission ID: {result.get('submission_id', 'N/A')}")
    print(f"  Interval Count: {result.get('interval_count', 0)}")

    schedule = result.get('extracted_schedule', [])
    if schedule:
        print(f"\nExtracted Schedule ({len(schedule)} entries):")
        for entry in schedule:
            day = entry.get('day', '?')
            start = entry.get('start', '??:??')
            end = entry.get('end', '??:??')
            cls = entry.get('class_name', '?')
            print(f"  [{day}] {start} ~ {end} : {cls}")
    else:
        print("\nNo schedule extracted")

    metadata = result.get('metadata', {})
    if metadata:
        print(f"\nPipeline Metadata:")
        print(f"  Image Size: {metadata.get('image_size', 'N/A')}")
        print(f"  Crop Size: {metadata.get('crop_size', 'N/A')}")
        print(f"  Cell Grid: {metadata.get('cell_grid', 'N/A')}")
        print(f"  Cell Detections: {metadata.get('cell_detections', 'N/A')}")
        print(f"  OCR Text Length: {metadata.get('ocr_text_length', 'N/A')}")
        bbox = metadata.get('detection_bbox', {})
        if bbox and 'confidence' in bbox:
            print(f"  YOLO Confidence: {bbox['confidence']:.3f}")

    print("\n" + "=" * 70)
    print("Test Complete - SUCCESS")
    print("=" * 70)
    return True

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
