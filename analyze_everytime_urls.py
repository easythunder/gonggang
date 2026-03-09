#!/usr/bin/env python3
"""다중 에브리타임 URL에서 시간표를 파싱하고 비교 분석하는 스크립트."""

import sys
import logging
import json
from typing import List, Tuple, Dict, Set
from pathlib import Path

from src.services.everytime_parser import EverytimeTimetableParser, EverytimeParserError

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DAYS = ['월', '화', '수', '목', '금', '토', '일']


def minutes_to_time(minutes: int) -> str:
    """분 단위를 HH:MM 형식으로 변환"""
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours:02d}:{mins:02d}"


def parse_url(parser: EverytimeTimetableParser, url: str, timeout: int = 10) -> Tuple[bool, List[Tuple[int, int, int]], str]:
    """
    단일 URL 파싱
    Returns: (성공 여부, 시간대 목록, 오류 메시지)
    """
    try:
        if not parser.validate_everytime_url(url):
            return False, [], "유효하지 않은 URL 형식"
        
        html = parser.fetch_html(url, timeout_seconds=timeout)
        intervals = parser.parse_html_to_pairs(html)
        return True, intervals, ""
    except EverytimeParserError as e:
        return False, [], str(e)
    except Exception as e:
        return False, [], f"예기치 않은 오류: {e}"


def format_schedule_detailed(
    intervals: List[Tuple[int, int, int]],
    name: str = ""
) -> Dict[str, List[Dict]]:
    """시간표를 요일별로 정렬"""
    schedule_by_day = {day: [] for day in DAYS}
    
    for day_idx, start_min, end_min in intervals:
        if 0 <= day_idx < len(DAYS):
            day = DAYS[day_idx]
            schedule_by_day[day].append({
                'start': minutes_to_time(start_min),
                'end': minutes_to_time(end_min),
                'start_min': start_min,
                'end_min': end_min,
                'duration_min': end_min - start_min
            })
    
    for day in schedule_by_day:
        schedule_by_day[day].sort(key=lambda x: x['start_min'])
    
    return schedule_by_day


def find_common_free_times(
    schedules: Dict[str, List[Tuple[int, int, int]]],
    min_duration: int = 30
) -> Dict[str, List[Tuple[int, int]]]:
    """모든 사람이 동시에 자유인 시간 찾기"""
    free_times = {}
    
    for day_idx, day in enumerate(DAYS):
        # 이 요일의 모든 수업 시간 수집
        busy_times = []
        
        for person, intervals in schedules.items():
            for d, start, end in intervals:
                if d == day_idx:
                    busy_times.append((start, end))
        
        # 수업 시간이 없으면 전일 자유
        if not busy_times:
            free_times[day] = [(8*60, 22*60)]
            continue
        
        # 수업 시간을 정렬하고 겹치는 부분 병합
        busy_times.sort()
        merged = []
        for start, end in busy_times:
            if merged and start <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(merged[-1][1], end))
            else:
                merged.append((start, end))
        
        # 자유 시간 계산
        free = []
        day_start = 8 * 60  # 08:00
        day_end = 22 * 60   # 22:00
        
        if not merged:
            free.append((day_start, day_end))
        else:
            if merged[0][0] > day_start:
                free.append((day_start, merged[0][0]))
            
            for i in range(len(merged) - 1):
                gap_start = merged[i][1]
                gap_end = merged[i+1][0]
                if gap_end - gap_start >= min_duration:
                    free.append((gap_start, gap_end))
            
            if merged[-1][1] < day_end:
                free.append((merged[-1][1], day_end))
        
        free_times[day] = free
    
    return free_times


def display_person_schedule(name: str, schedule: Dict[str, List[Dict]]), indent: str = "  "):
    """한 사람의 시간표 표시"""
    print(f"\n{indent}👤 {name}")
    print(f"{indent}" + "-" * 50)
    
    has_schedule = False
    for day in DAYS:
        classes = schedule[day]
        if classes:
            has_schedule = True
            for item in classes:
                print(
                    f"{indent}  {day} {item['start']}-{item['end']} "
                    f"({item['duration_min']:3d}분)"
                )
    
    if not has_schedule:
        print(f"{indent}  [수업 없음]")


def display_common_free_times(free_times: Dict[str, List[Tuple[int, int]]]):
    """공통 자유 시간 표시"""
    print("\n" + "="*70)
    print("⏰ 공통 자유 시간 (모든 사람이 동시에 만날 수 있는 시간)")
    print("="*70)
    
    has_free_time = False
    for day in DAYS:
        times = free_times[day]
        if times:
            has_free_time = True
            print(f"\n📅 {day}요일:")
            for start, end in times:
                duration = end - start
                print(
                    f"  {minutes_to_time(start)}-{minutes_to_time(end)} "
                    f"({duration//60}시간 {duration%60:02d}분)"
                )
    
    if not has_free_time:
        print("\n⚠️  공통 자유 시간이 없습니다")


