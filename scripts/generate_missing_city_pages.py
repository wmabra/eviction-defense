#!/usr/bin/env python3
"""Generate missing 50k+ city pages (reads /tmp/missing_cities.json).

Usage (run on the server, after census_50k_cities.py + audit_seo_pages.py):
    set -a && source /opt/eviction-defense/.env && set +a
    python3 scripts/generate_missing_city_pages.py [--dry-run]

Reuses build_city_page() from generate_missing_cities2.py.
"""
"""Generate the missing 50k+ city pages using the existing template."""
import sys
import os
import json

sys.path.insert(0, "/opt/eviction-defense/scripts")
from generate_missing_cities2 import (
    build_city_page, get_county_slug, STATE_ABBR_TO_NAME, slugify,
)

SEO = "/opt/eviction-defense/seo"
DRY = "--dry-run" in sys.argv

cities = json.load(open("/tmp/missing_cities.json"))
print(f"Loaded {len(cities)} missing cities")

created = 0
skipped = 0
failed = 0

for i, c in enumerate(cities, 1):
    state_slug = c["state_slug"]
    state_abbr = c["state_abbr"]
    state_name = STATE_ABBR_TO_NAME[state_abbr]
    county_name = c["county_name"]

    county_slug, _display = get_county_slug(state_slug, county_name)
    if not county_slug:
        print(f"[{i}/{len(cities)}] FAIL {state_abbr} {c['city']}: county '{county_name}' not found")
        failed += 1
        continue

    city_slug = slugify(c["city"])
    city_dir = os.path.join(SEO, state_slug, county_slug, city_slug)

    if os.path.exists(os.path.join(city_dir, "index.html")):
        print(f"[{i}/{len(cities)}] SKIP {state_abbr} {c['city']}: already exists at {state_slug}/{county_slug}/{city_slug}")
        skipped += 1
        continue

    if DRY:
        print(f"[{i}/{len(cities)}] WOULD CREATE {state_slug}/{county_slug}/{city_slug}")
        continue

    try:
        html = build_city_page(c["city"], state_abbr, state_slug, state_name,
                               county_name, county_slug, c["population"])
        os.makedirs(city_dir, exist_ok=True)
        with open(os.path.join(city_dir, "index.html"), "w", encoding="utf-8") as f:
            f.write(html)
        created += 1
        print(f"[{i}/{len(cities)}] CREATED {state_slug}/{county_slug}/{city_slug} (pop {c['population']:,})")
    except Exception as e:
        print(f"[{i}/{len(cities)}] FAIL {state_abbr} {c['city']}: {e}")
        failed += 1

print(f"\nDone. created={created} skipped={skipped} failed={failed}")
