#!/usr/bin/env python3
"""Debug OCR extraction from sample image"""

import sys
import os
sys.path.insert(0, '/app')
os.chdir('/app')

from src.services.ocr import OCRWrapper
from PIL import Image

# Test with sample image
image_path = '/app/data/everytime_samples/images/IMG_2777.PNG'

print(f"🔍 Testing OCR on {image_path}...\n")

with open(image_path, 'rb') as f:
    image_bytes = f.read()

ocr = OCRWrapper()

# Step 1: Parse image and get raw text
print("📝 Step 1: Raw OCR Text")
print("=" * 60)
raw_text = ocr.parse_image(image_bytes)
print(raw_text[:500])  # First 500 chars
print("...")
print(raw_text[-500:])  # Last 500 chars
print(f"\nTotal characters: {len(raw_text)}\n")

# Step 2: Parse schedule from text
print("📊 Step 2: Parsed Schedule")
print("=" * 60)
schedule_result = ocr.parse_schedule(image_bytes)
print(f"Schedule entries: {len(schedule_result['schedule'])}")
for entry in schedule_result['schedule'][:5]:
    print(f"  - {entry}")
print()

# Step 3: Extract intervals
print("⏱️  Step 3: Extracted Intervals")
print("=" * 60)
intervals = ocr.parse_schedule_text(raw_text)
print(f"Intervals: {len(intervals)}")
for day, start, end in intervals[:5]:
    days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    print(f"  - {days[day]}: {start:04d}-{end:04d} mins")
print()

# Step 4: Extract days and times separately
print("🔍 Step 4: Debug - Days & Times")
print("=" * 60)
days = ocr._extract_days(raw_text)
times = ocr._extract_times(raw_text)
print(f"Days found: {days}")
days_name = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
for d in days:
    print(f"  - {days_name[d]}")
print(f"\nTimes found: {times}")
for start, end in times[:5]:
    h1, m1 = divmod(start, 60)
    h2, m2 = divmod(end, 60)
    print(f"  - {h1:02d}:{m1:02d} ~ {h2:02d}:{m2:02d}")
