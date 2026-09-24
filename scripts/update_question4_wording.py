import os
import re

SEO_DIR = "/opt/eviction-defense/seo"

OLD_VARIANTS = [
    '<div class="question">Have you been served with eviction court papers or assigned a case number?</div>',
    '<div class="question">Have you been served with eviction court papers?</div>',
]
NEW_QUESTION = '<div class="question">Have you received formal court papers (Summons &amp; Complaint) with a court case number?</div>'

count = 0
for root, dirs, files in os.walk(SEO_DIR):
    for f in files:
        if f.endswith(".html"):
            path = os.path.join(root, f)
            with open(path, "r", encoding="utf-8") as fp:
                content = fp.read()
            changed = False
            for old in OLD_VARIANTS:
                if old in content:
                    content = content.replace(old, NEW_QUESTION)
                    changed = True
            if changed:
                with open(path, "w", encoding="utf-8") as fp:
                    fp.write(content)
                count += 1

print(f"Updated Question 4 wording in {count} HTML files.")
