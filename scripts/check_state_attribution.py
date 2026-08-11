#!/usr/bin/env python3
"""Check which state-level pages have CC-BY images missing attribution."""
import os, re, json

SEO = '/opt/eviction-defense/seo'
try:
    cache = json.load(open('/tmp/attribution_cache.json'))
except (FileNotFoundError, json.JSONDecodeError) as e:
    print(f'Cannot load cache: {e}')
    exit(1)

CC_BY = {
    'CC BY', 'CC BY-SA', 'CC BY-SA 1.0', 'CC BY-SA 2.0', 'CC BY-SA 2.5',
    'CC BY-SA 3.0', 'CC BY-SA 4.0', 'CC BY 3.0', 'CC BY 4.0', 'CC BY 2.0',
    'CC BY 2.5', 'CC-BY-3.0', 'CC-BY-4.0', 'CC-BY-SA-3.0', 'CC-BY-SA-4.0'
}

try:
    entries = os.listdir(SEO)
except OSError as e:
    print(f'Cannot list {SEO}: {e}')
    exit(1)
state_dirs = sorted([
    d for d in entries
    if os.path.isdir(os.path.join(SEO, d))
    and d not in ('assets', 'checkout', 'disclaimer', 'privacy', 'terms')
])

total_missing = 0

for state in state_dirs:
    fpath = os.path.join(SEO, state, 'index.html')
    if not os.path.isfile(fpath):
        continue
    try:
        html = open(fpath).read()
    except OSError:
        continue

    imgs = re.findall(r'<img src="/assets/locations/([^"]+)"', html)
    missing = []
    for img in imgs:
        fname = os.path.basename(img)
        info = cache.get(fname, {})
        lic = info.get('license', '').strip()
        # Check if CC-BY and no attribution present
        if lic in CC_BY and 'img-attr' not in html:
            missing.append(f'{fname} ({lic})')

    if missing:
        total_missing += len(missing)
        print(f'❌ {state}: {len(missing)} CC-BY images missing attribution:')
        for m in missing:
            print(f'   - {m}')
    else:
        has_attr = 'img-attr' in html
        status = '✅ (CC-BY attr present)' if has_attr else '✅ (all PD/CC0)'
        print(f'{status:35s}  {state}  ({len(imgs)} images)')

print(f'\nTotal CC-BY images missing attribution: {total_missing}')
