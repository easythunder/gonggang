#!/usr/bin/env python3
"""Test Playwright rendering in Docker"""
import subprocess
import sys
import tempfile
import os

PLAYWRIGHT_HELPER = """
import asyncio
import sys
from playwright.async_api import async_playwright

async def fetch_rendered_html(url, timeout_seconds):
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-dev-shm-usage',
            ]
        )
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36'
        )
        page = await context.new_page()
        
        await page.set_extra_http_headers({
            'Accept-Language': 'ko-KR,ko;q=0.9',
            'Referer': 'https://everytime.kr/',
        })
        
        try:
            await page.goto(url, timeout=timeout_seconds*1000, wait_until='domcontentloaded')
            
            try:
                await page.wait_for_selector('div.subject', timeout=5000)
            except:
                pass
            
            await page.wait_for_timeout(2000)
            
            html = await page.content()
            return html
        finally:
            await browser.close()

if __name__ == "__main__":
    url = sys.argv[1]
    timeout = int(sys.argv[2])
    html = asyncio.run(fetch_rendered_html(url, timeout))
    print(html)
"""

url = "https://everytime.kr/@PbBwfQM2BEWFeCneU6XC"

with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
    f.write(PLAYWRIGHT_HELPER)
    script_path = f.name

try:
    print(f"🎬 Running advanced Playwright script with bot detection avoidance...")
    result = subprocess.run(
        [sys.executable, script_path, url, "15"],
        capture_output=True,
        text=True,
        timeout=25
    )
    print(f"Return code: {result.returncode}")
    if result.stderr:
        print(f"\n❌ STDERR (first 2000 chars):\n{result.stderr[:2000]}")
    if result.stdout:
        print(f"\n✅ STDOUT length: {len(result.stdout)} bytes")
        print(f"First 1500 chars:\n{result.stdout[:1500]}")
        if 'subject' in result.stdout:
            print("\n✨ Found 'subject' in output!")
        if '비정상 접근' in result.stdout or 'abnormal' in result.stdout:
            print("\n⚠️ Still getting bot detection block")
finally:
    os.unlink(script_path)