def check_multiple_urls(
    urls: List[Tuple[str, str]],
    timeout: int = 10,
    min_free_duration: int = 30,
    output_file: str = None
) -> bool:
    """
    다중 URL 검증 및 분석
    
    Args:
        urls: [(이름, URL), ...] 튜플 리스트
        timeout: 페이지 로딩 타임아웃
        min_free_duration: 최소 자유 시간 (분)
        output_file: 결과 저장 파일 경로
    
    Returns:
        bool: 모든 URL이 성공했는지 여부
    """
    parser = EverytimeTimetableParser()
    
    print("\n" + "="*70)
    print("🔍 다중 에브리타임 시간표 파싱 및 분석")
    print("="*70)
    print(f"\n총 {len(urls)}명의 시간표 검사 시작...")
    
    results = {}
    all_success = True
    
    # Step 1: 모든 URL 파싱
    print("\n📋 Step 1: 시간표 파싱")
    print("-" * 70)
    
    for name, url in urls:
        print(f"\n  📍 {name}: {url}")
        success, intervals, error = parse_url(parser, url, timeout)
        
        if success:
            print(f"     ✅ 성공 ({len(intervals)}개 과목)")
            results[name] = {
                'url': url,
                'success': True,
                'intervals': intervals,
                'error': None
            }
        else:
            print(f"     ❌ 실패: {error}")
            results[name] = {
                'url': url,
                'success': False,
                'intervals': [],
                'error': error
            }
            all_success = False
    
    # 성공한 결과만 계속 처리
    successful_results = {
        name: data for name, data in results.items() if data['success']
    }
    
    if not successful_results:
        print("\n❌ 성공한 파싱이 없습니다")
        return False
    
    # Step 2: 시간표 표시
    print("\n" + "="*70)
    print("📅 Step 2: 개별 시간표")
    print("="*70)
    
    schedules_dict = {}
    for name, data in successful_results.items():
        schedule = format_schedule_detailed(data['intervals'], name)
        schedules_dict[name] = schedule
        display_person_schedule(name, schedule)
    
    # Step 3: 통계
    print("\n" + "="*70)
    print("📊 Step 3: 통계")
    print("="*70)
    
    for name in sorted(successful_results.keys()):
        intervals = successful_results[name]['intervals']
        total_hours = sum((end - start) / 60 for _, start, end in intervals)
        days_with_classes = sum(
            1 for day in DAYS
            if any(d == DAYS.index(day) for d, _, _ in intervals)
        )
        
        print(f"\n👤 {name}:")
        print(f"   • 총 수업 시간: {total_hours:.1f}시간")
        print(f"   • 수업 있는 요일: {days_with_classes}/7일")
        print(f"   • 과목 수: {len(intervals)}개")
    
    # Step 4: 공통 자유 시간
    if len(successful_results) > 1:
        free_times = find_common_free_times(
            {name: data['intervals'] for name, data in successful_results.items()},
            min_duration=min_free_duration
        )
        display_common_free_times(free_times)
        
        # Step 5: 결과 저장
        if output_file:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            output_data = {
                'created_at': __import__('datetime').datetime.now().isoformat(),
                'participants': list(successful_results.keys()),
                'schedules': {
                    name: {
                        day: [
                            {
                                'start': item['start'],
                                'end': item['end'],
                                'duration_min': item['duration_min']
                            }
                            for item in classes
                        ]
                        for day, classes in schedule.items()
                    }
                    for name, schedule in schedules_dict.items()
                },
                'common_free_times': {
                    day: [
                        {
                            'start': minutes_to_time(start),
                            'end': minutes_to_time(end),
                            'duration_min': end - start
                        }
                        for start, end in times
                    ]
                    for day, times in free_times.items()
                }
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
            
            print(f"\n💾 결과 저장됨: {output_path}")
    
    print("\n" + "="*70)
    print("✨ 분석 완료!")
    print("="*70 + "\n")
    
    return all_success


def main():
    """메인 실행"""
    if len(sys.argv) < 2:
        print("사용법: python analyze_everytime_urls.py <URL1> [<URL2> ...] [--names <NAME1> <NAME2> ...] [--output <파일경로>]")
        print("\n예시:")
        print("  python analyze_everytime_urls.py https://everytime.kr/@XXXXX https://everytime.kr/@YYYYY")
        print("  python analyze_everytime_urls.py https://everytime.kr/@XXXXX https://everytime.kr/@YYYYY --names 학생1 학생2")
        print("  python analyze_everytime_urls.py ... --output result.json")
        sys.exit(1)
    
    args = sys.argv[1:]
    urls = []
    names = []
    output_file = None
    
    i = 0
    while i < len(args):
        if args[i] == '--names':
            i += 1
            while i < len(args) and not args[i].startswith('--'):
                names.append(args[i])
                i += 1
        elif args[i] == '--output':
            i += 1
            if i < len(args):
                output_file = args[i]
                i += 1
        elif args[i].startswith('http'):
            urls.append(args[i])
            i += 1
        else:
            i += 1
    
    # 이름이 제공되지 않으면 자동 생성
    if not names:
        names = [f"사용자{i+1}" for i in range(len(urls))]
    elif len(names) < len(urls):
        names.extend([f"사용자{i+1}" for i in range(len(names), len(urls))])
    
    url_tuples = list(zip(names, urls))
    
    success = check_multiple_urls(url_tuples, output_file=output_file)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
