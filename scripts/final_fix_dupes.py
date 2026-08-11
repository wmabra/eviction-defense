#!/usr/bin/env python3
"""Surgically replace old duplicate images with new ones already on disk."""
import re, os

SEO = "/opt/eviction-defense/seo"

fixes = {
    "south-carolina/anderson-county": {
        "asset_prefix": "south_carolina/anderson",
        "new": [
            "U.S._Post_Office_and_Courthouse_(Anderson,_South_Carolina)_1910.jpg.jpg",
            "Anderson_-_County_Courthouse_annex.jpg.jpg",
        ],
    },
    "texas/bexar-county": {
        "asset_prefix": "texas/bexar",
        "new": [
            "Bexar_County_Courthouse,_San_Antonio,_Texas,_USA.jpg.jpg",
            "Bexar_County_Courthouse_seen_from_San_Antonio_River_Walk,_2014_(143298451).jpg.jpg",
        ],
    },
}

for page, cfg in fixes.items():
    path = os.path.join(SEO, page, "index.html")
    try:
        html = open(path).read()
    except OSError:
        print(f"{page}: cannot read")
        continue
    prefix = cfg["asset_prefix"]
    new_imgs = cfg["new"]

    # Find all location images
    old_imgs = re.findall(rf'/assets/locations/{prefix}/[^"]+', html)
    print(f"{page}: {len(old_imgs)} found, replacing first {len(new_imgs)}")

    modified = html
    for i, new_name in enumerate(new_imgs):
        if i < len(old_imgs):
            old_full = old_imgs[i]
            new_full = f"/assets/locations/{prefix}/{new_name}"
            modified = modified.replace(old_full, new_full, 1)

    # Remove any remaining unreplaced old img tags
    pattern = re.compile(
        r'<div class="img-cell">\s*<img src="/assets/locations/' + prefix + r'/[^"]+"[^>]*>\s*</div>'
    )
    # Only remove if we still have more than 2 location images
    remaining = re.findall(rf'/assets/locations/{prefix}/', modified)
    while len(remaining) > len(new_imgs):
        modified = pattern.sub("", modified, count=1)
        remaining = re.findall(rf'/assets/locations/{prefix}/', modified)

    if modified != html:
        try:
            open(path, "w").write(modified)
        except OSError:
            print(f"{page}: write failed")
            continue
        final = len(re.findall(rf'/assets/locations/{prefix}/', modified))
        print(f"  Fixed: {final} images remaining")
    else:
        print(f"  No changes needed")
