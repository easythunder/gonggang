"""Schedule time overlap analysis service.

분석: 여러 사람의 시간표에서 시간 겹침과 공통 자유 시간을 계산합니다.
기반: submissions의 intervals를 사용하여 AND intersection 계산합니다.
"""

import logging
from typing import Dict, List, Tuple, Optional
from uuid import UUID
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class TimeOverlapAnalyzer:
    """시간 겹침 분석기 - Interval 기반"""
    
    def __init__(self, session: Session):
        self.session = session
        self.days_korean = ['월', '화', '수', '목', '금', '토', '일']
        self.days_english = ['MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY', 'SUNDAY']
    
    def analyze_group_overlaps(self, group_id: UUID) -> Dict:
        """그룹의 모든 submission에 대해 시간 겹침 분석.
        
        Args:
            group_id: Group UUID
        
        Returns:
            분석 결과 dict
        """
        try:
            from sqlalchemy import text
            
            # Use raw SQL to avoid model loading issues
            # Get all successful submissions
            result = self.session.execute(
                text("""
                    SELECT id, nickname FROM submissions 
                    WHERE group_id = :group_id::uuid AND status = 'success'
                    ORDER BY nickname
                """),
                {"group_id": str(group_id)}
            )
            submissions = result.fetchall()
            
            if not submissions:
                logger.warning(f"No successful submissions for group {group_id}")
                return {
                    'participants': [],
                    'overlaps': [],
                    'free_times': {}
                }
            
            logger.info(f"Found {len(submissions)} participants for group {group_id}")
            
            # Load intervals for each submission
            participants = []
            for submission_id, nickname in submissions:
                # Get intervals for this submission
                intervals_result = self.session.execute(
                    text("""
                        SELECT day_of_week, start_minute, end_minute
                        FROM intervals
                        WHERE submission_id = :submission_id::uuid
                        ORDER BY day_of_week, start_minute
                    """),
                    {"submission_id": str(submission_id)}
                )
                intervals = intervals_result.fetchall()
                
                # Schedule by day: day_of_week -> [(start_min, end_min), ...]
                schedule_by_day = {}
                for day, start_min, end_min in intervals:
                    if day not in schedule_by_day:
                        schedule_by_day[day] = []
                    schedule_by_day[day].append((start_min, end_min))
                
                participants.append({
                    'nickname': nickname,
                    'schedule_by_day': schedule_by_day
                })
                
                logger.debug(f"{nickname}: {len(intervals)} intervals loaded")
            
            # Find overlaps between pairs
            overlaps = self._find_pairwise_overlaps(participants)
            
            # Find common free times
            free_times = self._find_common_free_times(participants)
            
            # Format result
            return {
                'group_id': str(group_id),
                'participant_count': len(participants),
                'participants': participants,
                'overlaps': overlaps,
                'free_times': free_times
            }
        
        except Exception as e:
            logger.error(f"Analysis failed for group {group_id}: {e}", exc_info=True)
            raise
    
    def _find_pairwise_overlaps(self, participants: List[Dict]) -> List[Dict]:
        """모든 쌍의 겹치는 시간 찾기."""
        overlaps = []
        
        for i, person1 in enumerate(participants):
            for person2 in participants[i+1:]:
                overlapping = self._find_overlaps_between_two(
                    person1['nickname'],
                    person1['schedule_by_day'],
                    person2['nickname'],
                    person2['schedule_by_day']
                )
                
                if overlapping:
                    overlaps.append({
                        'person1': person1['nickname'],
                        'person2': person2['nickname'],
                        'overlapping_times': overlapping
                    })
        
        return overlaps
    
    def _find_overlaps_between_two(self, name1: str, sched1: Dict, name2: str, sched2: Dict) -> List[Dict]:
        """두 사람의 겹치는 시간 찾기."""
        overlapping = []
        
        # All days 0-6
        for day in range(7):
            slots1 = sched1.get(day, [])
            slots2 = sched2.get(day, [])
            
            if not slots1 or not slots2:
                continue
            
            # Find overlapping intervals
            for start1, end1 in slots1:
                for start2, end2 in slots2:
                    # Check overlap
                    overlap_start = max(start1, start2)
                    overlap_end = min(end1, end2)
                    
                    if overlap_start < overlap_end:
                        overlapping.append({
                            'day': day,
                            'day_name': self.days_korean[day],
                            'start_minute': overlap_start,
                            'end_minute': overlap_end,
                            'start_time': self._minutes_to_time(overlap_start),
                            'end_time': self._minutes_to_time(overlap_end),
                            'duration_minutes': overlap_end - overlap_start
                        })
        
        return overlapping
    
    def _find_common_free_times(self, participants: List[Dict]) -> Dict[int, List[Tuple[int, int]]]:
        """모든 사람이 동시에 자유로운 시간 찾기.
        
        AND logic: 모든 사람이 자유로운 시간만 포함
        """
        free_times_by_day = {}
        
        # 시간 범위: 08:00 - 22:00
        start_hour = 8 * 60
        end_hour = 22 * 60
        
        for day in range(7):
            # 모든 사람의 busy intervals을 수집
            busy_slots = []
            
            for person in participants:
                slots = person['schedule_by_day'].get(day, [])
                busy_slots.extend(slots)
            
            # Merge overlapping busy slots
            busy_slots.sort()
            merged_busy = self._merge_intervals(busy_slots)
            
            # Find free intervals
            free_intervals = []
            
            if not merged_busy:
                # 이 요일에 아무도 바쁘지 않으면 전일 자유
                free_intervals.append((start_hour, end_hour))
            else:
                # 첫 수업 전
                if merged_busy[0][0] > start_hour:
                    free_intervals.append((start_hour, merged_busy[0][0]))
                
                # 수업 사이
                for i in range(len(merged_busy) - 1):
                    gap_start = merged_busy[i][1]
                    gap_end = merged_busy[i + 1][0]
                    
                    if gap_end - gap_start >= 30:  # 30분 이상만
                        free_intervals.append((gap_start, gap_end))
                
                # 마지막 수업 후
                if merged_busy[-1][1] < end_hour:
                    free_intervals.append((merged_busy[-1][1], end_hour))
            
            # 60분 이상의 자유 시간만 저장
            long_free_intervals = [
                (start, end)
                for start, end in free_intervals
                if end - start >= 60
            ]
            
            if long_free_intervals:
                free_times_by_day[day] = long_free_intervals
        
        return free_times_by_day
    
    def _merge_intervals(self, intervals: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
        """겹치는 intervals을 merge."""
        if not intervals:
            return []
        
        sorted_intervals = sorted(intervals)
        merged = [sorted_intervals[0]]
        
        for start, end in sorted_intervals[1:]:
            if start <= merged[-1][1]:
                # Overlap or adjacent - merge
                merged[-1] = (merged[-1][0], max(merged[-1][1], end))
            else:
                merged.append((start, end))
        
        return merged
    
    @staticmethod
    def _minutes_to_time(minutes: int) -> str:
        """분을 HH:MM 형식으로 변환."""
        h = minutes // 60
        m = minutes % 60
        return f"{h:02d}:{m:02d}"
    
    def get_human_readable_report(self, analysis: Dict) -> str:
        """분석 결과를 사람이 읽기 쉬운 형식으로 변환."""
        lines = []
        lines.append("=" * 70)
        lines.append("🕐 시간 겹침 분석")
        lines.append("=" * 70)
        
        # 참가자 시간표
        lines.append(f"\n📊 {analysis['participant_count']}명의 참가자\n")
        
        for person in analysis['participants']:
            lines.append(f"👤 {person['nickname']}:")
            
            schedule_by_day = person['schedule_by_day']
            for day in range(7):
                if day in schedule_by_day:
                    times = [
                        f"{self._minutes_to_time(start)}-{self._minutes_to_time(end)}"
                        for start, end in schedule_by_day[day]
                    ]
                    lines.append(f"   {self.days_korean[day]}: {', '.join(times)}")
            lines.append("")
        
        # 겹치는 시간
        if analysis['overlaps']:
            lines.append("⚠️  겹치는 시간")
            lines.append("=" * 70)
            for overlap in analysis['overlaps']:
                lines.append(f"\n🔗 {overlap['person1']} ↔ {overlap['person2']}:")
                for time in overlap['overlapping_times']:
                    lines.append(
                        f"   {self.days_korean[time['day']]} "
                        f"{time['start_time']}-{time['end_time']} "
                        f"({time['duration_minutes']}분)"
                    )
        else:
            lines.append("\n✅ 겹치는 시간이 없습니다!")
        
        # 공통 자유 시간
        lines.append("\n" + "=" * 70)
        lines.append("✨ 모든 사람이 동시에 자유로운 시간 (60분 이상)")
        lines.append("=" * 70)
        
        free_times = analysis['free_times']
        total_minutes = 0
        
        for day in range(7):
            if day in free_times:
                lines.append(f"\n{self.days_korean[day]}요일:")
                for start, end in free_times[day]:
                    lines.append(f"   {self._minutes_to_time(start)} - {self._minutes_to_time(end)}")
                    total_minutes += end - start
        
        if not free_times:
            lines.append("\n❌ 공통 자유 시간이 없습니다.")
        else:
            hours = total_minutes // 60
            mins = total_minutes % 60
            lines.append(f"\n📈 총 자유 시간: {hours}시간 {mins}분")
        
        return "\n".join(lines)
