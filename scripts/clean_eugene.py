#!/usr/bin/env python3
"""Remove Seattle image from Eugene page - approach: find and remove the first local-images
div that contains the Seattle image."""
import re

path = "/opt/eviction-defense/seo/oregon/lane-county/eugene/index.html"

try:
    html = open(path).read()
except FileNotFoundError:
    print("File not found")
    exit(1)

# Find the first local-images div with single column (contains Seattle)
start = html.find('<div class="local-images" style="display:grid;grid-template-columns:1fr;')
if start < 0:
    start = html.find('<div class="local-images" style="display:grid;grid-template-columns:1fr')

if start >= 0:
    # Find the NEXT local-images div start (this is the good one)
    next_local = html.find('<div class="local-images"', start + 50)
    if next_local > 0:
        html = html[:start] + html[next_local:]
        print("Removed first local-images div")
    else:
        print("Could not find next local-images div")

if "Seattle" in html:
    print("FAILED: Seattle still in page")
else:
    print("SUCCESS: Seattle removed")

try:
    open(path, "w").write(html)
    imgs = len(re.findall(r'src="/assets/locations/', open(path).read()))
    print(f"{imgs} location images remain on page")
except OSError:
    print("Write error")
