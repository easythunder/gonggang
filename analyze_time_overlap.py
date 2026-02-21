#!/usr/bin/env python3
"""
시간 겹침 분석 - 여러 사람의 시간표에서 공통 자유 시간 찾기
"""

import json
from pathlib import Path
from typing import List, Dict, Tuple, Set

class TimeSlot:
    """시간 슬롯"""
    def __init__(self, day: str, start: str, end: str):
        self.day = day
        self.start_time = self._time_to_minutes(start)
        self.end_time = self._time_to_minutes(end)
    
    def _time_to_minutes(self, time_str: str) -> int:
        """HH:MM을 분 단위로 변환"""
        h, m = map(int, time_str.split(':'))
        return h * 60 + m
    
    def overlaps_with(self, other: 'TimeSlot') -> bool:
        """다른 슬롯과 겹치는지 확인"""
        if self.day != other.day:
            return False
        # 겹치지 않는 경우: 한쪽이 다른 쪽보다 완전히 먼저 끝남
        return not (self.end_time <= other.start_time or self.start_time >= other.end_time)
    
    def __repr__(self):
        return f"{self.day} {self._minutes_to_time(self.start_time)}-{self._minutes_to_time(self.end_time)}"
    
    @staticmethod
    def _minutes_to_time(minutes: int) -> str:
        """분 단위를 HH:MM으로 변환"""
        h = minutes // 60
        m = minutes % 60
        return f"{h:02d}:{m:02d}"


