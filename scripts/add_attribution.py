#!/usr/bin/env python3
"""Add small CC-BY attribution to images that require it.

Queries Wikimedia for each image's license with proper throttling.
Adds a subtle, unobtrusive attribution line below CC-BY images.
"""
import os, re, json, time, urllib.request, urllib.parse

SEO = "/opt/eviction-defense/seo"
CACHE_FILE = "/tmp/attribution_cache.json"
UA = "evictions.help/1.0 (https://evictions.help; support@evictions.help)"
DELAY = 3.0  # Seconds between Wikimedia API calls to avoid 429

def wm_request(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=15) as r:
        try:
            return json.loads(r.read())
        except (json.JSONDecodeError, ValueError):
            return {}

def get_license_for_file(title):
    """Get license + artist for a Wikimedia file title."""
    params = urllib.parse.urlencode({
        "action": "query", "titles": title,
        "prop": "imageinfo", "iiprop": "extmetadata",
        "format": "json",
    })
    url = f"https://commons.wikimedia.org/w/api.php?{params}"
    try:
        data = wm_request(url)
        for page in data.get("query", {}).get("pages", {}).values():
            ii = page.get("imageinfo", [])
            if ii:
                meta = ii[0].get("extmetadata", {})
                lic = meta.get("LicenseShortName", {}).get("value", "")
                artist_html = meta.get("Artist", {}).get("value", "")
                # Strip HTML tags from artist
                artist = re.sub(r"<[^>]+>", "", artist_html).strip()
                # Truncate long artist names
                if len(artist) > 50:
                    artist = artist[:47] + "..."
                return {"license": lic, "artist": artist}
    except Exception as e:
        return {"license": f"ERROR:{e}", "artist": ""}
    return {"license": "UNKNOWN", "artist": ""}

def is_cc_by(license_name):
    """Check if license requires attribution."""
    lic = license_name.lower()
    # PD and CC0 don't need attribution
    if any(x in lic for x in ["pd", "cc0", "public domain"]):
        return False
    # CC-BY variants do
    if "cc by" in lic or "cc-by" in lic:
        return True
    return False

def build_attr_line(license_name, artist):
    """Build tiny attribution HTML."""
    lic_short = license_name.replace("CC ", "CC").replace("Creative Commons ", "")
    # Shorten to just the essentials
    parts = []
    if artist:
        parts.append(artist)
    parts.append(lic_short)
    text = " · ".join(parts)
    return f'<span class="img-attr">{text}</span>'

def main():
    # Load or build cache
    cache = {}
    if os.path.exists(CACHE_FILE):
        try:
            cache = json.loads(open(CACHE_FILE).read())
            print(f"Loaded {len(cache)} cached entries")
        except Exception:
            pass

    # Collect all unique image filenames
    seen = set()
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
        for img in imgs:
            seen.add(img)

    print(f"Found {len(seen)} unique images")

    # Check licenses for uncached images
    to_check = [img for img in seen if os.path.basename(img) not in cache]
    print(f"Need to check {len(to_check)} images")

    for i, img_path in enumerate(sorted(to_check)):
        fname = os.path.basename(img_path)
        name_no_ext = os.path.splitext(fname)[0]

        # Try multiple extensions
        result = {"license": "NOT_FOUND", "artist": ""}
        for ext in [".jpg", ".JPG", ".jpeg", ".png", ".PNG"]:
            title = f"File:{name_no_ext}{ext}"
            result = get_license_for_file(title)
            if result["license"] != "NOT_FOUND":
                break

        cache[fname] = result

        if (i + 1) % 20 == 0:
            print(f"  ... {i+1}/{len(to_check)} checked")
            # Save cache periodically
            try:
                with open(CACHE_FILE, "w") as f:
                    json.dump(cache, f)
            except Exception:
                pass

        time.sleep(DELAY)

    # Final cache save
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump(cache, f)
    except Exception:
        pass

    # Now walk pages and add attribution
    cc_by_count = 0
    pd_count = 0
    pages_modified = 0

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

        modified = False

        # Find all img tags pointing to location assets
        def add_attribution(match):
            nonlocal modified, cc_by_count, pd_count
            img_path = match.group(1)
            fname = os.path.basename(img_path)

            info = cache.get(fname, {})
            lic = info.get("license", "")

            if is_cc_by(lic):
                attr = build_attr_line(lic, info.get("artist", ""))
                cc_by_count += 1
                modified = True
                return match.group(0) + attr
            else:
                pd_count += 1
                return match.group(0)

        html = re.sub(
            r'<img src="(/assets/locations/[^"]+)"([^>]*)>',
            add_attribution,
            html,
        )

        if modified:
            try:
                with open(fpath, "w") as f:
                    f.write(html)
                pages_modified += 1
            except Exception:
                pass

    print(f"\nDone. {cc_by_count} CC-BY attributions added, {pd_count} PD/CC0 left alone.")
    print(f"{pages_modified} pages modified.")

    # Add CSS rule to styles.css
    css_path = os.path.join(SEO, "assets", "styles.css")
    css_rule = ".img-attr{display:block;font-size:10px;color:#999;opacity:.55;margin-top:2px;line-height:1.2}"
    try:
        existing = open(css_path).read()
        if ".img-attr" not in existing:
            with open(css_path, "w") as f:
                f.write(existing.rstrip() + css_rule)
            print("Added .img-attr CSS rule to styles.css")
    except Exception:
        pass

if __name__ == "__main__":
    main()
