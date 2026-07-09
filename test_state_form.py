"""
Test script — fills a state's eviction answer form and verifies output.
Usage: python3 test_state_form.py VA
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
os.environ["DATABASE_URL"] = "sqlite:///./test.db"

from app.services.pdf_overlay import fill_answer_form, fill_fee_waiver

SAMPLE_DATA = {
    "personal_info": {
        "full_name": "Jane M. Tenant",
        "phone": "(555) 123-4567",
        "email": "jane@email.com",
        "property_address": "123 Main Street",
        "property_city": "Norfolk",
        "property_zip": "23510",
        "county": "Norfolk City",
    },
    "landlord_info": {
        "landlord_name": "ABC Properties LLC",
        "landlord_address": "456 Market St, Norfolk, VA 23510",
        "landlord_phone": "(555) 987-6543",
        "landlord_email": "landlord@abcprops.com",
    },
    "case_details": {
        "case_number": "GVL-2024-012345",
        "court_name": "Norfolk General District Court",
        "notice_amount_demanded": "$2,400.00",
        "monthly_rent": "$1,200.00",
    },
    "defenses": {
        "def_bad_notice": {"checked": True, "explanation": "I did not receive a proper 5-day notice"},
        "def_repairs": {"checked": True, "explanation": "The landlord failed to fix the AC"},
    },
}

OUTPUT_DIR = "/tmp/eviction_test"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def test_state(state_code):
    print(f"\n{'='*60}")
    print(f"Testing {state_code}...")
    print('='*60)
    
    # Test answer form
    answer_path = os.path.join(OUTPUT_DIR, f"{state_code}_answer.pdf")
    try:
        result = fill_answer_form(SAMPLE_DATA, state_code, answer_path)
        if result:
            size = os.path.getsize(answer_path)
            print(f"  ✅ Answer form: {answer_path} ({size/1024:.0f} KB)")
        else:
            print(f"  ❌ Answer form: Failed")
    except Exception as e:
        print(f"  ❌ Answer form error: {e}")
    
    # Test fee waiver
    waiver_path = os.path.join(OUTPUT_DIR, f"{state_code}_fee_waiver.pdf")
    try:
        result = fill_fee_waiver(SAMPLE_DATA, state_code, waiver_path)
        if result:
            size = os.path.getsize(waiver_path)
            print(f"  ✅ Fee waiver: {waiver_path} ({size/1024:.0f} KB)")
        else:
            print(f"  ⚠️ Fee waiver: Not available or failed")
    except Exception as e:
        print(f"  ⚠️ Fee waiver error: {e}")
    
    # Verify PDF fields were filled
    try:
        import fitz
        doc = fitz.open(answer_path)
        filled = 0
        for page in doc:
            try:
                for w in page.widgets():
                    if w.field_value:
                        filled += 1
            except:
                pass
        if filled > 0:
            print(f"  ✅ {filled} fillable fields populated")
        else:
            # Check for overlay text
            text = ""
            for page in doc:
                text += page.get_text()
            if "Jane" in text or "ABC Properties" in text:
                print(f"  ✅ Text overlay confirmed (test data present)")
            else:
                print(f"  ⚠️ No filled fields or overlay text found")
        doc.close()
    except Exception as e:
        print(f"  ⚠️ Verification error: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        state = sys.argv[1].upper()
        test_state(state)
    else:
        for s in ["VA", "SC", "GA", "TX", "IL", "CT", "NC", "RI", "CO", "LA", "MS", "TN", "CA", "AR", "AZ", "MN", "NM", "FL"]:
            test_state(s)