class ScheduleAnalyzer:
    """시간표 분석기"""
    
    def __init__(self):
        self.days_order = ['월', '화', '수', '목', '금', '토', '일']
    
    def load_schedules(self, annotation_files: List[Path]) -> Dict[str, List[TimeSlot]]:
        """annotation 파일들을 로드"""
        schedules = {}
        
        for ann_file in annotation_files:
            with open(ann_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            person_name = ann_file.stem  # IMG_2777, IMG_2778, ...
            slots = []
            
            for entry in data['schedule']:
                slot = TimeSlot(entry['day'], entry['start'], entry['end'])
                slots.append(slot)
            
            schedules[person_name] = slots
        
        return schedules
    
    def analyze_overlaps(self, schedules: Dict[str, List[TimeSlot]]) -> Dict:
        """시간 겹침 분석"""
        result = {
            'schedules': {},
            'overlaps': [],
            'free_times': {}
        }
        
        # 각 사람의 시간표 저장
        for person, slots in schedules.items():
            result['schedules'][person] = [str(s) for s in slots]
        
        # 겹침 분석
        people = list(schedules.keys())
        for i, person1 in enumerate(people):
            for person2 in people[i+1:]:
                overlapping_slots = []
                
                for slot1 in schedules[person1]:
                    for slot2 in schedules[person2]:
                        if slot1.overlaps_with(slot2):
                            overlap_end = min(slot1.end_time, slot2.end_time)
                            overlap_start = max(slot1.start_time, slot2.start_time)
                            
                            overlapping_slots.append({
                                'day': slot1.day,
                                'start': TimeSlot._minutes_to_time(overlap_start),
                                'end': TimeSlot._minutes_to_time(overlap_end),
                                'person1_class': f"{slot1} (겹침)",
                                'person2_class': f"{slot2} (겹침)"
                            })
                
                if overlapping_slots:
                    result['overlaps'].append({
                        'person1': person1,
                        'person2': person2,
                        'overlapping_times': overlapping_slots
                    })
        
        # 전체 자유 시간 찾기 (모든 사람이 동시에 가능)
        if people:
            result['free_times'] = self._find_common_free_times(schedules)
        
        return result
    
    def _find_common_free_times(self, schedules: Dict[str, List[TimeSlot]]) -> Dict:
        """모든 사람이 동시에 자유로운 시간 찾기"""
        free_times_by_day = {}
        
        # 시간 범위 설정 (08:00 - 22:00)
        start_hour = 8 * 60  # 08:00
        end_hour = 22 * 60   # 22:00
        
        for day in self.days_order:
            # 이 요일에 수업이 있는 사람들만 확인
            busy_slots = []
            
            for person, slots in schedules.items():
                day_slots = [s for s in slots if s.day == day]
                busy_slots.extend(day_slots)
            
            # busy_slots를 시간순으로 정렬
            busy_slots.sort(key=lambda s: s.start_time)
            
            # 자유 시간 찾기
            free_intervals = []
            
            if not busy_slots:
                # 이 요일에 수업이 없으면 전일 자유
                free_intervals.append((start_hour, end_hour))
            else:
                # 첫 수업 전
                if busy_slots[0].start_time > start_hour:
                    free_intervals.append((start_hour, busy_slots[0].start_time))
                
                # 수업 사이
                for i in range(len(busy_slots) - 1):
                    gap_start = busy_slots[i].end_time
                    gap_end = busy_slots[i + 1].start_time
                    
                    if gap_end - gap_start >= 30:  # 30분 이상의 간격만
                        free_intervals.append((gap_start, gap_end))
                
                # 마지막 수업 후
                if busy_slots[-1].end_time < end_hour:
                    free_intervals.append((busy_slots[-1].end_time, end_hour))
            
            # 60분 이상의 연속 자유 시간만 표시
            free_intervals = [
                (TimeSlot._minutes_to_time(start), TimeSlot._minutes_to_time(end))
                for start, end in free_intervals
                if end - start >= 60
            ]
            
            if free_intervals:
                free_times_by_day[day] = free_intervals
        
        return free_times_by_day


# 메인 실행
if __name__ == "__main__":
    ann_dir = Path("data/everytime_samples/annotations")
    annotation_files = sorted(ann_dir.glob("IMG_*.json"))
    
    print("=" * 70)
    print("🕐 시간 겹침 분석 및 자유 시간 찾기")
    print("=" * 70)
    
    analyzer = ScheduleAnalyzer()
    schedules = analyzer.load_schedules(annotation_files)
    
    print(f"\n📊 분석 대상: {len(schedules)}명\n")
    
    # 개별 시간표 출력
    for person, slots in schedules.items():
        print(f"👤 {person}:")
        
        # 요일별로 정렬
        by_day = {}
        for slot in slots:
            if slot.day not in by_day:
                by_day[slot.day] = []
            by_day[slot.day].append(slot)
        
        for day in analyzer.days_order:
            if day in by_day:
                print(f"   {day}:", end=" ")
                times = [f"{TimeSlot._minutes_to_time(s.start_time)}-{TimeSlot._minutes_to_time(s.end_time)}" 
                        for s in sorted(by_day[day], key=lambda s: s.start_time)]
                print(", ".join(times))
        print()
    
    # 겹침 분석
    print("\n" + "=" * 70)
    print("⚠️  시간 겹침 분석")
    print("=" * 70)
    
    result = analyzer.analyze_overlaps(schedules)
    
    if result['overlaps']:
        for overlap_info in result['overlaps']:
            person1 = overlap_info['person1']
            person2 = overlap_info['person2']
            print(f"\n🔗 {person1} ↔ {person2}:")
            
            for overlap in overlap_info['overlapping_times']:
                print(f"   {overlap['day']} {overlap['start']}-{overlap['end']}")
    else:
        print("\n✅ 겹치는 시간이 없습니다!")
    
    # 자유 시간
    print("\n" + "=" * 70)
    print("✨ 모든 사람이 동시에 자유로운 시간 (60분 이상)")
    print("=" * 70)
    
    if result['free_times']:
        total_free_hours = 0
        for day in analyzer.days_order:
            if day in result['free_times']:
                print(f"\n{day}요일:")
                for start_time, end_time in result['free_times'][day]:
                    duration = TimeSlot._minutes_to_time(
                        TimeSlot(day, end_time, end_time)._time_to_minutes(end_time) - 
                        TimeSlot(day, start_time, start_time)._time_to_minutes(start_time)
                    )
                    print(f"   {start_time} - {end_time}")
                    
                    # 시간 계산
                    s_h, s_m = map(int, start_time.split(':'))
                    e_h, e_m = map(int, end_time.split(':'))
                    duration_min = (e_h * 60 + e_m) - (s_h * 60 + s_m)
                    total_free_hours += duration_min
        
        print(f"\n📈 총 자유 시간: {total_free_hours // 60}시간 {total_free_hours % 60}분")
    else:
        print("\n❌ 공통 자유 시간이 없습니다.")
    
    # JSON으로 저장
    output_file = "data/everytime_samples/results/time_analysis.json"
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 분석 결과 저장: {output_file}")
