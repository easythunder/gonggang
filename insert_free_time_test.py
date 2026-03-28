#!/usr/bin/env python3
"""Insert test schedule data with clear free time overlap."""

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
    group_name = f"FreeTim_Test_{timestamp}"
    
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
    # Busy times: 8-9, 12-14, 17-18
    # Free times: 9-12, 14-17, 18-22
    sub1 = Submission(
        id=uuid4(),
        group_id=group_id,
        nickname="Alice",
        status=SubmissionStatus.SUCCESS,
        error_reason=None
    )
    session.add(sub1)
    session.flush()
    
    # User 1 busy schedule (inverse of free time)
    user1_busy = [
        (0, 480, 540),    # Mon 8:00-9:00 BUSY
        (0, 720, 840),    # Mon 12:00-14:00 BUSY
        (0, 1020, 1080),  # Mon 17:00-18:00 BUSY
        (1, 480, 540),    # Tue 8:00-9:00 BUSY
        (1, 720, 840),    # Tue 12:00-14:00 BUSY
        (1, 1020, 1080),  # Tue 17:00-18:00 BUSY
        (2, 480, 540),    # Wed 8:00-9:00 BUSY
        (2, 720, 840),    # Wed 12:00-14:00 BUSY
        (2, 1020, 1080),  # Wed 17:00-18:00 BUSY
        (3, 480, 540),    # Thu 8:00-9:00 BUSY
        (3, 720, 840),    # Thu 12:00-14:00 BUSY
        (3, 1020, 1080),  # Thu 17:00-18:00 BUSY
        (4, 480, 540),    # Fri 8:00-9:00 BUSY
        (4, 720, 840),    # Fri 12:00-14:00 BUSY
        (4, 1020, 1080),  # Fri 17:00-18:00 BUSY
    ]
    
    # Convert to intervals (store busy times, system will invert to free times)
    for day, start, end in user1_busy:
        interval = Interval(
            id=uuid4(),
            submission_id=sub1.id,
            day_of_week=day,
            start_minute=start,
            end_minute=end
        )
        session.add(interval)
    
    session.commit()
    print(f"✅ Added User 1 (Alice) submission with {len(user1_busy)} busy intervals")
    
    # Create second submission (User 2)
    # Busy times: 8-9, 12-14, 17-18 (same as User 1 to ensure overlap!)
    sub2 = Submission(
        id=uuid4(),
        group_id=group_id,
        nickname="Bob",
        status=SubmissionStatus.SUCCESS,
        error_reason=None
    )
    session.add(sub2)
    session.flush()
    
    # User 2 busy schedule (SAME as User 1 for clear overlap)
    user2_busy = [
        (0, 480, 540),    # Mon 8:00-9:00 BUSY
        (0, 720, 840),    # Mon 12:00-14:00 BUSY
        (0, 1020, 1080),  # Mon 17:00-18:00 BUSY
        (1, 480, 540),    # Tue 8:00-9:00 BUSY
        (1, 720, 840),    # Tue 12:00-14:00 BUSY
        (1, 1020, 1080),  # Tue 17:00-18:00 BUSY
        (2, 480, 540),    # Wed 8:00-9:00 BUSY
        (2, 720, 840),    # Wed 12:00-14:00 BUSY
        (2, 1020, 1080),  # Wed 17:00-18:00 BUSY
        (3, 480, 540),    # Thu 8:00-9:00 BUSY
        (3, 720, 840),    # Thu 12:00-14:00 BUSY
        (3, 1020, 1080),  # Thu 17:00-18:00 BUSY
        (4, 480, 540),    # Fri 8:00-9:00 BUSY
        (4, 720, 840),    # Fri 12:00-14:00 BUSY
        (4, 1020, 1080),  # Fri 17:00-18:00 BUSY
    ]
    
    for day, start, end in user2_busy:
        interval = Interval(
            id=uuid4(),
            submission_id=sub2.id,
            day_of_week=day,
            start_minute=start,
            end_minute=end
        )
        session.add(interval)
    
    session.commit()
    print(f"✅ Added User 2 (Bob) submission with {len(user2_busy)} busy intervals")
    
    print(f"\n🎯 GROUP ID: {group_id}")
    print(f"📅 Common free times:")
    print(f"   Mon-Fri 9:00-12:00 (3 hours)")
    print(f"   Mon-Fri 14:00-17:00 (3 hours)")
    print(f"   Mon-Fri 18:00-24:00 (6 hours)")
    
    session.close()
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    session.rollback()
    sys.exit(1)
