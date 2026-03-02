#!/usr/bin/env python3
"""Insert test schedule data directly into database."""

import sys
import os
os.chdir('/app')
sys.path.insert(0, '/app')

from datetime import datetime, timedelta
from uuid import uuid4
from src.lib.database import DatabaseManager
from src.models.models import Group, Submission, SubmissionStatus, Interval

# Initialize database
DatabaseManager.init_db()
session = DatabaseManager.get_session()

try:
    # Create test group
    timestamp = datetime.now().isoformat().replace(':', '').replace('.', '')[:-5]
    group_name = f"Test_Group_{timestamp}"
    
    now = datetime.utcnow()
    expires_at = now + timedelta(hours=72)
    admin_token = str(uuid4())
    group_id = uuid4()
    invite_url = f"https://example.com/invite/{group_id}/{admin_token}"
    share_url = f"https://example.com/share/{group_id}"
    
    group = Group(
        id=group_id,
        name=group_name,
        display_unit_minutes=30,
        created_at=now,
        last_activity_at=now,
        expires_at=expires_at,
        admin_token=admin_token,
        invite_url=invite_url,
        share_url=share_url,
        max_participants=50
    )
    session.add(group)
    session.flush()
    
    print(f"✅ Created group: {group_id}")
    
    # Create first submission (User 1)
    sub1 = Submission(
        id=uuid4(),
        group_id=group_id,
        nickname="User 1",
        status=SubmissionStatus.SUCCESS,
        error_reason=None
    )
    session.add(sub1)
    session.flush()
    
    # User 1 schedule: Mon-Fri 9-12, 14-17
    user1_schedule = [
        (0, 540, 720),    # Mon 9:00-12:00
        (0, 840, 1020),   # Mon 14:00-17:00
        (1, 540, 720),    # Tue 9:00-12:00
        (1, 840, 1020),   # Tue 14:00-17:00
        (2, 540, 720),    # Wed 9:00-12:00
        (2, 840, 1020),   # Wed 14:00-17:00
        (3, 540, 720),    # Thu 9:00-12:00
        (3, 840, 1020),   # Thu 14:00-17:00
        (4, 540, 720),    # Fri 9:00-12:00
        (4, 840, 1020),   # Fri 14:00-17:00
    ]
    
    for day, start, end in user1_schedule:
        interval = Interval(
            id=uuid4(),
            submission_id=sub1.id,
            day_of_week=day,
            start_minute=start,
            end_minute=end
        )
        session.add(interval)
    
    session.commit()
    print(f"✅ Added User 1 submission with {len(user1_schedule)} intervals")
    
    # Create second submission (User 2)
    sub2 = Submission(
        id=uuid4(),
        group_id=group_id,
        nickname="User 2",
        status=SubmissionStatus.SUCCESS,
        error_reason=None
    )
    session.add(sub2)
    session.flush()
    
    # User 2 schedule: slightly different times
    user2_schedule = [
        (0, 570, 750),    # Mon 9:30-12:30
        (0, 870, 1050),   # Mon 14:30-17:30
        (1, 600, 780),    # Tue 10:00-13:00
        (1, 900, 1080),   # Tue 15:00-18:00
        (2, 540, 720),    # Wed 9:00-12:00
        (2, 840, 1020),   # Wed 14:00-17:00
        (3, 600, 780),    # Thu 10:00-13:00
        (3, 900, 1080),   # Thu 15:00-18:00
        (4, 540, 720),    # Fri 9:00-12:00
        (4, 840, 1020),   # Fri 14:00-17:00
    ]
    
    for day, start, end in user2_schedule:
        interval = Interval(
            id=uuid4(),
            submission_id=sub2.id,
            day_of_week=day,
            start_minute=start,
            end_minute=end
        )
        session.add(interval)
    
    session.commit()
    print(f"✅ Added User 2 submission with {len(user2_schedule)} intervals")
    
    print(f"\n🎯 GROUP ID: {group_id}")
    
    session.close()
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    session.rollback()
    sys.exit(1)
