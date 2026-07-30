#!/usr/bin/env python3
"""Update all SEO HTML files from 7 to 8 questions with county step."""

import os
import re
import sys

SEO_DIR = "/opt/eviction-defense/seo"

# The county question HTML to insert after the state question
COUNTY_STEP = '<div class="screen-step"><div class="question-count">Question 2 of 8</div><div class="question">What county is the eviction case in?</div><select name="county" required aria-label="County"><option value="">Select a county</option></select></div>'

# Pattern to find the end of the state select step
# The state step has name="state" and ends with </select></div>
# We need to insert county step right after that closing </div>
STATE_STEP_PATTERN = re.compile(
    r'(<div class="screen-step active"><div class="question-count">Question 1 of 7</div>.*?name="state".*?</select></div>)'
)


def transform(content: str, path: str) -> str | None:
    """Transform one HTML file. Returns new content or None if no changes."""
    changed = False
    original = content

    # 1. Insert county step after state step
    m = STATE_STEP_PATTERN.search(content)
    if m:
        content = content[:m.end()] + COUNTY_STEP + content[m.end():]
        changed = True
    else:
        print(f"  WARNING: Could not find state step pattern in {path}")

    # 2. Renumber question counts - work backward to avoid re-matching
    # Q7 of 7 → Q8 of 8
    content = content.replace("Question 7 of 7", "Question 8 of 8")
    content = content.replace("Question 6 of 7", "Question 7 of 8")
    content = content.replace("Question 5 of 7", "Question 6 of 8")
    content = content.replace("Question 4 of 7", "Question 5 of 8")
    content = content.replace("Question 3 of 7", "Question 4 of 8")
    content = content.replace("Question 2 of 7", "Question 3 of 8")
    content = content.replace("Question 1 of 7", "Question 1 of 8")

    # 3. Catch any remaining "of 7" 
    content = re.sub(r'\bof 7\b', 'of 8', content)

    # 4. Text updates
    replacements = [
        ("seven-question", "eight-question"),
        ("7-question", "8-question"),
        ("Answer seven questions", "Answer eight questions"),
        ("answer seven questions", "answer eight questions"),
        ("same seven-question", "same eight-question"),
        ("Start with 7 questions", "Start with 8 questions"),
        ("7 quick questions", "8 quick questions"),
    ]
    for old, new in replacements:
        if old in content:
            content = content.replace(old, new)
            changed = True

    if content != original:
        return content
    return None


def process_directory(dirpath: str):
    """Recursively process all HTML files."""
    count = 0
    for root, dirs, files in os.walk(dirpath):
        for fname in files:
            if not fname.endswith(".html"):
                continue
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception as e:
                print(f"  ERROR reading {fpath}: {e}")
                continue

            new_content = transform(content, fpath)
            if new_content is not None:
                try:
                    with open(fpath, "w", encoding="utf-8") as f:
                        f.write(new_content)
                    count += 1
                    rel = os.path.relpath(fpath, dirpath)
                    print(f"  ✓ {rel}")
                except Exception as e:
                    print(f"  ERROR writing {fpath}: {e}")

    return count


if __name__ == "__main__":
    if len(sys.argv) > 1:
        target = sys.argv[1]
    else:
        target = SEO_DIR

    if not os.path.isdir(target):
        print(f"Error: {target} is not a directory")
        sys.exit(1)

    print(f"Processing HTML files in {target}...")
    n = process_directory(target)
    print(f"\nDone. Updated {n} files.")
