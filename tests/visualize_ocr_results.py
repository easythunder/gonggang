#!/usr/bin/env python3.11
"""Visualize OCR results with schedule breakdown charts."""
import sys
sys.path.insert(0, '/Users/jin/Desktop/gong_gang/gonggang')

import random
from PIL import Image, ImageDraw, ImageFont
from src.services.ocr import OCRWrapper

# Sample data
DAYS_KOREAN = ['월', '화', '수', '목', '금']
DAYS_NAMES = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']

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

def generate_random_schedule(day_count: int = 3, format_type: str = None) -> str:
    """Generate random schedule text."""
    if format_type is None:
        format_type = random.choice(FORMATS)
    
    schedule_lines = []
    selected_indices = random.sample(range(5), day_count)
    selected_indices.sort()
    
    for idx in selected_indices:
        day_format = random.choice(['korean', 'english', 'abbreviated', 'mixed'])
        
        if day_format == 'korean':
            day = DAYS_KOREAN[idx]
        elif day_format == 'english':
            day = DAYS_NAMES[idx]
        elif day_format == 'abbreviated':
            day = DAYS_NAMES[idx][:3]
        else:
            day = f"{DAYS_NAMES[idx]} ({DAYS_KOREAN[idx]})"
        
        schedule_lines.append(day)
        
        slot_count = random.randint(1, 3)
        for _ in range(slot_count):
            start_time, end_time = random.choice(TIME_SLOTS)
            
            if format_type == 'range_format':
                schedule_lines.append(f"{start_time}-{end_time}")
            elif format_type == 'space_format':
                schedule_lines.append(f"{start_time} {end_time}")
            elif format_type == 'korean_format':
                schedule_lines.append(f"바쁨: {start_time}-{end_time}")
            else:
                styles = [f"{start_time}-{end_time}", f"{start_time}~{end_time}", f"Busy {start_time}-{end_time}"]
                schedule_lines.append(random.choice(styles))
    
    return '\n'.join(schedule_lines)


def create_schedule_visualization(schedule_text: str, result: list, output_path: str):
    """Create a visual representation of the schedule."""
    # Image dimensions
    width = 1000
    height = 600
    img = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(img)
    
    # Try to load a good font
    try:
        title_font = ImageFont.truetype("/Library/Fonts/Arial.ttf", 24)
        text_font = ImageFont.truetype("/Library/Fonts/Arial.ttf", 16)
        small_font = ImageFont.truetype("/Library/Fonts/Arial.ttf", 12)
    except:
        try:
            title_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
            text_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 16)
            small_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 12)
        except:
            title_font = ImageFont.load_default()
            text_font = ImageFont.load_default()
            small_font = ImageFont.load_default()
    
    # Colors
    bg_color = 'white'
    border_color = '#333333'
    title_color = '#1a1a1a'
    text_color = '#555555'
    success_color = '#2ecc71'  # Green
    result_color = '#3498db'   # Blue
    
    # Title
    draw.text((20, 20), "📊 OCR 스케줄 파싱 결과", fill=title_color, font=title_font)
    
    # Left side: Original text
    draw.text((20, 70), "📋 원본 텍스트:", fill=title_color, font=text_font)
    draw.rectangle([(20, 100), (450, 300)], outline=border_color, width=2)
    
    y_offset = 110
    for line in schedule_text.split('\n')[:10]:  # Limit to 10 lines
        draw.text((30, y_offset), line, fill=text_color, font=small_font)
        y_offset += 25
    
    # Right side: Parsed result
    draw.text((480, 70), "✅ 파싱 결과:", fill=title_color, font=text_font)
    draw.rectangle([(480, 100), (980, 300)], outline=border_color, width=2)
    
    y_offset = 110
    days_name = ['월', '화', '수', '목', '금', '토', '일']
    
    # Group results by day
    results_by_day = {}
    for day_num, start_min, end_min in result:
        if day_num not in results_by_day:
            results_by_day[day_num] = []
        results_by_day[day_num].append((start_min, end_min))
    
    for day_num in sorted(results_by_day.keys()):
        day_name = days_name[day_num]
        times = results_by_day[day_num]
        
        day_text = f"{day_name}: "
        time_texts = []
        for start_min, end_min in times:
            start_h, start_m = divmod(start_min, 60)
            end_h, end_m = divmod(end_min, 60)
            time_texts.append(f"{start_h:02d}:{start_m:02d}~{end_h:02d}:{end_m:02d}")
        
        day_text += ", ".join(time_texts)
        draw.text((490, y_offset), day_text, fill=result_color, font=small_font)
        y_offset += 25
    
    # Statistics
    stats_y = 320
    stats_text = f"📈 통계: {len(result)}개 시간대 파싱됨"
    draw.text((20, stats_y), stats_text, fill=success_color, font=text_font)
    
    # Weekly calendar view
    calendar_y = 380
    draw.text((20, calendar_y), "📅 주간 스케줄:", fill=title_color, font=text_font)
    
    # Draw calendar
    day_headers = ['월', '화', '수', '목', '금', '토', '일']
    cell_width = 130
    cell_height = 80
    calendar_start_x = 20
    calendar_start_y = 420
    
    # Draw day headers
    for i, day_header in enumerate(day_headers):
        x = calendar_start_x + i * cell_width
        draw.text((x + 50, calendar_start_y), day_header, fill=title_color, font=text_font)
    
    # Draw cells with time data
    for day_num in range(7):
        x = calendar_start_x + day_num * cell_width
        y = calendar_start_y + 30
        
        # Draw cell background
        if day_num in results_by_day:
            draw.rectangle([(x, y), (x + cell_width - 5, y + cell_height)], 
                          fill='#e8f4f8', outline=result_color, width=2)
            
            # Show count of slots
            slot_count = len(results_by_day[day_num])
            draw.text((x + 40, y + 25), f"{slot_count}개", fill=result_color, font=small_font)
        else:
            draw.rectangle([(x, y), (x + cell_width - 5, y + cell_height)], 
                          outline='#cccccc', width=1)
    
    # Save image
    img.save(output_path)
    print(f"✅ 이미지 저장: {output_path}")


def main():
    """Generate and visualize OCR results."""
    wrapper = OCRWrapper(library="tesseract", timeout_seconds=5)
    
    print("=" * 100)
    print("🎨 OCR 결과 시각화")
    print("=" * 100)
    
    output_dir = "/Users/jin/Desktop/gong_gang/gonggang/tests/output"
    import os
    os.makedirs(output_dir, exist_ok=True)
    
    for test_num in range(1, 6):
        print(f"\n📸 테스트 {test_num} 시각화 생성 중...")
        
        # Generate random schedule
        day_count = random.randint(2, 5)
        format_type = random.choice(FORMATS)
        schedule_text = generate_random_schedule(day_count=day_count, format_type=format_type)
        
        # Parse with OCR
        result = wrapper.parse_schedule_text(schedule_text)
        
        # Create visualization
        output_path = f"{output_dir}/ocr_result_{test_num:02d}.png"
        create_schedule_visualization(schedule_text, result, output_path)
        
        print(f"  파싱: {len(result)}개 시간대")
        print(f"  저장: {output_path}")
    
    print("\n" + "=" * 100)
    print(f"✅ 모든 시각화 생성 완료!")
    print(f"📁 저장 위치: {output_dir}")
    print("=" * 100)


if __name__ == '__main__':
    main()
