#!/usr/bin/env python3
"""Asset Versioning Tool for evictions.help.

Computes content hashes (SHA-256) of static assets (site.js, styles.css)
and synchronizes version tags (?v=<hash>) across all HTML files.

Usage:
    python3 scripts/version_assets.py [--check] [--dir /path/to/seo]
"""

import argparse
import hashlib
import os
import re
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_file_hash(filepath: str, length: int = 10) -> str:
    """Compute sha256 content hash of a file."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()[:length]


def version_assets(
    seo_dir: str,
    assets_dir: str,
    check_only: bool = False,
    sync_source_js: str | None = None,
) -> tuple[int, dict[str, str]]:
    """Version assets and update HTML references."""
    # If source seo-site.js exists, copy it to assets_dir/site.js first
    if sync_source_js and os.path.isfile(sync_source_js):
        target_js = os.path.join(assets_dir, "site.js")
        if os.path.abspath(sync_source_js) != os.path.abspath(target_js):
            with open(sync_source_js, "r", encoding="utf-8") as f_src:
                src_content = f_src.read()
            with open(target_js, "w", encoding="utf-8") as f_dst:
                f_dst.write(src_content)
            print(f"Synced source {sync_source_js} -> {target_js}")

    site_js_path = os.path.join(assets_dir, "site.js")
    styles_css_path = os.path.join(assets_dir, "styles.css")

    if not os.path.isfile(site_js_path):
        raise FileNotFoundError(f"Missing {site_js_path}")
    if not os.path.isfile(styles_css_path):
        raise FileNotFoundError(f"Missing {styles_css_path}")

    js_hash = get_file_hash(site_js_path)
    css_hash = get_file_hash(styles_css_path)

    hashes = {"site.js": js_hash, "styles.css": css_hash}
    print(f"Computed Asset Hashes:")
    print(f"  site.js    -> {js_hash} (sha256:10)")
    print(f"  styles.css -> {css_hash} (sha256:10)")

    js_pattern = re.compile(r'/assets/site\.js(\?v=[^\s"\'<>]*)?')
    css_pattern = re.compile(r'/assets/styles\.css(\?v=[^\s"\'<>]*)?')

    new_js_ref = f"/assets/site.js?v={js_hash}"
    new_css_ref = f"/assets/styles.css?v={css_hash}"

    updated_count = 0
    stale_count = 0

    for root, _, files in os.walk(seo_dir):
        for f in files:
            if not f.endswith(".html") or f.endswith(".bak"):
                continue
            path = os.path.join(root, f)
            try:
                with open(path, "r", encoding="utf-8") as fp:
                    content = fp.read()
            except Exception as e:
                print(f"Warning reading {path}: {e}", file=sys.stderr)
                continue

            new_content = js_pattern.sub(new_js_ref, content)
            new_content = css_pattern.sub(new_css_ref, new_content)

            if new_content != content:
                stale_count += 1
                if not check_only:
                    with open(path, "w", encoding="utf-8") as fp:
                        fp.write(new_content)
                    updated_count += 1

    if check_only:
        print(f"Check completed: {stale_count} HTML files need version updates.")
    else:
        print(f"Successfully updated {updated_count} HTML files to current asset hashes.")

    return updated_count, hashes


def main():
    parser = argparse.ArgumentParser(description="Asset Versioning for evictions.help")
    parser.add_argument(
        "--dir",
        default="/opt/eviction-defense/seo" if os.path.isdir("/opt/eviction-defense/seo") else os.path.join(BASE_DIR, "seo"),
        help="SEO directory containing HTML files",
    )
    parser.add_argument(
        "--assets",
        default=None,
        help="Directory containing site.js and styles.css (defaults to <dir>/assets)",
    )
    parser.add_argument(
        "--sync-js",
        default=os.path.join(BASE_DIR, "seo-site.js"),
        help="Path to source seo-site.js to sync into assets/site.js",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check only without writing changes",
    )

    args = parser.parse_args()
    assets_dir = args.assets or os.path.join(args.dir, "assets")

    if not os.path.isdir(args.dir):
        print(f"Error: Directory not found: {args.dir}", file=sys.stderr)
        sys.exit(1)
    if not os.path.isdir(assets_dir):
        print(f"Error: Assets directory not found: {assets_dir}", file=sys.stderr)
        sys.exit(1)

    sync_js = args.sync_js if os.path.isfile(args.sync_js) else None
    version_assets(args.dir, assets_dir, check_only=args.check, sync_source_js=sync_js)


if __name__ == "__main__":
    main()
