import os
import re

root_dir = "/opt/eviction-defense/seo"
count = 0
for root, dirs, files in os.walk(root_dir):
    for f in files:
        if f.endswith(".html"):
            path = os.path.join(root, f)
            with open(path, "r", encoding="utf-8") as fp:
                content = fp.read()
            new_content = re.sub(r'/assets/site\.js(\?v=[^\s"\'<>]*)?', '/assets/site.js?v=20260924_v3', content)
            if new_content != content:
                with open(path, "w", encoding="utf-8") as fp:
                    fp.write(new_content)
                count += 1
print(f"Updated {count} HTML files with cache buster.")
