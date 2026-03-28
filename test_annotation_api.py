#!/usr/bin/env python3
"""
annotation 데이터를 DB에 submissions + intervals로 저장하고 분석하는 스크립트
"""

import json
from pathlib import Path
from uuid import uuid4
from src.lib.database import db_manager
from src.models.models import Group, Submission, Interval, SubmissionStatus
from src.services.schedule_analyzer import TimeOverlapAnalyzer
from datetime import datetime, timezone

# Initialize DB
db_manager.init_db()

# Test group ID (임시)
TEST_GROUP_ID = uuid4()

print("=" * 70)
print("📋 Annotation Data → DB 저장")
print("=" * 70)

db = db_manager.get_session()

try:
    # 1. Create a test group
    test_group = Group(
        id=TEST_GROUP_ID,
        group_name="Annotation Test Group",
        creator_name="System",
        display_unit_minutes=30,
        expires_at=datetime.now(timezone.utc).replace(tzinfo=timezone.utc)
    )
    db.add(test_group)
    db.commit()
    
    print(f"\n✅ Test group created: {TEST_GROUP_ID}")
    
    # 2. Load annotations and create submissions
    annotation_dir = Path("data/everytime_samples/annotations")
    annotation_files = sorted(annotation_dir.glob("IMG_*.json"))
    
    print(f"\n📂 Found {len(annotation_files)} annotation files")
    
    submission_count = 0
    interval_count = 0
    
    for ann_file in annotation_files:
        try:
            with open(ann_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            image_name = ann_file.stem
            nickname = image_name
            schedule = data.get('schedule', [])
            
            if not schedule:
                print(f"⚠️  {image_name}: No schedule data")
                continue
            
            # Create submission
            submission = Submission(
                id=uuid4(),
                group_id=TEST_GROUP_ID,
                nickname=nickname,
                status=SubmissionStatus.SUCCESS,
                submitted_at=datetime.now(timezone.utc)
            )
            db.add(submission)
            db.flush()  # Get submission ID
            
            print(f"\n👤 {nickname}:")
            
            # Convert schedule to intervals
            for entry in schedule:
                day_name = entry.get('day', '')
                start_str = entry.get('start', '')
                end_str = entry.get('end', '')
                
                # Convert Korean day to 0-6
                days_korean = {'월': 0, '화': 1, '수': 2, '목': 3, '금': 4, '토': 5, '일': 6}
                day_of_week = days_korean.get(day_name, 0)
                
                # Convert HH:MM to minutes
                try:
                    start_h, start_m = map(int, start_str.split(':'))
                    end_h, end_m = map(int, end_str.split(':'))
                    start_minute = start_h * 60 + start_m
                    end_minute = end_h * 60 + end_m
                except:
                    print(f"   ⚠️  잘못된 시간 형식: {start_str}-{end_str}")
                    continue
                
                # Create interval
                interval = Interval(
                    id=uuid4(),
                    submission_id=submission.id,
                    day_of_week=day_of_week,
                    start_minute=start_minute,
                    end_minute=end_minute
                )
                db.add(interval)
                interval_count += 1
                
                print(f"   {day_name} {start_str}-{end_str} (day={day_of_week}, {start_minute}-{end_minute} min)")
            
            submission_count += 1
        
        except Exception as e:
            print(f"❌ Error processing {ann_file}: {e}")
    
    db.commit()
    
    print(f"\n✅ Created {submission_count} submissions with {interval_count} intervals")
    
    # 3. Analyze overlaps
    print("\n" + "=" * 70)
    print("🔍 시간 겹침 분석")
    print("=" * 70)
    
    analyzer = TimeOverlapAnalyzer(db)
    analysis = analyzer.analyze_group_overlaps(TEST_GROUP_ID)
    summary = analyzer.get_human_readable_report(analysis)
    
    print(summary)
    
    # 4. Show API endpoint
    print("\n" + "=" * 70)
    print("🌐 API 끝점")
    print("=" * 70)
    print(f"""
✅ 시간 겹침 분석 API가 준비되었습니다!

📍 엔드포인트:
  - GET /analysis/groups/{TEST_GROUP_ID}/overlaps
    (JSON 응답, 상세 분석)
  
  - GET /analysis/groups/{TEST_GROUP_ID}/overlaps/summary
    (Plain text 응답, 가독성 좋음)

테스트 명령:
  curl http://localhost:8000/analysis/groups/{TEST_GROUP_ID}/overlaps | python -m json.tool
  
  또는:
  
  curl http://localhost:8000/analysis/groups/{TEST_GROUP_ID}/overlaps/summary
    """)

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    db_manager.close_session(db)
