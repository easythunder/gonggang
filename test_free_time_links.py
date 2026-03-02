#!/usr/bin/env python3
"""Test script to add Everytime links to a group and calculate free time."""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000/api"
GROUPS_URL = "http://localhost:8000/groups"

# Everytime links to test
EVERYTIME_LINKS = [
    "https://everytime.kr/@PbBwfQM2BEWFeCneU6XC",
    "https://everytime.kr/@NVtbegyXowXpgePlKxAI",
]

NICKNAMES = ["User 1", "User 2"]


def create_group(group_name: str = None, display_unit: int = 30) -> dict:
    """Create a new group."""
    print(f"\n🔧 Creating group...")
    payload = {
        "group_name": group_name,
        "display_unit_minutes": display_unit,
    }
    
    response = requests.post(f"{GROUPS_URL}", json=payload)
    print(f"Status: {response.status_code}")
    
    if response.status_code != 201:
        print(f"Error: {response.text}")
        return None
    
    data = response.json()
    print(f"✅ Group created!")
    print(f"   Group ID: {data['group_id']}")
    print(f"   Group Name: {data['group_name']}")
    print(f"   Invite URL: {data['invite_url']}")
    
    return data


def submit_everytime_link(group_id: str, nickname: str, everytime_url: str) -> dict:
    """Submit schedule via Everytime link."""
    print(f"\n📝 Submitting schedule for '{nickname}' from {everytime_url}")
    
    payload = {
        "group_id": group_id,
        "nickname": nickname,
        "everytime_url": everytime_url,
    }
    
    response = requests.post(f"{BASE_URL}/submissions/everytime-link", data=payload)
    print(f"Status: {response.status_code}")
    
    if response.status_code not in [200, 201]:
        print(f"Error: {response.text}")
        return None
    
    data = response.json()
    print(f"✅ Submission successful!")
    print(f"   Submission ID: {data.get('submission_id')}")
    print(f"   Intervals: {data.get('interval_count', 'N/A')}")
    
    return data


def get_free_time(group_id: str) -> dict:
    """Get free time results for the group."""
    print(f"\n⏰ Calculating free time for group {group_id}...")
    
    response = requests.get(f"{GROUPS_URL}/{group_id}/free-time")
    print(f"Status: {response.status_code}")
    
    if response.status_code == 410:
        print("❌ Group has expired")
        return None
    
    if response.status_code != 200:
        print(f"Error: {response.text}")
        return None
    
    data = response.json()
    print(f"✅ Free time calculated!")
    print(f"   Participants: {data['participant_count']}")
    print(f"   Computed at: {data.get('computed_at', 'N/A')}")
    
    # Display free time slots
    print("\n📅 Free Time Slots (≥10 minutes):")
    if data['free_time']:
        for slot in data['free_time']:
            print(f"   {slot['day']:9} {slot['start_minute']:4d}-{slot['end_minute']:4d} ({slot['duration_minutes']:3d}min) - {slot['overlap_count']} people")
    else:
        print("   No common free time found")
    
    # Display 30-min slots
    print("\n📅 Free Time Slots (≥30 minutes):")
    if data['free_time_30min']:
        for slot in data['free_time_30min']:
            print(f"   {slot['day']:9} {slot['start_minute']:4d}-{slot['end_minute']:4d} ({slot['duration_minutes']:3d}min) - {slot['overlap_count']} people")
    else:
        print("   No common free time found")
    
    # Display 60-min slots
    print("\n📅 Free Time Slots (≥60 minutes):")
    if data['free_time_60min']:
        for slot in data['free_time_60min']:
            print(f"   {slot['day']:9} {slot['start_minute']:4d}-{slot['end_minute']:4d} ({slot['duration_minutes']:3d}min) - {slot['overlap_count']} people")
    else:
        print("   No common free time found")
    
    return data


def main():
    """Main execution flow."""
    print("=" * 60)
    print("🚀 Everytime Links Free Time Calculator")
    print("=" * 60)
    
    # Step 1: Create group
    group = create_group(group_name="Everytime Test Group")
    if not group:
        print("❌ Failed to create group")
        return
    
    group_id = group['group_id']
    
    # Step 2: Submit Everytime links
    submissions = []
    for nickname, everytime_url in zip(NICKNAMES, EVERYTIME_LINKS):
        submission = submit_everytime_link(group_id, nickname, everytime_url)
        if submission:
            submissions.append(submission)
    
    if len(submissions) == 0:
        print("❌ No submissions succeeded")
        return
    
    print(f"\n✅ {len(submissions)} submission(s) succeeded")
    
    # Step 3: Get free time results
    free_time = get_free_time(group_id)
    
    if free_time:
        # Save results to file
        output_file = f"/tmp/free_time_result_{group_id}.json"
        with open(output_file, 'w') as f:
            json.dump(free_time, f, indent=2)
        print(f"\n💾 Results saved to {output_file}")
    
    print("\n" + "=" * 60)
    print("✨ Test complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
