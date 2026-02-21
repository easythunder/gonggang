#!/usr/bin/env python3
"""Quick OCR test on first image to guide annotation."""

import sys
from pathlib import Path
from PIL import Image

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.services.ocr import OCRWrapper

def main():
    images_dir = Path(project_root) / "data" / "everytime_samples" / "images"
    image_files = sorted(images_dir.glob("*.PNG"))
    
    if not image_files:
        print("❌ No images found!")
        return
    
    print(f"✅ Found {len(image_files)} images\n")
    print("="*70)
    print("Testing first 3 images for OCR")
    print("="*70 + "\n")
    
    ocr = OCRWrapper()
    
    for i, img_path in enumerate(image_files[:3]):
        print(f"\n📷 Image {i+1}: {img_path.name}")
        print("-" * 70)
        
        # Read image
        with open(img_path, 'rb') as f:
            img_bytes = f.read()
        
        try:
            # Parse schedule
            result = ocr.parse_schedule(img_bytes)
            
            print(f"✓ Raw OCR text ({len(result['raw_text'])} chars):")
            print(result['raw_text'][:300] + "..." if len(result['raw_text']) > 300 else result['raw_text'])
            
            print(f"\n✓ Extracted schedule ({len(result['schedule'])} entries):")
            for entry in result['schedule'][:5]:  # Show first 5
                print(f"  - {entry['day']}: {entry['start']} ~ {entry['end']}")
            
            print(f"\n✓ Confidence: {result['confidence']:.1%}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print("\n" + "="*70)
    print("Summary Statistics")
    print("="*70)
    print(f"Total images: {len(image_files)}")
    print(f"\nNext: Create annotation files in data/everytime_samples/annotations/")
    print("Format: image_001.json, image_002.json, etc.")

if __name__ == "__main__":
    main()
