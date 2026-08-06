#!/usr/bin/env python3
"""Remove all broken image references from SEO pages.

For every page, scan img tags pointing to /assets/locations/,
check if the file exists on disk, and remove broken references.
Also remove orphaned img-cell divs and fix column counts.
"""
import os, re, sys

SEO_DIR = "/opt/eviction-defense/seo"

def fix_page(fpath):
    """Fix one page: remove broken images, fix layout."""
    try:
        html = open(fpath).read()
    except (FileNotFoundError, OSError):
        return False, "read error"

    original = html
    removed = 0

    # Find all img tags pointing to location assets
    imgs = re.findall(
        r'(<div class="img-cell">\s*<img src="(/assets/locations/[^"]+)"[^>]*></div>)',
        html, re.DOTALL
    )

    for full_tag, img_path in imgs:
        disk_path = os.path.join(SEO_DIR, img_path.lstrip("/"))
        if not os.path.exists(disk_path):
            html = html.replace(full_tag, "", 1)
            removed += 1

    if removed == 0:
        return False, "no changes needed"

    # Fix: if we removed images and now local-images div has wrong column count
    # Count remaining images in each local-images div
    def fix_columns(m):
        div_content = m.group(0)
        remaining = div_content.count('<div class="img-cell">')
        if remaining == 0:
            return ""  # Remove empty local-images div
        elif remaining == 1:
            return div_content.replace("1fr 1fr", "1fr", 1)
        return div_content

    html = re.sub(
        r'<div class="local-images"[^>]*>.*?</div>',
        fix_columns,
        html,
        flags=re.DOTALL
    )

    # Clean up: remove empty local-images divs, fix double spaces
    html = re.sub(r'<div class="local-images"[^>]*>\s*</div>', '', html)
    html = re.sub(r'\n{3,}', '\n\n', html)

    if html == original:
        return False, "no changes after cleanup"

    try:
        open(fpath, "w").write(html)
    except OSError:
        return False, "write error"

    return True, f"removed {removed} broken images"

def main():
    pages_fixed = 0
    total_removed = 0

    for root, dirs, files in os.walk(SEO_DIR):
        if "index.html" not in files:
            continue
        fpath = os.path.join(root, "index.html")
        rel = os.path.relpath(fpath, SEO_DIR)
        if rel.startswith(("assets/", "checkout/", "disclaimer/", "privacy/", "terms/")):
            continue

        ok, msg = fix_page(fpath)
        if ok:
            pages_fixed += 1
            try:
                removed = int(msg.split()[-2]) if "removed" in msg else 0
            except (ValueError, IndexError):
                removed = 0
            total_removed += removed
            print(f"  FIXED: {rel} ({msg})")

    print(f"\nDone. Fixed {pages_fixed} pages, removed {total_removed} broken image references.")

if __name__ == "__main__":
    main()
