#!/usr/bin/env python3
"""Inject CC-BY attributions into pages using cached license data."""
import os, re, json

SEO = "/opt/eviction-defense/seo"
CACHE_FILE = "/tmp/attribution_cache.json"

try:
    cache = json.loads(open(CACHE_FILE).read())
except (FileNotFoundError, json.JSONDecodeError):
    print("Cache not found or corrupt")
    exit(1)

print(f"Loaded cache: {len(cache)} entries")

def is_cc_by(lic):
    if not lic:
        return False
    l = lic.lower()
    if any(x in l for x in ["pd", "cc0", "public domain"]):
        return False
    return "cc by" in l or "cc-by" in l

def build_attr(lic, artist):
    artist = re.sub(r"<[^>]+>", "", artist).strip() if artist else ""
    if len(artist) > 50:
        artist = artist[:47] + "..."
    parts = []
    if artist:
        parts.append(artist)
    lic_short = lic.replace("CC ", "CC").replace("Creative Commons ", "")
    parts.append(lic_short)
    text = " · ".join(parts)
    return '<span class="img-attr">' + text + '</span>'

cc_by_count = 0
pd_count = 0
pages_mod = 0
already_done = 0

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

    # Skip if already done
    if "img-attr" in html:
        already_done += 1
        continue

    modified = False
    new_parts = []
    pos = 0

    for m in re.finditer(r'<img src="(/assets/locations/([^"]+))"([^>]*)>', html):
        # Add text before this match
        new_parts.append(html[pos:m.start()])
        img_path = m.group(2)
        fname = os.path.basename(img_path)
        info = cache.get(fname, {})
        lic = info.get("license", "")

        if is_cc_by(lic):
            attr = build_attr(lic, info.get("artist", ""))
            new_parts.append(m.group(0) + attr)
            cc_by_count += 1
            modified = True
        else:
            new_parts.append(m.group(0))
            pd_count += 1

        pos = m.end()

    new_parts.append(html[pos:])
    new_html = "".join(new_parts)

    if modified:
        try:
            with open(fpath, "w") as f:
                f.write(new_html)
            pages_mod += 1
        except OSError:
            pass

    if pages_mod % 200 == 0 and pages_mod > 0:
        print(f"  ... {pages_mod} pages modified")

print(f"\nDone! {cc_by_count} CC-BY attributions added to {pages_mod} pages.")
print(f"{pd_count} PD/CC0 images left alone. {already_done} pages already had attributions.")

# Add CSS rule
css_path = os.path.join(SEO, "assets", "styles.css")
rule = ".img-attr{display:block;font-size:10px;color:#999;opacity:.55;margin-top:2px;line-height:1.2}"
try:
    existing = open(css_path).read()
    if ".img-attr" not in existing:
        with open(css_path, "w") as f:
            f.write(existing.rstrip() + rule)
        print("Added .img-attr CSS rule")
except OSError:
    pass
