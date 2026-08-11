#!/usr/bin/env python3
"""Remove duplicate img tags left over from re-backfill."""
import re, os

SEO = "/opt/eviction-defense/seo"

pages = [
    "south-carolina/anderson-county",
    "texas/bexar-county",
]

def get_images(html):
    return re.findall(r'/assets/locations/([^"]+)', html)

for page in pages:
    path = os.path.join(SEO, page, "index.html")
    try:
        html = open(path).read()
    except OSError:
        print(f"{page}: cannot read")
        continue

    imgs = get_images(html)
    # Identify images that look like old ones (no .jpg.jpg or .JPG.JPG double ext)
    # New images from our script all have double extensions
    new_style = [img for img in imgs if img.endswith(('.jpg.jpg', '.JPG.JPG', '.jpeg.jpeg', '.JPEG.JPEG', '.png.png'))]
    old_style = [img for img in imgs if img not in new_style]
    
    print(f"  Total imgs: {len(imgs)}, new: {len(new_style)}, old: {len(old_style)}")
    
    if len(old_style) == 0:
        print(f"{page}: clean")
        continue

    modified = html
    for old in old_style:
        # Remove the entire img tag and its wrapping div
        pattern = re.compile(
            r'<div class="img-cell">\s*<img src="/assets/locations/'
            + re.escape(old)
            + r'"[^>]*>\s*<span class="img-attr"[^>]*>[^<]*</span>\s*</div>',
            re.DOTALL
        )
        modified = pattern.sub('', modified)
        # Also try without attribution span
        if modified == html:
            pattern2 = re.compile(
                r'<div class="img-cell">\s*<img src="/assets/locations/'
                + re.escape(old)
                + r'"[^>]*>\s*</div>',
                re.DOTALL
            )
            modified = pattern2.sub('', modified)
        
        if modified != html:
            print(f"  Removed old image: {os.path.basename(old)}")
        else:
            print(f"  Could not find pattern for: {os.path.basename(old)}")

    if modified != html:
        try:
            open(path, "w").write(modified)
            print(f"  Fixed!")
        except OSError as e:
            print(f"  Write error: {e}")
    else:
        print(f"  No changes")
