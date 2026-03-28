#!/usr/bin/env python3
"""Comprehensive test of OCR and free-time calculation."""

import subprocess
import json
import time

BASE_URL = "http://localhost:8000"

def run_curl(method, url, data=None, files=None):
    """Run curl command and return JSON response."""
    cmd = ["curl", "-s", "-X", method, url]
    
    if method == "POST" and data:
        cmd.extend(["-H", "Content-Type: application/json", "-d", json.dumps(data)])
    
    if files:
        for key, filepath in files.items():
            cmd.extend(["-F", f"{key}=@{filepath}"])
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return json.loads(result.stdout)
    except:
        return {"error": result.stdout, "stderr": result.stderr}

def main():
    print("=" * 70)
    print("🧪 Comprehensive OCR & Free-Time Calculation Test")
    print("=" * 70)
    
    # Step 1: Create Group
    print("\n📋 Step 1: Create Group")
    print("-" * 70)
    group_response = run_curl(
        "POST",
        f"{BASE_URL}/groups",
        data={
            "group_name": "Comprehensive OCR Test",
            "display_unit_minutes": 30
        }
    )
    
    if "error" in group_response:
        print(f"❌ Failed to create group: {group_response['error']}")
        return
    
    group_id = group_response['data']['group_id']
    print(f"✅ Group created: {group_id}")
    print(f"   Name: {group_response['data']['group_name']}")
    print(f"   Expires: {group_response['data']['expires_at']}")
    
    # Step 2: Submit multiple images
    print("\n📸 Step 2: Submit Schedule Images")
    print("-" * 70)
    
    test_images = [
        ("User 1", "/Users/jin/Desktop/easy_ing/gonggang/data/everytime_samples/images/IMG_2777.PNG"),
        ("User 2", "/Users/jin/Desktop/easy_ing/gonggang/data/everytime_samples/images/IMG_2778.PNG"),
        ("User 3", "/Users/jin/Desktop/easy_ing/gonggang/data/everytime_samples/images/IMG_2779.PNG"),
        ("User 4", "/Users/jin/Desktop/easy_ing/gonggang/data/everytime_samples/images/IMG_2780.PNG"),
    ]
    
    submissions = []
    for nickname, image_path in test_images:
        print(f"\n  📤 Submitting {nickname}...")
        
        cmd = [
            "curl", "-s", "-X", "POST",
            f"{BASE_URL}/api/submissions",
            "-F", f"group_id={group_id}",
            "-F", f"nickname={nickname}",
            "-F", f"image=@{image_path}"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        try:
            response = json.loads(result.stdout)
            
            if "error" in response or "detail" in response:
                print(f"    ❌ Error: {response.get('error') or response.get('detail')}")
            else:
                submissions.append(response)
                print(f"    ✅ Submission ID: {response['submission_id']}")
                print(f"       Status: {response['status']}")
                print(f"       Intervals: {response['interval_count']}")
        except:
            print(f"    ❌ Parse error: {result.stdout[:100]}")
        
        time.sleep(1)  # Small delay between submissions
    
    print(f"\n✅ Submitted {len(submissions)}/{len(test_images)} images successfully")
    
    # Step 3: Wait for calculation
    print("\n⏳ Step 3: Wait for Calculation (5 seconds...)")
    print("-" * 70)
    time.sleep(5)
    
    # Step 4: Get free-time results
    print("\n📊 Step 4: Get Free-Time Results")
    print("-" * 70)
    
    cmd = ["curl", "-s", "-X", "GET", f"{BASE_URL}/groups/{group_id}/free-time"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    try:
        free_time_response = json.loads(result.stdout)
        
        print(f"✅ Group: {free_time_response['group_name']}")
        print(f"   Participants: {free_time_response['participant_count']}")
        print(f"   Computed at: {free_time_response['computed_at']}")
        print(f"   Version: {free_time_response['version']}")
        
        print(f"\n   Participants:")
        for p in free_time_response['participants']:
            print(f"     - {p['nickname']}: {p['submitted_at']}")
        
        # Display free time slots
        print(f"\n   Free Time Slots (≥10 min):")
        if free_time_response['free_time']:
            for slot in free_time_response['free_time'][:10]:
                print(f"     - {slot['day']:9} {slot['start_minute']:4d}-{slot['end_minute']:4d} "
                      f"({slot['duration_minutes']:3d}min) - {slot['overlap_count']} people")
        else:
            print(f"     (No common free time)")
        
        # Display 30-min slots
        print(f"\n   Free Time Slots (≥30 min):")
        if free_time_response['free_time_30min']:
            for slot in free_time_response['free_time_30min'][:10]:
                print(f"     - {slot['day']:9} {slot['start_minute']:4d}-{slot['end_minute']:4d} "
                      f"({slot['duration_minutes']:3d}min) - {slot['overlap_count']} people")
        else:
            print(f"     (No common free time ≥30 min)")
        
        # Display 60-min slots
        print(f"\n   Free Time Slots (≥60 min):")
        if free_time_response['free_time_60min']:
            for slot in free_time_response['free_time_60min'][:10]:
                print(f"     - {slot['day']:9} {slot['start_minute']:4d}-{slot['end_minute']:4d} "
                      f"({slot['duration_minutes']:3d}min) - {slot['overlap_count']} people")
        else:
            print(f"     (No common free time ≥60 min)")
        
    except Exception as e:
        print(f"❌ Error parsing response: {e}")
        print(f"   Response: {result.stdout[:200]}")
    
    # Step 5: Summary
    print("\n" + "=" * 70)
    print("✨ Test Summary")
    print("=" * 70)
    print(f"Group ID: {group_id}")
    print(f"Submissions: {len(submissions)}/{len(test_images)}")
    print(f"Status: {'✅ PASS' if len(submissions) > 0 else '❌ FAIL'}")
    print("=" * 70)

if __name__ == "__main__":
    main()
