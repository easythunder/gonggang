#!/usr/bin/env python3.11
"""End-to-end OCR pipeline test with real API calls."""
import sys
sys.path.insert(0, '/Users/jin/Desktop/gong_gang/gonggang')

import time
import requests
import json
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime

BASE_URL = "http://127.0.0.1:8000"
API_TIMEOUT = 10

def create_schedule_image(text: str) -> bytes:
    """Create a simple schedule image with text."""
    img = Image.new('RGB', (600, 400), color='white')
    draw = ImageDraw.Draw(img)
    
    try:
        font = ImageFont.truetype("/Library/Fonts/Arial.ttf", 18)
    except:
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 18)
        except:
            font = ImageFont.load_default()
    
    y_offset = 50
    for line in text.split('\n'):
        draw.text((40, y_offset), line, fill='black', font=font)
        y_offset += 40
    
    img_bytes = BytesIO()
    img.save(img_bytes, format='PNG')
    return img_bytes.getvalue()


def test_end_to_end():
    """Test complete end-to-end workflow."""
    
    print("=" * 120)
    print("🚀 전체 실행환경 통합 테스트")
    print("=" * 120)
    
    # Test 1: Create a group
    print("\n[1️⃣] 그룹 생성...")
    group_payload = {
        "group_name": f"Integration Test {datetime.now().timestamp()}",
        "display_unit_minutes": 30,
    }
    
    try:
        group_response = requests.post(
            f"{BASE_URL}/groups",
            json=group_payload,
            timeout=API_TIMEOUT
        )
        print(f"  요청: {group_payload}")
        print(f"  상태: {group_response.status_code}")
        
        if group_response.status_code != 201:
            print(f"  ❌ 에러: {group_response.text}")
            return
        
        response_json = group_response.json()
        group_data = response_json.get('data', {})
        group_id = group_data.get('group_id')
        print(f"  ✅ 그룹 생성됨: {group_id}")
        print(f"     응답 데이터: {json.dumps(group_data, indent=2)}")
        
    except Exception as e:
        print(f"  ❌ 네트워크 에러: {e}")
        print(f"  💡 혹시 서버가 실행 중인가요?")
        print(f"     터미널에서 다음을 실행해보세요:")
        print(f"     cd /Users/jin/Desktop/gong_gang/gonggang")
        print(f"     /opt/homebrew/bin/python3.11 -m uvicorn src.main:app --reload")
        return
    
    # Test 2: Submit a schedule
    print("\n[2️⃣] 스케줄 제출...")
    
    schedule_text = """Monday
9:00-10:30
14:00-15:30

Tuesday
10:00-11:30

Wednesday (수)
13:00-14:30"""
    
    image_bytes = create_schedule_image(schedule_text)
    
    files = {
        'image': ('schedule.png', BytesIO(image_bytes), 'image/png')
    }
    form_data = {
        'group_id': group_id,
        'nickname': 'test_user_001'
    }
    
    try:
        submit_response = requests.post(
            f"{BASE_URL}/api/submissions",
            data=form_data,
            files=files,
            timeout=API_TIMEOUT
        )
        
        print(f"  요청 데이터: {form_data}")
        print(f"  상태: {submit_response.status_code}")
        
        if submit_response.status_code != 201:
            print(f"  ❌ 에러: {submit_response.text}")
            return
        
        submission_data = submit_response.json()
        submission_id = submission_data.get('submission_id')
        interval_count = submission_data.get('interval_count', 0)
        
        print(f"  ✅ 스케줄 제출됨: {submission_id}")
        print(f"     추출된 시간대: {interval_count}개")
        print(f"     닉네임: {submission_data.get('nickname')}")
        print(f"     상태: {submission_data.get('status')}")
        print(f"     신뢰도: {submission_data.get('ocr_confidence', 'N/A')}")
        
    except Exception as e:
        print(f"  ❌ 에러: {e}")
        return
    
    # Test 3: List submissions
    print("\n[3️⃣] 제출된 스케줄 목록 조회...")
    
    try:
        list_response = requests.get(
            f"{BASE_URL}/groups/{group_id}/submissions",
            timeout=API_TIMEOUT
        )
        
        print(f"  상태: {list_response.status_code}")
        
        if list_response.status_code != 200:
            print(f"  ❌ 에러: {list_response.text}")
            return
        
        submissions_data = list_response.json()
        submission_list = submissions_data.get('submissions', [])
        
        print(f"  ✅ {len(submission_list)}개의 스케줄 조회됨")
        for sub in submission_list:
            print(f"     - {sub.get('nickname')}: {sub.get('interval_count')}개 시간대")
        
    except Exception as e:
        print(f"  ❌ 에러: {e}")
        return
    
    # Test 4: Get free time (if available)
    print("\n[4️⃣] 자유 시간 계산...")
    
    try:
        free_time_response = requests.get(
            f"{BASE_URL}/groups/{group_id}/free-time",
            timeout=API_TIMEOUT
        )
        
        print(f"  상태: {free_time_response.status_code}")
        
        if free_time_response.status_code == 200:
            free_time_data = free_time_response.json()
            print(f"  ✅ 자유 시간 데이터 조회됨")
            print(f"     응답: {json.dumps(free_time_data, indent=2)[:200]}...")
        else:
            print(f"  ⚠️  상태 {free_time_response.status_code}: 자유 시간 아직 계산 안됨 (정상)")
        
    except Exception as e:
        print(f"  ⚠️  조회 불가: {e}")
    
    # Summary
    print("\n" + "=" * 120)
    print("✅ 통합 테스트 완료!")
    print("=" * 120)
    print("\n📊 테스트 결과:")
    print(f"  ✓ 그룹 생성: 성공")
    print(f"  ✓ 스케줄 제출: 성공 ({interval_count}개 시간대 추출)")
    print(f"  ✓ 제출 목록 조회: 성공 ({len(submission_list)}개 결과)")
    print(f"  ✓ 자유 시간 조회: 시도")
    print("\n🎯 전체 파이프라인 테스트 완료!")


if __name__ == '__main__':
    print("⏳ 서버 연결 확인 중...")
    time.sleep(3)  # 서버 시작 대기
    
    # Check if server is running
    try:
        health = requests.get("http://127.0.0.1:8000/health", timeout=5)
        print(f"✅ 서버 응답: {health.status_code}\n")
    except:
        print("❌ 서버에 연결할 수 없습니다.")
        print("   터미널에서 다음을 실행하세요:")
        print("   cd /Users/jin/Desktop/gong_gang/gonggang && \\\n   /opt/homebrew/bin/python3.11 -m uvicorn src.main:app --reload")
        sys.exit(1)
    
    test_end_to_end()
