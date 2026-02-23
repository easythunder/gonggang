#!/usr/bin/env python3.11
"""Generate detailed OCR analysis report that I can actually process."""
import sys
sys.path.insert(0, '/Users/jin/Desktop/gong_gang/gonggang')

import random
import json
from src.services.ocr import OCRWrapper

# Sample data
DAYS_KOREAN = ['월', '화', '수', '목', '금']
DAYS_NAMES = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
DAYS_ABBREV = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']

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
            day = DAYS_ABBREV[idx]
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


def format_time_for_display(minutes: int) -> str:
    """Convert minutes to HH:MM format."""
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours:02d}:{mins:02d}"


def generate_detailed_report(test_num: int, schedule_text: str, result: list, format_type: str) -> dict:
    """Generate a detailed analysis report."""
    
    # Parse the raw text to show structure
    days_map = {
        'MONDAY': 0, 'TUESDAY': 1, 'WEDNESDAY': 2,
        'THURSDAY': 3, 'FRIDAY': 4, 'SATURDAY': 5, 'SUNDAY': 6
    }
    
    days_name = ['월', '화', '수', '목', '금', '토', '일']
    
    # Group results by day
    results_by_day = {}
    for day_num, start_min, end_min in result:
        if day_num not in results_by_day:
            results_by_day[day_num] = []
        results_by_day[day_num].append({
            'start': format_time_for_display(start_min),
            'end': format_time_for_display(end_min),
            'start_minutes': start_min,
            'end_minutes': end_min
        })
    
    return {
        'test_num': test_num,
        'format_type': format_type,
        'input': {
            'raw_text': schedule_text,
            'line_count': len(schedule_text.split('\n')),
        },
        'output': {
            'total_slots': len(result),
            'days_covered': list(sorted(results_by_day.keys())),
            'by_day': {
                days_name[day_num]: results_by_day.get(day_num, [])
                for day_num in range(7)
            }
        },
        'success': len(result) > 0,
        'success_rate': len(result)
    }


def main():
    """Generate detailed analysis report."""
    wrapper = OCRWrapper(library="tesseract", timeout_seconds=5)
    
    all_reports = []
    
    print("=" * 120)
    print("📊 상세 OCR 분석 리포트")
    print("=" * 120)
    print()
    
    for test_num in range(1, 6):
        print(f"\n{'=' * 120}")
        print(f"테스트 #{test_num}")
        print(f"{'=' * 120}")
        
        # Generate random schedule
        day_count = random.randint(2, 5)
        format_type = random.choice(FORMATS)
        schedule_text = generate_random_schedule(day_count=day_count, format_type=format_type)
        
        # Parse with OCR
        result = wrapper.parse_schedule_text(schedule_text)
        
        # Generate report
        report = generate_detailed_report(test_num, schedule_text, result, format_type)
        all_reports.append(report)
        
        # Display report
        print(f"\n📋 입력 분석:")
        print(f"  - 형식: {format_type}")
        print(f"  - 입력 텍스트 라인 수: {report['input']['line_count']}")
        print(f"  - 입력 텍스트:")
        for line in schedule_text.split('\n'):
            print(f"      | {line}")
        
        print(f"\n✅ 출력 분석:")
        print(f"  - 파싱된 슬롯 총 개수: {report['output']['total_slots']}")
        days_covered_str = ', '.join([f"{i}({list(report['output']['by_day'].keys())[i]})" for i in report['output']['days_covered']])
        print(f"  - 포함된 요일: {days_covered_str}")
        
        print(f"\n📅 요일별 상세 결과:")
        for day_num, day_name in enumerate(['월', '화', '수', '목', '금', '토', '일']):
            slots = report['output']['by_day'][day_name]
            if slots:
                print(f"  {day_name}: {len(slots)}개 슬롯")
                for i, slot in enumerate(slots, 1):
                    print(f"      {i}. {slot['start']} ~ {slot['end']} ({slot['start_minutes']}분 ~ {slot['end_minutes']}분)")
            else:
                print(f"  {day_name}: 없음")
        
        print(f"\n🎯 결과:")
        if report['success']:
            print(f"  ✅ 성공 - {report['output']['total_slots']}개 시간대 추출")
        else:
            print(f"  ❌ 실패 - 데이터 추출 불가")
    
    # Summary
    print(f"\n\n{'=' * 120}")
    print("📊 종합 분석")
    print(f"{'=' * 120}")
    
    total_slots = sum(r['success_rate'] for r in all_reports)
    total_tests = len(all_reports)
    success_tests = sum(1 for r in all_reports if r['success'])
    
    print(f"\n전체 통계:")
    print(f"  - 실행된 테스트: {total_tests}개")
    print(f"  - 성공한 테스트: {success_tests}개 ({success_tests*100//total_tests}%)")
    print(f"  - 추출된 총 슬롯: {total_slots}개")
    print(f"  - 평균 슬롯/테스트: {total_slots//total_tests}개")
    
    print(f"\n형식별 통계:")
    format_stats = {}
    for report in all_reports:
        fmt = report['format_type']
        if fmt not in format_stats:
            format_stats[fmt] = {'count': 0, 'slots': 0}
        format_stats[fmt]['count'] += 1
        format_stats[fmt]['slots'] += report['success_rate']
    
    for fmt, stats in sorted(format_stats.items()):
        print(f"  - {fmt:20s}: {stats['count']}회, {stats['slots']}개 슬롯 추출")
    
    # Save JSON report
    json_path = '/Users/jin/Desktop/gong_gang/gonggang/tests/output/analysis_report.json'
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(all_reports, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 JSON 리포트 저장: {json_path}")
    
    print(f"\n{'=' * 120}")
    print("✅ 분석 완료!")
    print(f"{'=' * 120}")


if __name__ == '__main__':
    main()
