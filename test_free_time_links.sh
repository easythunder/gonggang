#!/bin/bash
# Test script to add Everytime links to a group and calculate free time

BASE_URL="http://localhost:8000"
API_URL="http://localhost:8000/api"

# Everytime links to test
EVERYTIME_LINK_1="https://everytime.kr/@PbBwfQM2BEWFeCneU6XC"
EVERYTIME_LINK_2="https://everytime.kr/@NVtbegyXowXpgePlKxAI"

NICKNAME_1="User 1"
NICKNAME_2="User 2"

echo "============================================================"
echo "🚀 Everytime Links Free Time Calculator"
echo "============================================================"

# Step 1: Create group with unique name
echo ""
echo "🔧 Creating group..."
TIMESTAMP=$(date +%s%N)
GROUP_NAME="Test_$TIMESTAMP"

GROUP_RESPONSE=$(curl -s -X POST "$BASE_URL/groups" \
  -H "Content-Type: application/json" \
  -d "{\"group_name\": \"$GROUP_NAME\", \"display_unit_minutes\": 30}")

echo "Response: $GROUP_RESPONSE"

GROUP_ID=$(echo "$GROUP_RESPONSE" | grep -o '"group_id":"[^"]*' | cut -d'"' -f4)

if [ -z "$GROUP_ID" ]; then
  echo "❌ Failed to create group"
  exit 1
fi

echo "✅ Group created!"
echo "   Group ID: $GROUP_ID"

# Step 2: Submit Everytime links
echo ""
echo "📝 Submitting schedule for '$NICKNAME_1'..."
SUBMISSION_1=$(curl -s -X POST "$API_URL/submissions/everytime-link" \
  -F "group_id=$GROUP_ID" \
  -F "nickname=$NICKNAME_1" \
  -F "everytime_url=$EVERYTIME_LINK_1")

echo "Response: $SUBMISSION_1"

SUBMISSION_ID_1=$(echo "$SUBMISSION_1" | grep -o '"submission_id":"[^"]*' | cut -d'"' -f4)
if [ ! -z "$SUBMISSION_ID_1" ]; then
  echo "✅ First submission successful! ID: $SUBMISSION_ID_1"
else
  echo "⚠️  First submission response: $SUBMISSION_1"
fi

echo ""
echo "📝 Submitting schedule for '$NICKNAME_2'..."
SUBMISSION_2=$(curl -s -X POST "$API_URL/submissions/everytime-link" \
  -F "group_id=$GROUP_ID" \
  -F "nickname=$NICKNAME_2" \
  -F "everytime_url=$EVERYTIME_LINK_2")

echo "Response: $SUBMISSION_2"

SUBMISSION_ID_2=$(echo "$SUBMISSION_2" | grep -o '"submission_id":"[^"]*' | cut -d'"' -f4)
if [ ! -z "$SUBMISSION_ID_2" ]; then
  echo "✅ Second submission successful! ID: $SUBMISSION_ID_2"
else
  echo "⚠️  Second submission response: $SUBMISSION_2"
fi

# Step 3: Get free time results
echo ""
echo "⏰ Calculating free time for group..."
sleep 1

FREE_TIME=$(curl -s -X GET "$BASE_URL/groups/$GROUP_ID/free-time")

echo "Response: $FREE_TIME"

echo "✅ Free time retrieved!"

# Display free time info
echo ""
echo "📅 Free Time Slots (≥10 minutes):"
echo "$FREE_TIME" | python3 -c "import json, sys; d=json.load(sys.stdin); [print('   ' + s['day'] + ' ' + str(s['start_minute']) + '-' + str(s['end_minute']) + ' (' + str(s['duration_minutes']) + 'min) - ' + str(s['overlap_count']) + ' people') for s in d.get('free_time', [])]" 2>/dev/null || echo "   No slots found"

echo ""
echo "📅 Free Time Slots (≥30 minutes):"
echo "$FREE_TIME" | python3 -c "import json, sys; d=json.load(sys.stdin); [print('   ' + s['day'] + ' ' + str(s['start_minute']) + '-' + str(s['end_minute']) + ' (' + str(s['duration_minutes']) + 'min) - ' + str(s['overlap_count']) + ' people') for s in d.get('free_time_30min', [])]" 2>/dev/null || echo "   No slots found"

echo ""
echo "📅 Free Time Slots (≥60 minutes):"
echo "$FREE_TIME" | python3 -c "import json, sys; d=json.load(sys.stdin); [print('   ' + s['day'] + ' ' + str(s['start_minute']) + '-' + str(s['end_minute']) + ' (' + str(s['duration_minutes']) + 'min) - ' + str(s['overlap_count']) + ' people') for s in d.get('free_time_60min', [])]" 2>/dev/null || echo "   No slots found"

# Save results
OUTPUT_FILE="/tmp/free_time_result_${GROUP_ID}.json"
echo "$FREE_TIME" > "$OUTPUT_FILE"
echo ""
echo "💾 Results saved to $OUTPUT_FILE"

echo ""
echo "============================================================"
echo "✨ Test complete! Group ID: $GROUP_ID"
echo "============================================================"
