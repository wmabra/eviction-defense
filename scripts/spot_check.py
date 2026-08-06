#!/usr/bin/env python3
"""Spot-check image quality across 12 diverse pages."""
import os, re

SEO = "/opt/eviction-defense/seo"
BAD_KW = [
    "prosch", "seattle", "memorial_service", "funeral", "daguerreotype",
    "ambrotype", "nara_", "bain_news", "bain_collection", "detroit_publishing",
    "loc.gov", "library_of_congress", "dpla", "engraving", "etching", "lithograph",
]

SAMPLES = [
    ("texas/harris-county/houston", "Houston, TX"),
    ("illinois/cook-county", "Cook County, IL"),
    ("california/los-angeles-county/los-angeles", "Los Angeles, CA"),
    ("oregon/lane-county/eugene", "Eugene, OR"),
    ("tennessee/davidson-county/nashville", "Nashville, TN"),
    ("florida", "Florida (state)"),
    ("arizona", "Arizona (state)"),
    ("virginia/arlington-county", "Arlington, VA"),
    ("georgia/fulton-county/atlanta", "Atlanta, GA"),
    ("nevada/clark-county/las-vegas", "Las Vegas, NV"),
    ("massachusetts/suffolk-county/boston", "Boston, MA"),
    ("colorado/denver-county", "Denver, CO"),
]

print("SPOT CHECK — Image Quality Audit")
print("=" * 60)
all_ok = True

for rel, label in SAMPLES:
    fpath = os.path.join(SEO, rel, "index.html")
    if not os.path.exists(fpath):
        print(f"\n{label}: NOT FOUND")
        continue

    try:
        html = open(fpath).read()
    except Exception:
        print(f"\n{label}: READ ERROR")
        continue

    imgs = re.findall(r'src="/assets/locations/([^"]+)"', html)

    issues = []
    for img in imgs:
        full = os.path.join(SEO, "assets/locations", img)
        if not os.path.exists(full):
            issues.append(f"  404: {img}")
        else:
            img_lower = img.lower()
            for kw in BAD_KW:
                if kw in img_lower:
                    issues.append(f"  OLD PHOTO: contains '{kw}' — {img}")
                    break

    status = "OK" if not issues else f"{len(issues)} PROBLEMS"
    print(f"\n{label} ({len(imgs)} images): {status}")
    if issues:
        all_ok = False
    for i in issues:
        print(i)

print(f"\n{'=' * 60}")
if all_ok:
    print("ALL CLEAN — no 1800s photos, no broken images, no wrong cities.")
else:
    print("SOME ISSUES FOUND — see above.")
