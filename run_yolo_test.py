#!/usr/bin/env python3
import requests
import json
import sys
import time
from pathlib import Path

BASE = "http://localhost:8000"

print("=" * 70)
print("YOLO PIPELINE TEST")
print("=" * 70)

# Group
print("\n[1] Creating test group...")
group_name = f"YOLO_{int(time.time())}"
resp = requests.post(f"{BASE}/groups", json={
    "group_name": group_name,
    "display_unit_minutes": 30
})
gid = resp.json()['data']['group_id']
print(f"OK - Group ID: {gid}")

# Image
print("\n[2] Checking test image...")
img = Path("data/everytime_samples/images/IMG_2777.PNG")
if not img.exists():
    print(f"ERROR: Image not found at {img}")
    sys.exit(1)
size_kb = img.stat().st_size / 1024
print(f"OK - Found {img} ({size_kb:.0f} KB)")

# Submit to YOLO pipeline
print("\n[3] Submitting to YOLO pipeline endpoint...")
print(f"    POST /api/submissions/image-yolo")
try:
    with open(img, 'rb') as f:
        files = {'image': f}
        data = {'group_id': gid, 'nickname': 'YOLO'}
        resp = requests.post(f"{BASE}/api/submissions/image-yolo", 
                             files=files, data=data, timeout=120)
    
    print(f"OK - Response code: {resp.status_code}")
    
    if resp.status_code not in [200, 201]:
        print(f"ERROR: Submission failed")
        print(resp.text)
        sys.exit(1)
    
    result = resp.json()
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Display results
print("\n[4] Results:")
print(f"    Status: {result.get('status')}")
print(f"    Intervals: {result.get('interval_count')}")

schedule = result.get('extracted_schedule', [])
if schedule:
    print(f"\n[5] Extracted Schedule ({len(schedule)} entries):")
    for e in schedule:
        day = e.get('day', '?')
        start = e.get('start', '??:??')
        end = e.get('end', '??:??')
        cls = e.get('class_name', '?')
        print(f"    [{day}] {start} ~ {end} : {cls}")
else:
    print("[5] No schedule extracted")

meta = result.get('metadata', {})
if meta:
    print(f"\n[6] Metadata:")
    print(f"    Image size: {meta.get('image_size')}")
    print(f"    Crop size: {meta.get('crop_size')}")
    print(f"    Cell grid: {meta.get('cell_grid')}")
    print(f"    OCR text length: {meta.get('ocr_text_length')}")
    bbox = meta.get('detection_bbox', {})
    if bbox:
        conf = bbox.get('confidence', 0)
        print(f"    YOLO confidence: {conf:.3f}")

print("\n" + "=" * 70)
print("TEST COMPLETE - SUCCESS")
print("=" * 70)
