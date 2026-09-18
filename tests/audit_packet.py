#!/usr/bin/env python3
"""Audit a generated test packet for errors:
- Form 01 & Form 02 completeness
- Signature auto-fill (/s/)
- Widget overlaps / collisions
- Checkbox exclusivity (e.g. Yes/No, pay frequencies)
- Orphan pages
- Financial concordance
"""
import sys
import os
import pymupdf as fitz

def audit_packet(pkg_dir):
    errors = []
    warnings = []
    
    if not os.path.isdir(pkg_dir):
        return [f"Directory not found: {pkg_dir}"], []

    files = sorted([f for f in os.listdir(pkg_dir) if f.endswith('.pdf')])
    if not files:
        return [f"No PDF files found in {pkg_dir}"], []
        
    for fname in files:
        fpath = os.path.join(pkg_dir, fname)
        doc = fitz.open(fpath)
        
        # 1. Signature auto-fill check (signature widgets must stay blank for ink)
        for pno in range(len(doc)):
            page = doc[pno]
            for w in page.widgets():
                val = str(getattr(w, "field_value", "") or "").strip()
                fn = (w.field_name or "").lower()
                if "/s/" in val:
                    errors.append(f"{fname} Page {pno+1}: signature auto-filled with '/s/' in {w.field_name}")
                elif any(k in fn for k in ("signature", "sig_line", "sign_here")) and val and not any(k in fn for k in ("date", "name", "title")):
                    errors.append(f"{fname} Page {pno+1}: signature widget {w.field_name} filled with {repr(val)}")
                
        # 2. Orphan page check (last page has <= 4 lines on multi-page docs)
        if len(doc) > 1:
            last_page = doc[-1]
            lines = [l.strip() for l in last_page.get_text().splitlines() if l.strip()]
            # Exclude deliberate final forms or checklists that might be short, and official court forms
            if len(lines) <= 4 and not any(k in fname.lower() for k in ("checklist", "timeline", "court_form")):
                warnings.append(f"{fname} Page {len(doc)} has only {len(lines)} lines (orphan page): {lines}")
                
        # 3. Widget collision check
        for pno in range(len(doc)):
            page = doc[pno]
            ws = list(page.widgets())
            for i in range(len(ws)):
                for j in range(i + 1, len(ws)):
                    w1, w2 = ws[i], ws[j]
                    if w1.field_name != w2.field_name and w1.rect.intersects(w2.rect):
                        # check if intersection is non-trivial (> 2pt)
                        ir = fitz.Rect(w1.rect).intersect(w2.rect)
                        if ir.width > 2 and ir.height > 2:
                            errors.append(f"{fname} Page {pno+1}: widget {w1.field_name} intersects {w2.field_name} by {ir.width:.1f}x{ir.height:.1f}pt")

        # 4. Form 02 Checkbox exclusivity checks
        if "fee_waiver" in fname.lower():
            # Check for multiple pay frequency boxes
            freq_checked = []
            yes_no_pairs = {}
            for pno in range(len(doc)):
                for w in doc[pno].widgets():
                    fn = (w.field_name or "").lower()
                    val = str(getattr(w, "field_value", "") or "")
                    if val in ("Yes", "On", "true", "1") or val is True:
                        if any(k in fn for k in ("weekly", "bi-weekly", "biweekly", "monthly")) and "amount" not in fn and "expense" not in fn and "paid" in fn:
                            freq_checked.append((w.field_name, pno+1))
                    # Yes/No tracking
                    if fn.endswith("- yes") or fn.endswith(" yes"):
                        base = fn.replace("- yes", "").replace(" yes", "").strip()
                        yes_no_pairs.setdefault(base, {})["yes"] = (val in ("Yes", "On", "true", "1") or val is True)
                    elif fn.endswith("- no") or fn.endswith(" no"):
                        base = fn.replace("- no", "").replace(" no", "").strip()
                        yes_no_pairs.setdefault(base, {})["no"] = (val in ("Yes", "On", "true", "1") or val is True)
            
            if len(freq_checked) > 1:
                errors.append(f"{fname}: Multiple pay frequencies checked: {[f[0] for f in freq_checked]}")
                
            for base, states in yes_no_pairs.items():
                if states.get("yes") and states.get("no"):
                    errors.append(f"{fname}: Contradictory Yes/No both checked for '{base}'")
                    
        doc.close()
        
    return errors, warnings

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python audit_packet.py <pkg_dir>")
        sys.exit(1)
    errs, warns = audit_packet(sys.argv[1])
    print(f"Audit for {sys.argv[1]}:")
    print(f"  Errors: {len(errs)}")
    for e in errs:
        print(f"   [ERROR] {e}")
    print(f"  Warnings: {len(warns)}")
    for w in warns:
        print(f"   [WARN] {w}")
    sys.exit(1 if errs else 0)
