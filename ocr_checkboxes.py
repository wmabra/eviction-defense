"""OCR-based checkbox detection for overlay-only state forms."""
import fitz, subprocess, tempfile, os, json, re, sys

sys.path.insert(0, os.path.dirname(__file__))
from app.services.state_configs import get_state_config

FORMS_DIR = os.path.join(os.path.dirname(__file__), "app", "templates", "counties")

# Defense keyword → our internal key mapping
DEFENSE_KEY_MAP = [
    ("dismiss", "def_dismiss"),
    ("jurisdiction", "def_contest"),
    ("proper party", "def_not_owner"),
    ("not the person", "def_not_owner"),
    ("notice", "def_bad_notice"),
    ("retaliat", "def_retaliation"),
    ("discrim", "def_discrimination"),
    ("repair", "def_repairs"),
    ("fail", "def_repairs"),
    ("maintain", "def_repairs"),
    ("habita", "def_repairs"),
    ("condition", "def_repairs"),
    ("uninhabit", "def_repairs"),
    ("unsafe", "def_repairs"),
    ("paid", "def_paid"),
    ("rent paid", "def_paid"),
    ("amount", "def_amount"),
    ("owe", "def_amount"),
    ("accept", "def_accepted_rent"),
    ("waive", "def_waived"),
    ("correct", "def_corrected"),
    ("breach", "def_landlord_breach"),
    ("moved", "def_moved_out"),
    ("other defense", "def_other"),
    ("counterclaim", "def_counterclaim"),
]


def ocr_page(page, dpi=300):
    """Render a PDF page and run Tesseract OCR, returning word list."""
    pix = page.get_pixmap(dpi=dpi)
    scale = dpi / 72.0

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        pix.save(f.name)
        result = subprocess.run(
            ["tesseract", f.name, "stdout", "-l", "eng", "--psm", "6", "tsv"],
            capture_output=True, text=True, timeout=30,
        )
        os.unlink(f.name)

    if result.returncode != 0:
        return [], scale

    lines = result.stdout.strip().split("\n")
    if len(lines) < 2:
        return [], scale

    words = []
    for line in lines[1:]:
        cols = line.split("\t")
        if len(cols) >= 12:
            try:
                conf = float(cols[10])
                text = cols[11].strip()
                left = int(cols[6])
                top = int(cols[7])
                width = int(cols[8])
                height = int(cols[9])
                if text and conf > 10:
                    words.append({"text": text, "x": left, "y": top, "w": width, "h": height})
            except (ValueError, IndexError):
                pass

    words.sort(key=lambda w: (w["y"], w["x"]))
    return words, scale


def find_checkboxes(words, scale):
    """Find [ ] or ( ) checkbox markers in OCR output and extract their labels."""
    findings = []
    for i, w in enumerate(words):
        if w["text"] in ["[", "("]:
            if i + 1 < len(words) and words[i + 1]["text"] in ["]", ")"]:
                cb_x = round(w["x"] / scale)
                cb_y = round(w["y"] / scale)

                # Get the text after the checkbox
                label_words = []
                for j in range(i + 3, min(i + 25, len(words))):
                    nw = words[j]
                    if nw["y"] - w["y"] > 25:
                        break
                    label_words.append(nw["text"])

                label = " ".join(label_words)[:150]
                if not label:
                    continue

                # Map to defense key
                def_key = None
                label_lower = label.lower()
                for kw, key in DEFENSE_KEY_MAP:
                    if kw in label_lower:
                        def_key = key
                        break

                findings.append({
                    "x": cb_x,
                    "y": cb_y,
                    "label": label,
                    "defense_key": def_key,
                })

    return findings


def main():
    states_to_scan = sys.argv[1:] if len(sys.argv) > 1 else ["AR", "AZ", "MN", "NM", "OR"]

    for state in states_to_scan:
        cfg = get_state_config(state)
        if not cfg:
            continue
        form_file = os.path.join(FORMS_DIR, cfg.get("answer_form", ""))
        if not os.path.exists(form_file):
            print(f"{state}: FORM NOT FOUND")
            continue

        doc = fitz.open(form_file)
        print(f"\n{'='*70}")
        print(f"  {state}: {cfg.get('answer_form')} ({len(doc)} pages)")
        print(f"{'='*70}")

        all_findings = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            words, scale = ocr_page(page)

            if not words:
                print(f"  Page {page_num+1}: No text found by OCR")
                continue

            findings = find_checkboxes(words, scale)
            for f in findings:
                f["page"] = page_num + 1
                all_findings.append(f)

            print(f"  Page {page_num+1}: {len(findings)} checkboxes found")

        doc.close()

        if all_findings:
            for f in all_findings:
                status = f["defense_key"] or "??"
                print(f"    p{f['page']} @({f['x']:4d},{f['y']:4d}) [{status:20s}] {f['label'][:100]}")
        else:
            print(f"  ⚠️  No checkboxes detected")


if __name__ == "__main__":
    main()
