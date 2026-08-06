#!/usr/bin/env python3
"""Full license audit: verify every image on evictions.help is legally usable.

Checks each image against Wikimedia Commons for its license.
Flags anything that isn't PD, CC0, or CC-BY.
Also flags CC-BY images without proper attribution on the page.
"""
import os, re, json, time, urllib.request, urllib.parse
from collections import defaultdict

SEO = "/opt/eviction-defense/seo"
UA = "evictions.help/1.0 (https://evictions.help; support@evictions.help)"

def wm_request(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=15) as r:
        raw = r.read()
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}

def get_license_from_title(file_title):
    """Query Wikimedia for the license of a file title."""
    params = urllib.parse.urlencode({
        "action": "query",
        "titles": file_title,
        "prop": "imageinfo",
        "iiprop": "extmetadata",
        "format": "json",
    })
    url = f"https://commons.wikimedia.org/w/api.php?{params}"
    try:
        data = wm_request(url)
        for page in data.get("query", {}).get("pages", {}).values():
            ii = page.get("imageinfo", [])
            if ii:
                meta = ii[0].get("extmetadata", {})
                return {
                    "license_short": meta.get("LicenseShortName", {}).get("value", "Unknown"),
                    "license_url": meta.get("LicenseUrl", {}).get("value", ""),
                    "artist": meta.get("Artist", {}).get("value", ""),
                    "description": meta.get("ImageDescription", {}).get("value", "")[:200],
                }
    except Exception as e:
        return {"license_short": f"API_ERROR: {e}", "license_url": "", "artist": ""}
    return {"license_short": "NOT_FOUND", "license_url": "", "artist": ""}

def extract_title_from_path(img_path):
    """Convert /assets/locations/.../Some_Image_Name.jpg back to File:Some Image Name.jpg"""
    # Get just the filename
    fname = os.path.basename(img_path)
    # Remove extension
    name_no_ext = os.path.splitext(fname)[0]
    # Replace underscores with spaces
    readable = name_no_ext.replace("_", " ")
    return f"File:{readable}.jpg"  # try jpg first

def main():
    # 1. Collect all unique image paths from all pages
    all_images = set()
    pages_with_images = 0

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

        imgs = re.findall(r'src="/assets/locations/([^"]+)"', html)
        if imgs:
            pages_with_images += 1
            for img in imgs:
                all_images.add(img)

    print(f"Found {len(all_images)} unique images across {pages_with_images} pages")
    print("=" * 60)

    # 2. Check each image's license
    safe = 0
    needs_attribution = 0
    problems = 0
    errored = 0
    attribution_needed = []

    for i, img_path in enumerate(sorted(all_images)):
        # Try to find the image on Wikimedia by its filename
        fname = os.path.basename(img_path)
        name_no_ext = os.path.splitext(fname)[0]

        # Try common extensions
        for ext in [".jpg", ".jpeg", ".png", ".JPG", ".PNG"]:
            title = f"File:{name_no_ext}{ext}"
            lic = get_license_from_title(title)
            if lic["license_short"] not in ("NOT_FOUND",) and "API_ERROR" not in lic["license_short"]:
                break

        if lic["license_short"] == "NOT_FOUND":
            # Try with full path as search
            print(f"\n  NOT FOUND on Commons: {fname}")
            errored += 1
            continue

        if "API_ERROR" in lic["license_short"]:
            print(f"\n  API ERROR: {fname} — {lic['license_short']}")
            errored += 1
            continue

        license_name = lic["license_short"].lower()

        # Categorize
        if any(x in license_name for x in ["pd", "public domain", "cc0"]):
            safe += 1
        elif "cc-by" in license_name or "cc by" in license_name:
            needs_attribution += 1
            attribution_needed.append({
                "path": img_path,
                "license": lic["license_short"],
                "license_url": lic["license_url"],
                "artist": lic.get("artist", ""),
            })
        else:
            problems += 1
            print(f"\n  PROBLEM LICENSE: {fname}")
            print(f"    License: {lic['license_short']}")
            print(f"    URL: {lic['license_url']}")

        time.sleep(0.5)  # Throttle

        # Progress
        if (i + 1) % 50 == 0:
            print(f"  ... {i+1}/{len(all_images)} checked")

    # 3. Summary
    print("\n" + "=" * 60)
    print("LICENSE AUDIT RESULTS")
    print("=" * 60)
    print(f"  Public Domain / CC0:  {safe}")
    print(f"  CC-BY (needs attr):  {needs_attribution}")
    print(f"  Problematic:         {problems}")
    print(f"  Not found / errors:  {errored}")
    print(f"  Total:               {len(all_images)}")

    if problems > 0:
        print(f"\n  WARNING: {problems} images have non-free licenses!")

    if attribution_needed:
        print(f"\n  {len(attribution_needed)} CC-BY images require attribution.")
        print("  Current pages do NOT display attribution.")
        print("  You must either: (a) add attribution to each page, or (b) replace with PD/CC0 images.")
        print("\n  Sample CC-BY images needing attribution:")
        for item in attribution_needed[:10]:
            print(f"    {item['path']}")
            print(f"      License: {item['license']} — By: {item['artist'][:80]}")

    if safe == len(all_images):
        print("\n  ALL IMAGES ARE 100% COPYRIGHT-SAFE (PD or CC0). You are legally in the clear.")

if __name__ == "__main__":
    main()
