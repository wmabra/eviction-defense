#!/usr/bin/env python3
"""Fix remaining 'seven' and '7' references, update logo extension."""
import os, sys, re

SEO_DIR = "/opt/eviction-defense/seo"

REPLACEMENTS = [
    # Logo - jpg to png
    ('evictions-help-logo.jpg', 'evictions-help-logo.png'),
    
    # "seven" text patterns
    ('Start with seven questions', 'Start with eight questions'),
    ('start with seven questions', 'start with eight questions'),
    ('Answer seven questions', 'Answer eight questions'),
    ('answer seven questions', 'answer eight questions'),
    ('Answer seven focused questions', 'Answer eight focused questions'),
    ('same seven-question', 'same eight-question'),
    ('seven-question screening', 'eight-question screening'),
    ('seven questions first', 'eight questions first'),
    ('seven eligibility questions', 'eight eligibility questions'),
    ('Check eligibility in seven questions', 'Check eligibility in eight questions'),
    ('seven focused questions', 'eight focused questions'),
    ('Start with seven', 'Start with eight'),
    ('answer seven', 'answer eight'),
    ('Seven questions', 'Eight questions'),
    
    # "7" in stat bands and sticky mobile
    ('<strong>7</strong><span>eligibility questions</span>', '<strong>8</strong><span>eligibility questions</span>'),
    ('Start with 7 questions<br>', 'Start with 8 questions<br>'),
    ('Start with 7 questions<br', 'Start with 8 questions<br'),
    ('Begin with 7 questions', 'Begin with 8 questions'),
    
    # Meta descriptions
    ('in seven questions, complete', 'in eight questions, complete'),
]

def fix_file(fpath):
    try:
        with open(fpath, 'r', encoding='utf-8') as f:
            content = f.read()
    except:
        return False
    
    original = content
    for old, new in REPLACEMENTS:
        content = content.replace(old, new)
    
    if content != original:
        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

def process():
    count = 0
    for root, dirs, files in os.walk(SEO_DIR):
        for fname in files:
            if not fname.endswith('.html'):
                continue
            fpath = os.path.join(root, fname)
            if fix_file(fpath):
                count += 1
    return count

if __name__ == '__main__':
    target = sys.argv[1] if len(sys.argv) > 1 else SEO_DIR
    n = process()
    print(f"Fixed {n} files")
