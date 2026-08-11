#!/usr/bin/env python3
"""
Remove ALL location images from evictions.help SEO pages.

Strips both Markdown-style images (![alt](/assets/locations/...)) and
HTML local-images div blocks from every state, county, and city page.

Usage:
    python3 remove_all_images.py              # all pages
    python3 remove_all_images.py --dry-run    # preview only
    python3 remove_all_images.py --state texas  # one state
"""

import os, sys, re
from argparse import ArgumentParser

SEO_DIR = "/opt/eviction-defense/seo"
SKIP_PREFIXES = ["assets/", "checkout/", "disclaimer/", "privacy/", "terms/"]


def remove_images(html: str) -> tuple[str, int]:
    """Remove all location images. Returns (new_html, count_removed)."""
    removed = 0
    modified = html

    # 1. Remove HTML <div class="local-images"> blocks
    pattern_div = re.compile(
        r'<div class="local-images"[^>]*>.*?</div>\s*</div>',
        re.DOTALL
    )
    matches = pattern_div.findall(modified)
    removed += len(matches)
    modified = pattern_div.sub('', modified)

    # 2. Remove standalone local-images divs (without trailing </div>)
    pattern_standalone = re.compile(
        r'<div class="local-images"[^>]*>.*?</div>',
        re.DOTALL
    )
    matches2 = pattern_standalone.findall(modified)
    removed += len(matches2)
    modified = pattern_standalone.sub('', modified)

    # 3. Remove Markdown-style images pointing to /assets/locations/
    pattern_md = re.compile(
        r'!\[[^\]]*\]\(/assets/locations/[^)]+\)\s*',
        re.MULTILINE
    )
    matches3 = pattern_md.findall(modified)
    removed += len(matches3)
    modified = pattern_md.sub('', modified)

    # 4. Remove any orphaned HTML img tags for location assets
    pattern_img = re.compile(
        r'<img src="/assets/locations/[^"]*"[^>]*>\s*',
    )
    matches4 = pattern_img.findall(modified)
    removed += len(matches4)
    modified = pattern_img.sub('', modified)

    # 5. Clean up: no more than 2 consecutive blank lines
    modified = re.sub(r'\n{3,}', '\n\n', modified)

    # 6. Remove trailing whitespace on each line
    modified = re.sub(r'[ \t]+$', '', modified, flags=re.MULTILINE)

    return modified, removed


def find_pages(limit_state: str | None = None) -> list[str]:
    """Find all SEO index.html pages."""
    pages = []
    for root, dirs, files in os.walk(SEO_DIR):
        if "index.html" not in files:
            continue
        fpath = os.path.join(root, "index.html")
        rel = os.path.relpath(fpath, SEO_DIR)
        if any(rel.startswith(p) for p in SKIP_PREFIXES):
            continue
        if limit_state and not (rel.startswith(limit_state + "/") or
                                rel == limit_state + "/index.html"):
            continue
        pages.append(fpath)
    return sorted(pages)


def main():
    parser = ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--state", help="Process only one state")
    args = parser.parse_args()

    pages = find_pages(args.state)
    print(f"Found {len(pages)} pages\n")

    total_removed = 0
    pages_changed = 0

    for fpath in pages:
        rel = os.path.relpath(fpath, SEO_DIR)
        try:
            html = open(fpath, "r", encoding="utf-8").read()
        except (OSError, UnicodeDecodeError) as e:
            print(f"  SKIP {rel}: {e}")
            continue

        new_html, removed = remove_images(html)

        if removed > 0:
            total_removed += removed
            pages_changed += 1

            if args.dry_run:
                print(f"  WOULD REMOVE {removed} images from {rel}")
            else:
                try:
                    open(fpath, "w", encoding="utf-8").write(new_html)
                    print(f"  OK {rel}: removed {removed} image(s)")
                except OSError as e:
                    print(f"  FAIL {rel}: {e}")

    print(f"\n{'='*60}")
    if args.dry_run:
        print(f"DRY RUN: {pages_changed} pages would be changed, "
              f"{total_removed} images would be removed")
    else:
        print(f"Done. {pages_changed} pages changed, "
              f"{total_removed} images removed.")


if __name__ == "__main__":
    main()
