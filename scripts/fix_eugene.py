#!/usr/bin/env python3
"""Fix Eugene, OR page - replace Seattle image with actual Eugene photos."""
import urllib.request, urllib.parse, json, time, os, re

UA = "evictions.help/1.0"

def wm(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())

# 1. Clean the page
html = open("/opt/eviction-defense/seo/oregon/lane-county/eugene/index.html").read()
html = re.sub(r'<div class=.local-images.*?</div>', '', html, flags=re.DOTALL)
open("/opt/eviction-defense/seo/oregon/lane-county/eugene/index.html", "w").write(html)
print("Cleaned old images")

# 2. Find Eugene-specific modern photos
queries = [
    "Eugene Oregon downtown skyline",
    "Eugene Oregon city hall building",
    "Eugene Oregon university campus",
    "Eugene Oregon park",
]
found = []
for q in queries:
    if len(found) >= 6:
        break
    params = urllib.parse.urlencode({
        "action": "query", "list": "search",
        "srsearch": q, "srnamespace": "6", "srlimit": 6, "format": "json"
    })
    data = wm(f"https://commons.wikimedia.org/w/api.php?{params}")
    for r in data.get("query", {}).get("search", []):
        t = r["title"].lower()
        # Must contain eugene
        if "eugene" not in t:
            continue
        # Skip bad/old/historical content
        bad = ["nara", "prosch", "seattle", "portland", "memorial",
               "funeral", "dpla", "loc.gov", "library_of_congress"]
        if any(b in t for b in bad):
            continue
        if r["title"] not in [f["title"] for f in found]:
            found.append(r)
    time.sleep(1.5)

print(f"Found {len(found)} candidates: {[f['title'] for f in found[:5]]}")

# 3. Download up to 2 best images
dest_dir = "/opt/eviction-defense/seo/assets/locations/oregon/lane/eugene"
os.makedirs(dest_dir, exist_ok=True)
downloaded = []

for f in found[:5]:
    if len(downloaded) >= 2:
        break
    params = urllib.parse.urlencode({
        "action": "query", "titles": f["title"],
        "prop": "imageinfo", "iiprop": "url|extmetadata",
        "iiurlwidth": 800, "format": "json"
    })
    data = wm(f"https://commons.wikimedia.org/w/api.php?{params}")
    for p in data.get("query", {}).get("pages", {}).values():
        ii = p.get("imageinfo", [])
        if not ii:
            continue
        url = ii[0].get("thumburl") or ii[0]["url"]
        ext_meta = ii[0].get("extmetadata", {})
        lic = ext_meta.get("LicenseShortName", {}).get("value", "").lower()
        if not any(x in lic for x in ["pd", "cc-by", "cc0", "public domain"]):
            continue
        ext = os.path.splitext(url.split("?")[0])[-1]
        if ext.lower() not in [".jpg", ".jpeg", ".png", ".webp"]:
            ext = ".jpg"
        clean_name = os.path.splitext(p["title"].split(":")[-1])[0]
        fname = re.sub(r"[^a-zA-Z0-9_-]", "_", clean_name)
        dest = os.path.join(dest_dir, f"{fname}{ext}")
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=30) as r:
            with open(dest, "wb") as out:
                out.write(r.read())
        rel = "/" + os.path.relpath(dest, "/opt/eviction-defense/seo")
        downloaded.append(rel)
        print(f"Downloaded: {rel}")
        time.sleep(1)

# 4. Inject into HTML
html2 = open("/opt/eviction-defense/seo/oregon/lane-county/eugene/index.html").read()
cols = "1fr 1fr" if len(downloaded) >= 2 else "1fr"
cells = []
for p in downloaded:
    cells.append(
        '<div class="img-cell">'
        f'<img src="{p}" alt="Eugene, Oregon" loading="lazy" '
        'style="width:100%;height:auto;border-radius:8px;aspect-ratio:16/10;object-fit:cover">'
        '</div>'
    )
imgs_html = "".join(cells)
img_div = (
    f'<div class="local-images" '
    f'style="display:grid;grid-template-columns:{cols};gap:16px;margin:24px 0">'
    f'{imgs_html}</div>'
)
html2 = html2.replace("</p></div></section>", f"</p>{img_div}</div></section>", 1)
open("/opt/eviction-defense/seo/oregon/lane-county/eugene/index.html", "w").write(html2)
print(f"Injected {len(downloaded)} images into Eugene page")
