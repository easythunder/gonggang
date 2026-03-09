#!/usr/bin/env python3
"""에브리타임 URL 파싱 테스트 - 간단한 예제"""

from src.services.everytime_parser import EverytimeTimetableParser, EverytimeParserError

# ===== 예제 1: 단일 URL 파싱 =====
def example_single_url():
    print("\n" + "="*70)
    print("예제 1: 단일 URL 파싱")
    print("="*70)
    
    url = input("에브리타임 URL 입력: ").strip()
    if not url:
        print("❌ URL이 비어있습니다")
        return
    
    parser = EverytimeTimetableParser()
    
    print(f"\n⏳ 파싱 중... ({url})")
    try:
        intervals = parser.parse_from_url(url, timeout_seconds=10)
        
        print(f"\n✅ 성공!")
        print(f"📊 총 {len(intervals)}개 과목 발견\n")
        
        # 요일별 정렬
        DAYS = ['월', '화', '수', '목', '금', '토', '일']
        schedule_by_day = {day: [] for day in DAYS}
        
        for day_idx, start_min, end_min in intervals:
            if 0 <= day_idx < len(DAYS):
                hours_start = start_min // 60
                mins_start = start_min % 60
                hours_end = end_min // 60
                mins_end = end_min % 60
                
                day = DAYS[day_idx]
                schedule_by_day[day].append({
                    'start': f"{hours_start:02d}:{mins_start:02d}",
                    'end': f"{hours_end:02d}:{mins_end:02d}",
                    'duration': end_min - start_min
                })
        
        # 출력
        for day in DAYS:
            classes = schedule_by_day[day]
            if classes:
                classes.sort(key=lambda x: x['start'])
                print(f"📅 {day}요일:")
                for cls in classes:
                    print(f"   {cls['start']}-{cls['end']} ({cls['duration']}분)")
        
        # 통계
        total_hours = sum(end - start for _, start, end in intervals) / 60
        print(f"\n📊 통계:")
        print(f"   • 총 수업 시간: {total_hours:.1f}시간")
        print(f"   • 수업이 있는 요일: {sum(1 for day in DAYS if schedule_by_day[day])}/7일")
        
    except EverytimeParserError as e:
        print(f"\n❌ 파싱 실패: {e}")
    except Exception as e:
        print(f"\n❌ 오류: {e}")


# ===== 예제 2: 다중 URL 비교 =====
def example_multiple_urls():
    print("\n" + "="*70)
    print("예제 2: 다중 URL 비교 (공통 자유 시간)")
    print("="*70)
    
    parser = EverytimeTimetableParser()
    
    urls = []
    names = []
    
    print("\n📍 URL 입력 (빈 줄로 종료):")
    while True:
        name = input(f"이름 [{len(urls)+1}]: ").strip()
        if not name:
            if urls:
                break
            else:
                print("❌ 최소 1개 이상의 URL이 필요합니다")
                continue
        
        url = input(f"URL: ").strip()
        if not url:
            print("❌ URL이 비어있습니다")
            continue
        
        urls.append(url)
        names.append(name)
        print()
    
    # 파싱
    schedules = {}
    print(f"⏳ {len(urls)}개 URL 파싱 중...\n")
    
    for name, url in zip(names, urls):
        try:
            print(f"  처리 중: {name}...", end=" ", flush=True)
            intervals = parser.parse_from_url(url, timeout_seconds=10)
            schedules[name] = intervals
            print(f"✅ ({len(intervals)}개 과목)")
        except Exception as e:
            print(f"❌ {e}")
    
    if len(schedules) < len(urls):
        print(f"\n⚠️  {len(urls) - len(schedules)}개 URL 파싱 실패")
    
    if not schedules:
        print("❌ 파싱된 결과가 없습니다")
        return
    
    # 개별 시간표 표시
    DAYS = ['월', '화', '수', '목', '금', '토', '일']
    
    print("\n" + "="*70)
    print("📅 개별 시간표")
    print("="*70)
    
    for name, intervals in schedules.items():
        print(f"\n👤 {name}:")
        
        schedule_by_day = {day: [] for day in DAYS}
        for day_idx, start_min, end_min in intervals:
            if 0 <= day_idx < len(DAYS):
                day = DAYS[day_idx]
                start_str = f"{start_min//60:02d}:{start_min%60:02d}"
                end_str = f"{end_min//60:02d}:{end_min%60:02d}"
                schedule_by_day[day].append({
                    'start': start_str,
                    'end': end_str,
                    'start_min': start_min,
                    'end_min': end_min
                })
        
        for day in DAYS:
            classes = schedule_by_day[day]
            if classes:
                classes.sort(key=lambda x: x['start_min'])
                for cls in classes:
                    print(f"   {day} {cls['start']}-{cls['end']}")
    
    # 공통 자유 시간 계산
    print("\n" + "="*70)
    print("⏰ 공통 자유 시간 (30분 이상)")
    print("="*70)
    
    for day_idx, day in enumerate(DAYS):
        # 이 요일의 모든 수업 시간 수집
        busy_times = []
        
        for name, intervals in schedules.items():
            for d, start, end in intervals:
                if d == day_idx:
                    busy_times.append((start, end))
        
        # 수업 시간 병합
        if busy_times:
            busy_times.sort()
            merged = []
            for start, end in busy_times:
                if merged and start <= merged[-1][1]:
                    merged[-1] = (merged[-1][0], max(merged[-1][1], end))
                else:
                    merged.append((start, end))
        else:
            merged = []
        
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
                if gap_end - gap_start >= 30:
                    free.append((gap_start, gap_end))
            
            if merged[-1][1] < day_end:
                free.append((merged[-1][1], day_end))
        
        # 출력
        if free:
            print(f"\n📅 {day}요일:")
            for start, end in free:
                duration_h = (end - start) // 60
                duration_m = (end - start) % 60
                start_str = f"{start//60:02d}:{start%60:02d}"
                end_str = f"{end//60:02d}:{end%60:02d}"
                print(f"   {start_str}-{end_str} ({duration_h}시간 {duration_m}분)")


# ===== 메인 메뉴 =====
def main():
    while True:
        print("\n" + "="*70)
        print("🎓 에브리타임 시간표 파싱 테스트")
        print("="*70)
        print("\n1️⃣  단일 URL 파싱")
        print("2️⃣  다중 URL 비교 (공통 자유 시간)")
        print("3️⃣  종료")
        
        choice = input("\n선택 (1-3): ").strip()
        
        if choice == "1":
            example_single_url()
        elif choice == "2":
            example_multiple_urls()
        elif choice == "3":
            print("\n👋 종료합니다")
            break
        else:
            print("❌ 잘못된 선택입니다 (1-3)")


if __name__ == "__main__":
    main()
