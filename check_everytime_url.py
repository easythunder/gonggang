#!/usr/bin/env python3
"""에브리타임 URL에서 시간표를 직접 파싱하고 확인하는 스크립트."""

import sys
import logging
from typing import List, Tuple, Dict
from datetime import time

from src.services.everytime_parser import EverytimeTimetableParser, EverytimeParserError

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 요일별 인덱스
DAYS = ['월', '화', '수', '목', '금', '토', '일']


def minutes_to_time(minutes: int) -> str:
    """분 단위를 HH:MM 형식으로 변환"""
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours:02d}:{mins:02d}"


def format_schedule(
    intervals: List[Tuple[int, int, int]]
) -> Dict[str, List[Dict]]:
    """
    (day_index, start_minute, end_minute) 튜플을 정렬된 형식으로 변환
    Returns: {'일': [{'start': '09:00', 'end': '10:30', ...}], ...}
    """
    schedule_by_day = {day: [] for day in DAYS}
    
    for day_idx, start_min, end_min in intervals:
        if 0 <= day_idx < len(DAYS):
            day = DAYS[day_idx]
            schedule_by_day[day].append({
                'start': minutes_to_time(start_min),
                'end': minutes_to_time(end_min),
                'duration_min': end_min - start_min
            })
    
    # 각 요일별로 시간순으로 정렬
    for day in schedule_by_day:
        schedule_by_day[day].sort(key=lambda x: x['start'])
    
    return schedule_by_day


def check_everytime_url(url: str, timeout: int = 10) -> bool:
    """
    에브리타임 URL을 검증하고 시간표를 파싱합니다.
    
    Args:
        url: 에브리타임 공용 시간표 URL (e.g., https://everytime.kr/@XXXXX)
        timeout: 페이지 로딩 타임아웃 (초)
    
    Returns:
        bool: 성공 여부
    """
    parser = EverytimeTimetableParser()
    
    print("\n" + "="*70)
    print("🔍 에브리타임 시간표 파싱")
    print("="*70)
    print(f"\n📍 URL: {url}")
    
    # Step 1: URL 검증
    print(f"\n1️⃣  URL 검증 중...")
    if not parser.validate_everytime_url(url):
        print("❌ 유효하지 않은 에브리타임 URL입니다")
        print("   형식: https://everytime.kr/@XXXXX")
        return False
    print("✅ URL 형식 유효")
    
    # Step 2: HTML 페칭
    print(f"\n2️⃣  HTML 페칭 중 (타임아웃: {timeout}초)...")
    try:
        html = parser.fetch_html(url, timeout_seconds=timeout)
        print(f"✅ HTML 페칭 성공 ({len(html)} bytes)")
    except EverytimeParserError as e:
        print(f"❌ HTML 페칭 실패: {e}")
        return False
    except Exception as e:
        print(f"❌ 예기치 않은 오류: {e}")
        return False
    
    # Step 3: 시간표 파싱
    print(f"\n3️⃣  시간표 파싱 중...")
    try:
        intervals = parser.parse_html_to_pairs(html)
        if not intervals:
            print("⚠️  시간표를 찾을 수 없습니다 (시간표가 비어있는 경우)")
            return True
        print(f"✅ 파싱 성공 ({len(intervals)} 과목 발견)")
    except EverytimeParserError as e:
        print(f"❌ 파싱 실패: {e}")
        return False
    except Exception as e:
        print(f"❌ 예기치 않은 오류: {e}")
        return False
    
    # Step 4: 시간표 표시
    print(f"\n4️⃣  시간표 정보")
    print("-" * 70)
    
    schedule = format_schedule(intervals)
    
    has_schedule = False
    for day in DAYS:
        classes = schedule[day]
        if classes:
            has_schedule = True
            print(f"\n📅 {day}요일:")
            for item in classes:
                print(
                    f"   {item['start']}-{item['end']} "
                    f"({item['duration_min']}분)"
                )
    
    if not has_schedule:
        print("⚠️  요일별 시간표가 없습니다")
    
    # Step 5: 데이터 검증
    print(f"\n5️⃣  데이터 검증")
    print("-" * 70)
    
    validation_results = validate_schedule(intervals)
    
    for check_name, status, message in validation_results:
        symbol = "✅" if status else "⚠️ "
        print(f"{symbol} {check_name}: {message}")
    
    # Step 6: 통계
    print(f"\n6️⃣  통계")
    print("-" * 70)
    total_hours = sum(
        (end - start) / 60 for _, start, end in intervals
    )
    days_with_classes = sum(
        1 for day in DAYS if schedule[day]
    )
    
    print(f"📊 총 수업 시간: {total_hours:.1f}시간")
    print(f"📊 수업이 있는 요일: {days_with_classes}/7일")
    print(f"📊 수업 개수: {len(intervals)}개")
    
    avg_class_duration = (
        sum((end - start) for _, start, end in intervals) / len(intervals) / 60
        if intervals
        else 0
    )
    print(f"📊 평균 수업 시간: {avg_class_duration:.1f}시간")
    
    print("\n" + "="*70)
    print("✨ 파싱 완료!")
    print("="*70 + "\n")
    
    return True


