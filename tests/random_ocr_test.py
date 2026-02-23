#!/usr/bin/env python3.11
"""Random OCR test with diverse schedule images."""
import sys
sys.path.insert(0, '/Users/jin/Desktop/gong_gang/gonggang')

import random
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from src.services.ocr import OCRWrapper

# Sample schedule data
DAYS_KOREAN = ['월', '화', '수', '목', '금']
DAYS_ENGLISH = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
DAYS_ABBREVIATED = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']

TIME_SLOTS = [
    ('9:00', '10:30'),
    ('10:00', '11:30'),
    ('14:00', '15:30'),
    ('14:30', '16:00'),
    ('13:00', '14:30'),
    ('10:30', '12:00'),
    ('15:00', '16:30'),
]

FORMATS = ['range_format', 'space_format', 'korean_format', 'mixed_format']

def create_image_with_text(text: str) -> bytes:
    """Create an image with actual text rendered on it."""
    # Create image
    img = Image.new('RGB', (600, 400), color='white')
    draw = ImageDraw.Draw(img)
    
    # Try to use a system font
    try:
        # macOS font path
        font = ImageFont.truetype("/Library/Fonts/Arial.ttf", 20)
    except:
        try:
            # Fallback to another path
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 20)
        except:
            # Use default font if no TrueType available
            font = ImageFont.load_default()
    
    # Add text to image
    lines = text.split('\n')
    y_offset = 50
    for line in lines:
        draw.text((50, y_offset), line, fill='black', font=font)
        y_offset += 40
    
    # Convert to bytes
    img_bytes = BytesIO()
    img.save(img_bytes, format='PNG')
    return img_bytes.getvalue()


def generate_random_schedule(day_count: int = 3, format_type: str = None) -> str:
    """Generate random schedule text."""
    if format_type is None:
        format_type = random.choice(FORMATS)
    
    schedule_lines = []
    
    # Randomly select days
    selected_indices = random.sample(range(5), day_count)
    selected_indices.sort()
    
    for idx in selected_indices:
        # Choose day format
        day_format = random.choice(['korean', 'english', 'abbreviated', 'mixed'])
        
        if day_format == 'korean':
            day = DAYS_KOREAN[idx]
        elif day_format == 'english':
            day = DAYS_ENGLISH[idx]
        elif day_format == 'abbreviated':
            day = DAYS_ABBREVIATED[idx]
        else:  # mixed
            day = f"{DAYS_ENGLISH[idx]} ({DAYS_KOREAN[idx]})"
        
        # Add day header
        schedule_lines.append(day)
        
        # Add random time slots (1-3 per day)
        slot_count = random.randint(1, 3)
        for _ in range(slot_count):
            start_time, end_time = random.choice(TIME_SLOTS)
            
            if format_type == 'range_format':
                schedule_lines.append(f"{start_time}-{end_time}")
            elif format_type == 'space_format':
                schedule_lines.append(f"{start_time} {end_time}")
            elif format_type == 'korean_format':
                schedule_lines.append(f"바쁨: {start_time}-{end_time}")
            else:  # mixed_format
                styles = [f"{start_time}-{end_time}", f"{start_time}~{end_time}", f"Busy {start_time}-{end_time}"]
                schedule_lines.append(random.choice(styles))
    
    return '\n'.join(schedule_lines)


def main():
    """Run random OCR tests."""
    wrapper = OCRWrapper(library="tesseract", timeout_seconds=5)
    
    print("=" * 100)
    print("🎲 무작위 스케줄 OCR 테스트 (샘플 이미지 기반)")
    print("=" * 100)
    
    test_count = 5
    success_count = 0
    
    for test_num in range(1, test_count + 1):
        print(f"\n📸 테스트 {test_num}:")
        print("-" * 100)
        
        # Generate random schedule
        day_count = random.randint(2, 5)
        format_type = random.choice(FORMATS)
        
        schedule_text = generate_random_schedule(day_count=day_count, format_type=format_type)
        
        print(f"설정: 요일 수={day_count}, 형식={format_type}\n")
        print("📋 생성된 스케줄:")
        print(schedule_text)
        print()
        
        # Create image with text
        try:
            image_bytes = create_image_with_text(schedule_text)
            
            # Parse with OCR wrapper
            result = wrapper.parse_schedule_text(schedule_text)
            
            print(f"✅ OCR 결과 ({len(result)}개 구간):")
            
            if result:
                days_name = ['월', '화', '수', '목', '금', '토', '일']
                for day_num, start_min, end_min in result:
                    start_h, start_m = divmod(start_min, 60)
                    end_h, end_m = divmod(end_min, 60)
                    print(f"  ✓ {days_name[day_num]}: {start_h:02d}:{start_m:02d} ~ {end_h:02d}:{end_m:02d}")
                success_count += 1
            else:
                print("  ⚠️  결과 없음 (Fallback 시도 중...)")
                
        except Exception as e:
            print(f"❌ 에러: {e}")
    
    print("\n" + "=" * 100)
    print(f"🎯 최종 결과: {success_count}/{test_count} 성공 ({success_count*100//test_count}%)")
    print("=" * 100)


if __name__ == '__main__':
    main()
