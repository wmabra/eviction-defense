"""Inspect PDF fields and nearby text labels to build accurate field mappings."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import fitz

def inspect_state(state_code):
    from app.services.state_configs import STATE_CONFIGS
    cfg = STATE_CONFIGS.get(state_code.upper())
    if not cfg:
        print(f"{state_code}: Not configured")
        return
    fn = cfg.get("answer_form")
    if not fn:
        print(f"{state_code}: No answer form")
        return
    path = os.path.join("app/templates/counties", fn)
    if not os.path.exists(path):
        print(f"{state_code}: File not found: {path}")
        return
    
    doc = fitz.open(path)
    print(f"\n{'='*70}")
    print(f"{state_code} — {cfg['name']} ({fn})")
    print(f"{doc.page_count} pages")
    print(f"{'='*70}")
    
    for i in range(doc.page_count):
        page = doc[i]
        widgets = list(page.widgets())
        if not widgets:
            continue
        
        # Get text blocks near fields
        blocks = page.get_text("blocks")
        
        print(f"\n--- Page {i+1}: {len(widgets)} fields ---")
        for w in widgets:
            fn = w.field_name or "(unnamed)"
            fv = w.field_value or "(empty)"
            # Find closest text label above/before this field
            rect = w.rect
            nearby = []
            for b in blocks:
                bx, by, bx2, by2, txt, *_ = b
                txt = txt.strip()
                if txt and len(txt) > 2:
                    # Check if text is near the field (above or to the left)
                    if (by < rect.y1 + 20 and by > rect.y0 - 60) or \
                       (bx < rect.x0 + 10 and abs(by - rect.y0) < 40):
                        nearby.append(txt[:60])
            
            # If field name is generic (Text1, Check Box, number), show nearby labels
            if fn.startswith("Text") or fn.startswith("Check Box") or (str(fn).isdigit() and int(str(fn)) < 100):
                label = nearby[0] if nearby else "(no label nearby)"
                print(f"  Field \"{fn}\" ← near: \"{label}\"")
            elif fn in ["undefined", "undefined_2", "VS", "VS_2"]:
                label = nearby[0] if nearby else "(no label)"
                print(f"  Field \"{fn}\" ← near: \"{label}\"")
            else:
                print(f"  Field \"{fn}\"")
    
    doc.close()

if __name__ == "__main__":
    states = sys.argv[1:] if len(sys.argv) > 1 else ["VA","SC","GA","TX","IL","RI","CO","MS","TN","CA","NC"]
    for s in states:
        inspect_state(s.upper())
