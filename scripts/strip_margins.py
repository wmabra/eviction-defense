#!/usr/bin/env python3
"""Strip inline margins from local-images divs so CSS centering works."""
import os, re

SEO = "/opt/eviction-defense/seo"
count = 0

for root, dirs, files in os.walk(SEO):
    if "index.html" not in files:
        continue
    fpath = os.path.join(root, "index.html")
    rel = os.path.relpath(fpath, SEO)
    if rel.startswith(("assets/", "checkout/")):
        continue
    try:
        html = open(fpath).read()
    except Exception:
        continue
    if "local-images" not in html:
        continue

    # Remove inline margin from local-images div (both with and without trailing semicolon)
    for variant in ["margin:24px 0;", "margin:24px 0\"", "margin:24px 0 "]:
        if variant in html:
            html = html.replace(variant, "\"" if "\"" in variant else "")
            html = html.replace(";;", ";")
            modified = True

print(f"Stripped inline margins from {count} pages")
