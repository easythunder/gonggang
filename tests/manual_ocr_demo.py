#!/usr/bin/env python3.11
"""Manual OCR demonstration with enhanced version."""
import sys
sys.path.insert(0, '/Users/jin/Desktop/gong_gang/gonggang')

from src.services.ocr import OCRWrapper, EverytimeScheduleParser

def test_enhanced_ocr():
    """Test enhanced OCR with various formats."""
    
    wrapper = OCRWrapper(library="tesseract", timeout_seconds=5)
    parser = EverytimeScheduleParser()
    
    # Test cases
    test_cases = [
        {
            "name": "한글 요일 + 시간범위",
            "text": "월\n9:00-10:30\n14:00-15:30\n\n화\n10:00-11:00"
        },
        {
            "name": "영문 요일 + 시간범위",
            "text": "MONDAY\n9:00-10:30 Busy\n14:00-15:30 Busy\n\nTUESDAY\n10:00-11:00 Busy"
        },
        {
            "name": "축약 영문 요일",
            "text": "Mon 9:00-10:30\nTue 14:00-15:00\nWed 10:30-12:00"
        },
        {
            "name": "요일 없는 시간범위 (멀티데이)",
            "text": "Meeting 9:00-10:30"
        },
        {
            "name": "복합 형식",
            "text": """
            Schedule for next week:
            Monday: 9:00-10:30
            Tuesday (화): 14:00-15:30
            Wed 10:00-11:30
            """
        }
    ]
    
    print("=" * 80)
    print("🚀 강화된 OCR 테스트")
    print("=" * 80)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📝 테스트 {i}: {test_case['name']}")
        print("-" * 80)
        
        text = test_case['text']
        print(f"입력:\n{text}\n")
        
        # Parse with enhanced parser
        result = parser.parse(text)
        
        print(f"파싱 결과 ({len(result)}개 항목):")
        for entry in result:
            print(f"  - 요일: {entry['day']}, 시간: {entry['start']} ~ {entry['end']}")
        
        # Also test parse_schedule_text
        intervals = wrapper.parse_schedule_text(text)
        print(f"\n간격 추출 ({len(intervals)}개 구간):")
        days_name = ['월', '화', '수', '목', '금', '토', '일']
        for day_num, start_min, end_min in intervals:
            start_h, start_m = divmod(start_min, 60)
            end_h, end_m = divmod(end_min, 60)
            print(f"  - {days_name[day_num]}: {start_h:02d}:{start_m:02d} ~ {end_h:02d}:{end_m:02d}")
    
    print("\n" + "=" * 80)
    print("✅ 모든 테스트 완료!")
    print("=" * 80)


if __name__ == '__main__':
    test_enhanced_ocr()
