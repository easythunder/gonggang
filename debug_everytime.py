#!/usr/bin/env python3
import urllib.request
import urllib.error

url = "https://everytime.kr/@PbBwfQM2BEWFeCneU6XC"

try:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }
    request = urllib.request.Request(url, headers=headers)
    
    with urllib.request.urlopen(request, timeout=5) as response:
        html = response.read().decode("utf-8", errors="ignore")
        
        print(f"✅ HTML fetched successfully ({len(html)} bytes)")
        print("\n📋 First 3000 chars:")
        print(html[:3000])
        print("\n...")
        print(html[-1000:])
        
        # Check for key elements
        print("\n\n🔍 Checking for key elements:")
        print(f"  - 'tablebody' in HTML: {'tablebody' in html}")
        print(f"  - 'subject' in HTML: {'subject' in html}")
        print(f"  - '<table' in HTML: {'<table' in html}")
        print(f"  - 'style=' in HTML: {'style=' in html}")
        print(f"  - 'class=' in HTML: {'class=' in html}")
        
        # Save for inspection
        with open("debug_html.html", "w") as f:
            f.write(html)
        print("\n✅ Saved to debug_html.html")
        
except urllib.error.HTTPError as e:
    print(f"❌ HTTP Error {e.code}: {e.reason}")
except Exception as e:
    print(f"❌ Error: {e}")
