#!/bin/bash
# Insert test data directly into database for free time calculation

BASE_URL="http://localhost:8000"

echo "============================================================"
echo "🚀 Direct Free Time Test (Database Insert)"
echo "============================================================"

# Step 1: Create test group
echo ""
echo "🔧 Creating test group..."
TIMESTAMP=$(date +%s%N)
GROUP_NAME="Test_Direct_$TIMESTAMP"

GROUP_RESPONSE=$(curl -s -X POST "$BASE_URL/groups" \
  -H "Content-Type: application/json" \
  -d "{\"group_name\": \"$GROUP_NAME\", \"display_unit_minutes\": 30}")

GROUP_ID=$(echo "$GROUP_RESPONSE" | grep -o '"group_id":"[^"]*' | cut -d'"' -f4)

if [ -z "$GROUP_ID" ]; then
  echo "❌ Failed to create group"
  exit 1
fi

echo "✅ Group created: $GROUP_ID"

# Step 2: Test submitting simple schedule image
# Create a simple test with curl multipart form data
echo ""
echo "📝 Testing with direct DB insertion..."

# We'll use Docker exec to insert test data directly
docker exec gonggang-app python3 << 'PYTHON'
import sys
sys.path.insert(0, '/app')

from datetime import datetime
from uuid import UUID
from src.lib.database import DatabaseManager
from src.models.models import Group, Submission, SubmissionStatus, Interval
from sqlalchemy import text

db = DatabaseManager(
    host="postgres",
    port=5432,
    user="gonggang",
    password="gonggang_dev_password",
    database="gonggang"
)

session = db.get_session()

try:
    # Get the test group from the last created group
    group = session.query(Group).order_by(Group.created_at.desc()).first()
    if not group:
        print("❌ No group found")
        sys.exit(1)
    
    group_id = group.id
    print(f"✅ Using group: {group_id}")
    
    # Create first submission
    sub1 = Submission(
        group_id=group_id,
        nickname="User 1",
        status=SubmissionStatus.SUCCESS,
        ocr_success=True,
        error_reason=None,
    )
    session.add(sub1)
    session.flush()
    
    # Add intervals for User 1 (Mon-Fri: 9-12, 14-17)
    user1_intervals = [
        # Monday: 9-12, 14-17
        (0, 540, 720),    # 9:00-12:00
        (0, 840, 1020),   # 14:00-17:00
        # Tuesday: 9-12, 14-17
        (1, 540, 720),
        (1, 840, 1020),
        # Wednesday: 10-13, 15-18
        (2, 600, 780),    # 10:00-13:00
        (2, 900, 1080),   # 15:00-18:00
        # Thursday: 9-12, 14-17
        (3, 540, 720),
        (3, 840, 1020),
        # Friday: 10-13, 15-18
        (4, 600, 780),
        (4, 900, 1080),
    ]
    
    for day, start, end in user1_intervals:
        interval = Interval(
            submission_id=sub1.id,
            day_of_week=day,
            start_minute=start,
            end_minute=end
        )
        session.add(interval)
    
    session.commit()
    print(f"✅ Added submission for User 1 with {len(user1_intervals)} intervals")
    
    # Create second submission
    sub2 = Submission(
        group_id=group_id,
        nickname="User 2",
        status=SubmissionStatus.SUCCESS,
        ocr_success=True,
        error_reason=None,
    )
    session.add(sub2)
    session.flush()
    
    # Add intervals for User 2 (slightly different: 9:30-12:30, 14:30-17:30)
    user2_intervals = [
        # Monday: 9:30-12:30, 14:30-17:30
        (0, 570, 750),    # 9:30-12:30
        (0, 870, 1050),   # 14:30-17:30
        # Tuesday: 10-13, 15-18
        (1, 600, 780),
        (1, 900, 1080),
        # Wednesday: 9-12, 14-17
        (2, 540, 720),
        (2, 840, 1020),
        # Thursday: 10-13, 15-18
        (3, 600, 780),
        (3, 900, 1080),
        # Friday: 9-12, 14-17
        (4, 540, 720),
        (4, 840, 1020),
    ]
    
    for day, start, end in user2_intervals:
        interval = Interval(
            submission_id=sub2.id,
            day_of_week=day,
            start_minute=start,
            end_minute=end
        )
        session.add(interval)
    
    session.commit()
    print(f"✅ Added submission for User 2 with {len(user2_intervals)} intervals")
    print(f"🎯 Group ID: {group_id}")

except Exception as e:
    print(f"❌ Error: {e}")
    session.rollback()
    import traceback
    traceback.print_exc()
    sys.exit(1)
finally:
    session.close()

PYTHON

echo ""
echo "⏰ Fetching calculated free time..."
sleep 2

# Fetch the group again to get its ID (we need to do this dynamically)
LATEST_GROUP=$(curl -s -X GET "$BASE_URL/health" 2>/dev/null || echo "")

# Get the free time for the latest group
GROUPS_RESPONSE=$(curl -s -X GET "$BASE_URL/groups" 2>/dev/null || echo "{}")

# Alternative: Use the group ID from previous insertion
# For now, get the latest group by direct query
docker exec gonggang-app python3 << 'PYTHON'
import sys
sys.path.insert(0, '/app')

from src.lib.database import DatabaseManager
from src.models.models import Group

db = DatabaseManager(
    host="postgres",
    port=5432,
    user="gonggang",
    password="gonggang_dev_password",
    database="gonggang"
)

session = db.get_session()
group = session.query(Group).order_by(Group.created_at.desc()).first()
if group:
    print(group.id)
session.close()
PYTHON
