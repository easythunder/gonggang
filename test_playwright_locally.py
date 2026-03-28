#!/usr/bin/env python3
"""Test Playwright parser locally"""

import asyncio
import sys
sys.path.insert(0, '/Users/jin/Desktop/easy_ing/gonggang')

from src.services.everytime_parser import EverytimeTimetableParser

async def main():
    parser = EverytimeTimetableParser()
    url = "https://everytime.kr/@PbBwfQM2BEWFeCneU6XC"
    
    print(f"Testing Playwright parser with {url}")
    try:
        intervals = parser.parse_from_url(url, timeout_seconds=15)
        print(f"✅ Success! Found {len(intervals)} intervals")
        for day, start, end in intervals[:5]:
            print(f"   Day {day}: {start}-{end}")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