def validate_schedule(intervals: List[Tuple[int, int, int]]) -> List[Tuple[str, bool, str]]:
    """시간표 데이터 검증"""
    results = []
    
    # 1. 시간 범위 확인 (08:00 - 23:59)
    valid_time_range = all(
        0 <= start < 1440 and 0 < end <= 1440 and start < end
        for _, start, end in intervals
    )
    results.append((
        "시간 범위",
        valid_time_range,
        "08:00-23:59 범위 내" if valid_time_range else "범위 초과 항목 있음"
    ))
    
    # 2. 요일 범위 확인 (0-6: 월-일)
    valid_days = all(0 <= day <= 6 for day, _, _ in intervals)
    results.append((
        "요일 범위",
        valid_days,
        "월-일 범위 내" if valid_days else "범위 초과 항목 있음"
    ))
    
    # 3. 4시간 이상 수업 확인
    long_classes = [
        (day, start, end) for day, start, end in intervals
        if (end - start) > 4 * 60
    ]
    no_long_classes = len(long_classes) == 0
    results.append((
        "수업 길이",
        no_long_classes,
        "정상 (4시간 이상 없음)" if no_long_classes else f"주의: {len(long_classes)}개의 4시간 이상 수업"
    ))
    
    # 4. 요일별 겹침 확인
    def has_overlap(intervals_list):
        for i, (d1, s1, e1) in enumerate(intervals_list):
            for d2, s2, e2 in intervals_list[i+1:]:
                if d1 == d2 and not (e1 <= s2 or e2 <= s1):
                    return True
        return False
    
    no_overlaps = not has_overlap(intervals)
    results.append((
        "시간 겹침",
        no_overlaps,
        "없음" if no_overlaps else "같은 요일에 겹치는 수업 있음"
    ))
    
    # 5. 최소 수업 길이 확인 (15분 이상)
    min_duration = min((end - start for _, start, end in intervals), default=0)
    valid_min_duration = min_duration >= 15 if intervals else True
    results.append((
        "최소 수업 길이",
        valid_min_duration,
        f"최소 {min_duration}분" if valid_min_duration else f"15분 미만 수업 있음 ({min_duration}분)"
    ))
    
    return results


def main():
    """메인 실행"""
    if len(sys.argv) < 2:
        print("사용법: python check_everytime_url.py <에브리타임_URL> [타임아웃]")
        print("\n예시:")
        print("  python check_everytime_url.py https://everytime.kr/@XXXXX")
        print("  python check_everytime_url.py https://everytime.kr/@XXXXX 15")
        sys.exit(1)
    
    url = sys.argv[1]
    timeout = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    
    success = check_everytime_url(url, timeout=timeout)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
