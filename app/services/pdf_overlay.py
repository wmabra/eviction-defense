"""
PDF overlay system — fills any court form, even scanned/non-fillable PDFs.

For fillable PDFs: uses field mapping (fast, precise).
For scanned PDFs: overlays text at exact coordinates (works on any form).
"""
# pyright: reportAttributeAccessIssue=false, reportOptionalMemberAccess=false

import os
import logging
from typing import Any, Dict, Optional, cast
from datetime import date


def _to_float(val) -> float:
    """Safely coerce a value to float (financial data is validated as numeric)."""
    try:
        return float(val)
    except (TypeError, ValueError):
        return 0.0


def _money(val, dec: int = 2) -> str:
    """Safely format a value as a dollar string."""
    try:
        return f"${float(val):,.{dec}f}"
    except (TypeError, ValueError):
        return "$0.00"


import fitz  # PyMuPDF

from app.services.state_configs import get_state_config

logger = logging.getLogger(__name__)

FORMS_DIR = os.path.join(os.path.dirname(__file__), "..", "templates", "counties")
REBUILT_DIR = os.path.join(os.path.dirname(__file__), "..", "templates", "rebuilt")


def _get_form_path(form_filename, state_code=""):
    """Get the best form to use.

    The rebuilt (scanned+widget) forms had misaligned native widgets, so we now
    always fill the ORIGINAL form via coordinate overlay (which is y-flip
    corrected in _fill_via_overlay) plus auto-detected blanks.
    """
    return os.path.join(FORMS_DIR, form_filename)


def fill_answer_form(data: dict, state: str, output_path: str) -> bool:
    """Fill a state's eviction answer form — handles fillable AND scanned PDFs."""
    return _fill_form(data, state, output_path, "answer_form")


def fill_fee_waiver(data: dict, state: str, output_path: str) -> bool:
    """Fill a state's fee waiver form."""
    return _fill_form(data, state, output_path, "fee_waiver_form")


def _expected_fee_waiver_checkbox(page, r, data, field_name=""):
    """Compute the expected checked state (True/False/None) for one fee-waiver checkbox.

    Returns None when no rule matches. Descriptive native field names (e.g.
    "My employment", "SNAP", "SSI") are matched first because they are precise;
    otherwise the question/answer text around the box is used (for generic names
    and auto-detected checkboxes). Used both to fill the box and, independently,
    to verify it afterwards.
    """
    fin = data.get("financial_info") or {}

    def has(*keys):
        return any(bool(fin.get(k)) for k in keys)

    nm = (field_name or "").lower()

    # ---- 1. Field-name rules (precise, ordered so "social security" beats "ssi") ----
    if nm:
        income_source_names = [
            ("social security", "social_security_income"),
            ("child support", "child_support_income"),
            ("unemployment", "unemployment_income"),
            ("pension", "pension_income"),
            ("annuity", "pension_income"),
            ("alimony", "alimony_income"),
            ("spousal support", "alimony_income"),
            ("self-employment", "self_employment_income"),
            ("self employment", "self_employment_income"),
            ("business", "self_employment_income"),
            ("employment", "employment_income"),
            ("wages", "employment_income"),
            ("salary", "employment_income"),
        ]
        for k, key in income_source_names:
            if k in nm:
                return bool(fin.get(key))
        if "no income" in nm:
            return not has("employment_income", "monthly_gross_income")
        benefit_names = [
            ("snap", "receives_snap"), ("food stamp", "receives_snap"),
            ("medicaid", "receives_medicaid"), ("medical", "receives_medicaid"),
            ("ssi", "receives_ssi"), ("tanf", "receives_tanf"),
            ("aabd", "receives_tanf"), ("general assistance", "receives_tanf"),
        ]
        for k, key in benefit_names:
            if k in nm:
                return bool(fin.get(key))

    # ---- 2. Text/position rules (generic or auto-detected checkboxes) ----
    yesno_rules = [
        (("employed", "salary", "wage", "job", "work", "employment"),
         has("employment_income", "monthly_gross_income")),
        (("business", "profession", "self-employment", "self employment"),
         has("self_employment_income")),
        (("rent payment", "interest", "dividend"),
         has("rental_income", "interest_income", "dividend_income")),
        (("pension", "annuity", "life insurance", "retirement"),
         has("pension_income")),
        (("gift", "inherit"),
         has("gift_income", "other_income", "other_income_description")),
        (("other source", "other income", "any other"),
         has("other_income", "other_income_description")),
        (("cash", "checking", "savings", "account", "money", "bank", "funds"),
         has("checking_balance", "savings_balance", "cash_on_hand")),
        (("real estate", "automobile", "vehicle", "stock", "bond", "note"),
         has("vehicle_make_model", "real_estate_value")),
    ]
    income_source_text = [
        (("social security",), "social_security_income"),
        (("child support",), "child_support_income"),
        (("unemployment",), "unemployment_income"),
        (("pension", "annuity", "retirement"), "pension_income"),
        (("alimony", "spousal support"), "alimony_income"),
        (("self-employment", "self employment", "business"), "self_employment_income"),
        (("employment", "wages", "salary", "job"), "employment_income"),
    ]
    benefit_text = [
        (("snap", "food stamp", "food assistance"), bool(fin.get("receives_snap"))),
        (("medicaid", "medical assistance", "medical"), bool(fin.get("receives_medicaid"))),
        (("supp. security", "supp security", "supplemental security", "ssi"),
         bool(fin.get("receives_ssi"))),
        (("aid to the blind", "aid to blind"), bool(fin.get("receives_ssi"))),
        (("old age", "old-age"), bool(fin.get("receives_ssi"))),
        (("tanf", "family assistance", "general assistance", "public assistance"),
         bool(fin.get("receives_tanf"))),
    ]

    def _bbox(t):
        try:
            return (float(t[0]), float(t[1]), float(t[2]), float(t[3]), str(t[4]))
        except (TypeError, ValueError, IndexError):
            return (0.0, 0.0, 0.0, 0.0, "")

    words = [_bbox(x) for x in page.get_text("words")]
    clip = fitz.Rect(r.x0 - 220, r.y0 - 35, r.x1 + 90, r.y1 + 35)
    ctx = page.get_text("text", clip=clip).lower()
    cw = [x for x in words if x[1] < r.y1 + 8 and x[3] > r.y0 - 8
          and x[0] >= r.x0 - 220 and x[2] <= r.x1 + 90]

    # Yes/No pair
    yes_x = no_x = None
    for x in cw:
        if x[4].lower() == "yes":
            yes_x = x[0]
        elif x[4].lower() == "no":
            no_x = x[0]
    if yes_x is not None or no_x is not None:
        is_yes = no_x is None or r.x0 < no_x
        for kws, ans in yesno_rules:
            if any(k in ctx for k in kws):
                return (is_yes and ans) or (not is_yes and not ans)
        return None

    for kws, flag in benefit_text:
        if any(k in ctx for k in kws):
            return flag

    for kws, key in income_source_text:
        if any(k in ctx for k in kws):
            return bool(fin.get(key))

    return None


def _map_fee_waiver_checkboxes(doc: fitz.Document, data: dict) -> int:
    """Check fee-waiver Yes/No and benefit boxes from the intake financial data.

    Handles Yes/No pairs that share a single field name (e.g. two 'Check Box1'
    widgets — one for Yes, one for No) by using each widget's x-position relative
    to the printed 'Yes'/'No' labels.
    """
    checked = 0
    for page in doc:
        for w in page.widgets():
            w = cast(Any, w)
            if getattr(w, "field_type", None) != fitz.PDF_WIDGET_TYPE_CHECKBOX:
                continue
            r = fitz.Rect(w.rect)
            nm = str(getattr(w, "field_name", "") or "cb")
            if _expected_fee_waiver_checkbox(page, r, data, nm):
                try:
                    w.field_value = True
                    w.update()
                    checked += 1
                except Exception:
                    pass
    return checked


def _fill_form(data: dict, state: str, output_path: str, form_key: str) -> bool:
    """Fill a state's form (answer or fee waiver) — handles fillable AND scanned PDFs."""
    state_code = state.upper()
    config = get_state_config(state_code)
    if not config:
        logger.warning(f"No state config for {state_code}")
        return False

    form_filename = config.get(form_key)
    if not form_filename:
        logger.warning(f"No form configured for {state_code} ({form_key})")
        return False
    
    # County-specific form override: check if this county needs a different form
    county = (data.get("personal_info", {}) or {}).get("county", "").strip()
    county_overrides = config.get("county_form_overrides", {})
    if county and county in county_overrides and form_key == "answer_form":
        override = county_overrides[county]
        override_filename = override.get("answer_form")
        if override_filename:
            logger.info(f"Using county-specific form for {state_code}/{county}: {override_filename}")
            form_filename = override_filename
            # Merge overlay positions from override if present
            if override.get("overlay_positions"):
                config = {**config, "overlay_positions": {**config.get("overlay_positions", {}), **override["overlay_positions"]}}
            if override.get("field_mapping"):
                config = {**config, "field_mapping": {**config.get("field_mapping", {}), **override["field_mapping"]}}
            if override.get("has_fillable_fields") is not None:
                config = {**config, "has_fillable_fields": override["has_fillable_fields"]}

    # Use rebuilt form if available (clean standardized fields)
    form_path = _get_form_path(form_filename, state_code if form_key == "answer_form" else "")
    if not os.path.exists(form_path):
        logger.error(f"Form not found: {form_path}")
        return False

    p = data.get("personal_info", {})
    l = data.get("landlord_info", {})
    c = data.get("case_details", {})
    defenses = data.get("defenses", {})

    doc = fitz.open(form_path)
    
    # Check if form has fillable fields
    has_fields = False
    try:
        widgets_list = list(doc.load_page(0).widgets())
        fields_count = len(widgets_list)
        has_fields = fields_count > 0
    except Exception:
        pass

    has_overlay = bool(config.get("overlay_positions"))
    # For fee waiver forms, also check fee_waiver_overlay
    if form_key == "fee_waiver_form":
        has_overlay = has_overlay or bool(config.get("fee_waiver_overlay"))
    # Also check fee_waiver_mapping for fillable fee waiver PDFs
    if form_key == "fee_waiver_form" and config.get("fee_waiver_mapping"):
        has_fields = True  # Treat as fillable if mapping exists
    
    # Per-form field rect overrides: fix mispositioned native widgets (raw
    # pre-flip coordinates) before the y-flip below.
    overrides = (config.get("field_rect_overrides", {}) or {}).get(form_key, {})
    if overrides and has_fields:
        for page in doc:
            for w in page.widgets():
                w = cast(Any, w)
                o = overrides.get(str(getattr(w, "field_name", "") or ""))
                if not o:
                    continue
                r = w.rect
                if r is None:
                    continue
                w.rect = fitz.Rect(
                    o.get("x0", r.x0), o.get("y0", r.y0),
                    o.get("x1", r.x1), o.get("y1", r.y1))
                try:
                    w.update()
                except Exception:
                    pass

    # Native widget rects are already top-down (y=0 = top of page) in PyMuPDF's
    # Widget API, so do NOT flip y. Only shift caption/address/phone fields right
    # of their labels where the field starts on top of the label.
    if has_fields:
        for page in doc:
            PH = page.rect.height
            for w in page.widgets():
                w = cast(Any, w)
                r = w.rect
                if r is None or (r.y0 <= 0 and r.y1 >= PH):
                    continue
                nm = str(getattr(w, "field_name", "") or "").lower()
                if r.x0 < 90 and any(k in nm for k in ("plaintiff", "defendant", "printed")):
                    r = fitz.Rect(130, r.y0, r.x1, r.y1)
                elif 350 <= r.x0 <= 370 and any(k in nm for k in ("address", "phone")):
                    r = fitz.Rect(400, r.y0, r.x1, r.y1)
                w.rect = fitz.Rect(r.x0, r.y0, r.x1, r.y1)
                try:
                    w.update()
                except Exception:
                    pass

    if has_fields:
        # Native fillable form: fill its own fields only (no coordinate overlay,
        # which had misaligned positions and stamped text on top of printed text).
        _fill_via_widgets(doc, data, config)
    else:
        # Scanned/non-fillable form: stamp via coordinate overlay (top-down y).
        _fill_via_overlay(doc, data, config, form_key)
        # Scanned forms have no native fields — auto-detect every blank/checkbox
        # so the tenant can edit them. (Native forms already have editable fields;
        # running detection there adds duplicate boxes/fields.)
        _make_scanned_form_editable(doc, data)

    # Final safety net: every text field must wrap long input instead of clipping,
    # and any signature line must stay blank + non-editable (ink).
    _force_multiline_text_widgets(doc)
    _make_signature_fields_readonly(doc)

    if form_key == "fee_waiver_form":
        _map_fee_waiver_checkboxes(doc, data)

    doc.save(output_path, deflate=True)
    doc.close()
    logger.info(f"✅ {state_code} form saved: {output_path}")
    return True


def _fill_via_widgets(doc: fitz.Document, data: dict, config: dict):
    """Fill a PDF's form fields using widget/field mapping + smart auto-fill."""
    mapping = config.get("field_mapping", {})
    p = data.get("personal_info", {})
    l = data.get("landlord_info", {})
    c = data.get("case_details", {})
    defenses = data.get("defenses", {})
    today = date.today()
    
    values = {}
    
    # === UNIFIED MAPPING FOR REBUILT FORMS (standardized field names) ===
    # These work for ALL states with rebuilt forms — predictable, clean field names
    UNIFIED_MAP = {
        "defendant_name": p.get("full_name", ""),
        "plaintiff_name": l.get("landlord_name", ""),
        "case_number": c.get("case_number", ""),
        "court_name": c.get("court_name", ""),
        "county": p.get("county", ""),
        "property_address": p.get("property_address", ""),
        "phone": p.get("phone", ""),
        "email": p.get("email", ""),
        "date": today.strftime("%m/%d/%Y"),
        "printed_name": p.get("full_name", ""),
        "rent_amount": str(c.get("monthly_rent", "")),
        "amount_claimed": str(c.get("complaint_amount_claimed", "")),
    }
    
    # Defense checkboxes — universal names
    DEFENSE_UNIFIED = {
        "def_repairs": "defense_repairs",
        "def_amount": "defense_amount",
        "def_attempted_pay": "defense_attempted_pay",
        "def_paid": "defense_paid",
        "def_waived": "defense_waived",
        "def_retaliation": "defense_retaliation",
        "def_fair_housing": "defense_discrimination",
        "def_accepted_rent": "defense_accepted_rent",
        "def_corrected": "defense_corrected",
        "def_not_owner": "defense_not_owner",
        "def_bad_notice": "defense_bad_notice",
        "def_other": "defense_other",
    }
    
    for chatbot_key, std_name in DEFENSE_UNIFIED.items():
        d = defenses.get(chatbot_key, {})
        checked = d.get("checked", False) if isinstance(d, dict) else False
        if checked:
            values[std_name] = "Yes"
    
    for std_name, val in UNIFIED_MAP.items():
        if val:
            values[std_name] = str(val)
    
    # Defense narrative
    if defenses:
        narrative = _build_defense_narrative(defenses)
        values["defense_narrative"] = narrative
    
    # === LEGACY: Build _all_data for non-rebuilt forms that use field_mapping ===
    _all_data = {}
    for section in [p, l, c]:
        for k, v in section.items():
            if v:
                _all_data[k] = str(v)
    
    # Synthesize aliases — field_mapping keys must match _all_data keys
    aliases = {
        "full_name": ["name", "defendant_name", "printed_name"],
        "property_address": ["address", "street", "mailing_address", "property"],
        "property_city": ["city", "town"],
        "property_zip": ["zip", "postal_code"],
        "court_name": ["court_address", "courthouse", "court"],
        "landlord_name": ["plaintiff", "plaintiff_name", "landlord"],
        "phone": ["telephone", "phone_number", "cell"],
        "email": ["e_mail", "email_address"],
        "county": ["county_name"],
    }
    for source_key, target_keys in aliases.items():
        if source_key in _all_data:
            for tk in target_keys:
                if tk not in _all_data:
                    _all_data[tk] = _all_data[source_key]
    
    # Synthesize city_state_zip from city + state + zip
    state_code = data.get("state", "")
    if "property_city" in _all_data and "city_state_zip" not in _all_data:
        city = _all_data.get("property_city", "")
        zipcode = _all_data.get("property_zip", "")
        _all_data["city_state_zip"] = f"{city}, {state_code} {zipcode}".strip(", ")
    if "landlord_city_state_zip" not in _all_data:
        _all_data["landlord_city_state_zip"] = ""  # landlord city/state/zip rarely available

    # Case name for "Name of case" captions (e.g. CT): "Landlord v. Tenant"
    if "case_name" not in _all_data:
        _all_data["case_name"] = f"{_all_data.get('landlord_name', '')} v. {_all_data.get('full_name', '')}".strip(" v.")
    
    # Also add state-level data
    state_code = data.get("state", "")
    if state_code:
        _all_data["state"] = state_code
        _all_data["state_code"] = state_code
    
    # Certificate of Service mailing address — use property address as default
    if "cos_mail" not in _all_data and "property_address" in _all_data:
        _all_data["cos_mail"] = _all_data["property_address"]
    if "mailing_address" not in _all_data and "property_address" in _all_data:
        _all_data["mailing_address"] = _all_data["property_address"]
    
    # Certificate fields for CT, LA, and other states — derive from existing data
    cert_synthesis = {
        "cert_name": "full_name",
        "cert_address": "property_address", 
        "cert_date_signed": None,
        "cert_date": None,
        "cert_mail": "property_address",
        "cert_phone": "phone",
        "note": None,
        "notified": None,
        "code_violation": None,
        "date_offered": None,
        "date_note": None,
        "date_increase": None,
        "lease": None,
        "lease_renewal": None,
        "no_rent_due": None,
        "rent_increase": None,
        "rent_offered": None,
        "rent_paid": None,
        "rent_accepted": None,
        "status": None,
        "additional_info": None,
        "additional_reasons": None,
    }
    for cert_key, source_key in cert_synthesis.items():
        if cert_key not in _all_data:
            if source_key and source_key in _all_data:
                _all_data[cert_key] = _all_data[source_key]
            elif source_key is None:
                _all_data[cert_key] = ""
    
    # Set certificate dates to today
    today_str = date.today().strftime("%m/%d/%Y")
    for k in ["cert_date", "cert_date_signed"]:
        if k not in _all_data or not _all_data.get(k):
            _all_data[k] = today_str
    
    # Map each field_mapping key to a value from our data
    # Also make defense_narrative available for field_mapping
    if "defense_narrative" in values:
        _all_data["defense_narrative"] = values["defense_narrative"]
    for map_key, pdf_field in mapping.items():
        if map_key in _all_data:
            values[pdf_field] = str(_all_data[map_key])
    
    # Also apply fee_waiver_mapping if present (different field names for fee waivers)
    fw_mapping = config.get("fee_waiver_mapping", {})
    financial = data.get("financial_info", {})
    for map_key, pdf_field in fw_mapping.items():
        # Handle financial boolean fields as checkboxes
        if map_key.startswith("receives_") or map_key in ("income_below_threshold", "unable_to_pay_fees"):
            val = _get_financial_value(map_key, data)
            if val:
                values[pdf_field] = "Yes"
        elif map_key in _all_data:
            values[pdf_field] = str(_all_data[map_key])
        else:
            val = _get_financial_value(map_key, data)
            if val:
                values[pdf_field] = str(val)

    # Additional native fields that hold the tenant's full name (e.g. the "I, ___"
    # affidavit blank and the "Petitioner" line) beyond the single mapped name field.
    for fname in config.get("fee_waiver_name_fields", []):
        if fname not in values:
            values[fname] = p.get("full_name", "")
    
    # Date
    if "date" in mapping:
        values[mapping["date"]] = date.today().strftime("%m/%d/%Y")
    
    # Month/day/year handling
    today = date.today()
    if "month" in mapping:
        values[mapping["month"]] = str(today.month)
    if "day" in mapping:
        values[mapping["day"]] = str(today.day)
    if "year" in mapping:
        values[mapping["year"]] = str(today.year)
    
    # Handle defense checkboxes
    defense_opts = config.get("defense_options", [])
    
    # Defense key aliases — maps chatbot's standard keys to state-specific keys used in configs
    DEFENSE_ALIASES = {
        "def_repairs": ["def_repairs", "def_conditions", "def_failed_repair", "def_repair", "def_failed_maintain", "def_habitability", "def_disagree_6", "def_agree_6", "box 6.", "def_no_free_pay", "def_costs_not_rent", "def_deny_all"],
        "def_amount": ["def_amount", "def_amount_wrong", "def_disagree_amount", "def_no_rent_due", "def_not_owed", "def_dispute_amount", "def_disagree_5", "def_disagree_8", "8. disagree that", "def_admit_partial", "def_deny_all"],
        "def_attempted_pay": ["def_attempted_pay", "def_offered_pay", "def_offered_refused", "def_tried_to_pay", "def_refused_payment", "def_refused_rent", "def_partial_payment", "def_deny_all"],
        "def_paid": ["def_paid", "def_rent_paid", "def_rent_paid_full", "def_admit_all", "def_deny_all"],
        "def_waived": ["def_waived", "def_waiver", "def_deny_all"],
        "def_retaliation": ["def_retaliation", "def_disagree_7", "def_contest", "def_deny_all"],
        "def_fair_housing": ["def_fair_housing", "def_discrimination", "def_deny_all"],
        "def_accepted_rent": ["def_accepted_rent", "def_accepted_late", "def_foreclosure", "def_deny_all"],
        "def_corrected": ["def_corrected", "def_cured", "def_did_repairs", "def_moved_out", "def_deny_all"],
        "def_not_owner": ["def_not_owner", "def_landlord_not_entitled", "def_ownership", "def_disagree_4", "def_deny_all"],
        "def_bad_notice": ["def_bad_notice", "def_no_notice", "def_invalid", "def_improper_notice", "def_disagree_3", "def_late_fee", "def_deny_all"],
        "def_other": ["def_other", "def_other2", "def_other_defenses", "def_admit_all", "def_partial", "def_deny_all", "def_contest", "def_jury_trial", "def_no_breach", "def_lease_violation", "def_justifiable", "def_disagree_9", "def_disagree_10", "9. disagree", "10 disagree", "def_costs_not_rent", "def_no_free_pay", "def_late_fee", "def_foreclosure", "def_moved_out", "def_partial_payment", "def_discrimination"],
    }
    
    for opt in defense_opts:
        def_key = opt.get("key", "")
        field_name = opt.get("field", "")
        if def_key and field_name:
            # Check if any of our defense data matches this config key (or an alias)
            found_checked = False
            for standard_key, aliases in DEFENSE_ALIASES.items():
                if def_key in aliases:
                    def_data = defenses.get(standard_key, {})
                    checked = def_data.get("checked", False) if isinstance(def_data, dict) else False
                    if checked:
                        values[field_name] = "Yes"
                        found_checked = True
                    break
            # Also check direct match (for keys not in alias list)
            if not found_checked:
                def_data = defenses.get(def_key, {})
                checked = def_data.get("checked", False) if isinstance(def_data, dict) else False
                if checked:
                    values[field_name] = "Yes"
    
    # Static values: fixed text that doesn't come from user data
    # Used for fields like CA's "In Pro Per" attorney firm notation
    static_values = config.get("static_values", {})
    for pdf_field, static_text in static_values.items():
        values[pdf_field] = static_text

    # Smart auto-fill for common field names not in explicit mapping
    # Uses word-boundary matching to avoid false positives:
    #   "address" matches "AddressName2" but NOT "CourtAddress"
    #   "date" matches "Date3" but NOT "TrialDate" or "BOPDueDate"
    auto_fill_rules = [
        ("defendant", p.get("full_name", "")),
        ("plaintiff", l.get("landlord_name", "")),
        ("tenant", p.get("full_name", "")),
        ("landlord", l.get("landlord_name", "")),
        ("party1", l.get("landlord_name", "")),
        ("party2", p.get("full_name", "")),
        ("applicant", p.get("full_name", "")),
        ("case number", c.get("case_number", "")),
        ("case no", c.get("case_number", "")),
        ("file number", c.get("case_number", "")),
        ("docket", c.get("case_number", "")),
        ("phone", p.get("phone", "")),
        ("telephone", p.get("phone", "")),
        ("email", p.get("email", "")),
        ("county", p.get("county", "")),
        ("property", p.get("property_address", "")),
        ("street", p.get("property_address", "")),
        ("city or town", p.get("property_city", "")),
        ("signed", today.strftime("%m/%d/%Y")),
    ]
    # Word-boundary-only rules: match "Date" or "Date3" but not "TrialDate" or "BOPDueDate"
    # Also handles camelCase like "ResidenceAddress" → "address"
    import re
    word_boundary_rules = [
        (re.compile(r'(?<![a-zA-Z])address|(?<=[a-z])Address', re.IGNORECASE), p.get("property_address", "")),
        (re.compile(r'(?<![a-zA-Z])date(?![a-zA-Z])|(?<=[a-z])Date$', re.IGNORECASE), today.strftime("%m/%d/%Y")),
        (re.compile(r'(?<![a-zA-Z])court(?![a-zA-Z])', re.IGNORECASE), c.get("court_name", "")),
        (re.compile(r'(?<![a-zA-Z])city', re.IGNORECASE), p.get("property_city", "")),
    ]
    # Field names that should NOT receive auto-fill from substring rules
    auto_fill_skip = re.compile(r'(court|trial|bop|file|attorney|judge|jury).*(address|date)|'
                                r'landlord.*(accepted|date|payment|partial)|'
                                r'(notice|amount|date).*(landlord)|'
                                r'(damages|owes|reduced|repairs|amt|fees|costs|number|months)', re.IGNORECASE)
    
    # Apply to each page
    for page_num in range(len(doc)):
        page = doc[page_num]
        for widget in page.widgets():
            widget = cast(Any, widget)  # PyMuPDF widget: dynamic attributes
            field_name = cast(str, widget.field_name)
            if not field_name:
                continue
            if widget.field_type == fitz.PDF_WIDGET_TYPE_TEXT:
                widget.field_flags = (widget.field_flags or 0) | fitz.PDF_TX_FIELD_IS_MULTILINE
            
            # 1. Check explicit mapping first
            if field_name in values:
                widget.field_value = values[field_name]
                widget.update()
                continue
            
            # 1a. Substring matching for truncated widget names
            matched_substring = False
            for val_key, val_value in list(values.items()):
                if len(val_key) > 30 and len(field_name) > 20:
                    if field_name in val_key or val_key in field_name:
                        widget.field_value = val_value
                        widget.update()
                        matched_substring = True
                        break
            if matched_substring:
                continue
            
            # 1b. UNIVERSAL DEFAULTS: checkboxes that should always be set for pro se tenants
            fn_lower = field_name.lower()
            if 'generally denies' in fn_lower or 'general denial' in fn_lower:
                widget.field_value = "Yes"
                widget.update()
                continue
            
            # 1c. Try partial name matching for long XFA widget names
            # e.g., "form1[0].FRONT[0].CERTNAME[0]" should match values["CERTNAME[0]"]
            parts = field_name.rsplit('.', 1)
            if len(parts) == 2:
                short_name = parts[1]
                if short_name in values:
                    widget.field_value = values[short_name]
                    widget.update()
                    continue
            
            # 1d. Skip auto-fill for fields that have any explicit mapping
            if field_name in mapping.values() or field_name in fw_mapping.values():
                continue
            
            # 2. Try auto-fill rules on field name (substring match)
            if not field_name:
                continue
            # Skip fields that shouldn't get auto-filled (court/trial/attorney address/date)
            if auto_fill_skip.search(field_name):
                continue
            fn_lower = field_name.lower()
            matched = False
            for keyword, value in auto_fill_rules:
                if value and keyword in fn_lower:
                    widget.field_value = str(value)
                    widget.update()
                    matched = True
                    break
            if matched:
                continue
            # 3. Try word-boundary rules (exact word match, not substring)
            for pattern, value in word_boundary_rules:
                if value and pattern.search(field_name):
                    widget.field_value = str(value)
                    widget.update()
                    break


_LABEL_FIELDS = [
    ("court file number", "case_details", "case_number", False),
    ("case number", "case_details", "case_number", False),
    ("case type", "case_details", "division", False),
    ("county of", "personal_info", "county", False),
    ("judicial district", "case_details", "court_name", False),
    ("plaintiff", "landlord_info", "landlord_name", False),
    ("defendant", "personal_info", "full_name", False),
    ("address", "personal_info", "property_address", False),
    ("city, state, zip", "personal_info", "property_city_zip", False),
    ("phone", "personal_info", "phone", False),
    ("email", "personal_info", "email", False),
    ("rent or mortgage", "financial_info", "rent_or_mortgage", False),
    ("utilities", "financial_info", "utilities_expense", False),
    ("food", "financial_info", "food_expense", False),
    ("car payments", "financial_info", "transportation_expense", False),
    ("car insurance", "financial_info", "transportation_expense", False),
    ("childcare", "financial_info", "child_care_expense", False),
    ("medical insurance", "financial_info", "medical_expense", False),
    ("cell phone", "financial_info", "utilities_expense", False),
    ("cash", "financial_info", "cash_on_hand", False),
    ("accounts", "financial_info", "bank_total", False),
    ("total monthly income", "financial_info", "monthly_gross_income", False),
    ("average monthly income", "financial_info", "monthly_gross_income", False),
    ("household size", "financial_info", "household_size", False),
    ("ssi", "financial_info", "receives_ssi", True),
    ("snap", "financial_info", "receives_snap", True),
    ("medical assistance", "financial_info", "receives_medicaid", True),
    ("minnesotacare", "financial_info", "receives_medicaid", True),
    ("mfip", "financial_info", "receives_tanf", True),
    ("general assistance", "financial_info", "receives_tanf", True),
    ("energy", "financial_info", "receives_energy_assistance", True),
    ("job/wages", "financial_info", "employment_income", True),
    ("unemployment", "financial_info", "unemployment_income", True),
    ("social security", "financial_info", "social_security_income", True),
    ("child support", "financial_info", "child_support_income", True),
    ("spousal support", "financial_info", "alimony_income", True),
]


def _resolve_field_value(section: str, key: str, data: dict) -> str:
    if section is None:
        return ""
    d = data.get(section) or {}
    if key == "property_city_zip":
        return f"{d.get('property_city', '')}, {d.get('property_zip', '')}".strip(", ")
    if key == "bank_total":
        c = d.get("checking_balance") or 0
        s = d.get("savings_balance") or 0
        return f"{c + s:,.2f}" if (c or s) else ""
    if key == "household_size":
        a = d.get("household_adults") or 0
        ch = d.get("household_children") or 0
        return str(a + ch) if (a or ch) else ""
    v = d.get(key)
    if v is None:
        return ""
    if isinstance(v, bool):
        return "Yes" if v else ""
    return str(v)


def _match_label_field(label: Optional[str]):
    if not label:
        return None
    l = label.lower()
    for text, section, key, is_checkbox in _LABEL_FIELDS:
        if text in l:
            return (section, key, is_checkbox)
    return None


def _find_label_for_line(words, r) -> Optional[str]:
    best = None
    best_dist = None
    for w in words:
        x0, y0, x1, y1, word = w[0], w[1], w[2], w[3], w[4]
        if y1 <= r.y0 + 1 and y0 >= r.y0 - 24 and x0 <= r.x0 + 6:
            dist = (r.y0 - y1) + max(0, r.x0 - x1) * 0.05
            if best_dist is None or dist < best_dist:
                best_dist = dist
                best = word
        elif abs((y0 + y1) / 2 - r.y0) < 8 and x1 <= r.x0 + 2:
            dist = r.x0 - x1
            if best_dist is None or dist < best_dist:
                best_dist = dist
                best = word
    return best


def _is_signature_line(page, rect) -> bool:
    """True if text near rect is a signature/notary area (keep as ink, not editable)."""
    clip = fitz.Rect(rect.x0 - 60, rect.y0 - 14, rect.x1 + 160, rect.y1 + 14)
    txt = page.get_text("text", clip=clip).lower()
    return any(k in txt for k in ("signature", "notary", "affiant", "officer", "sworn", "subscribed", "witness", "deponent", "attesting"))


def _force_multiline_text_widgets(doc: fitz.Document) -> int:
    """Ensure every text widget is multiline so long input wraps instead of clipping.

    Native form fields (especially on fee-waiver forms) often carry only the
    rich-text flag or no flags at all, so a long value overflows a single line.
    This is a final, idempotent pass applied to every text widget regardless of
    how it was created (native AcroForm, overlay, or auto-detected blank).
    """
    changed = 0
    for page in doc:
        for w in page.widgets():
            w = cast(Any, w)
            if getattr(w, "field_type", None) != fitz.PDF_WIDGET_TYPE_TEXT:
                continue
            flags = getattr(w, "field_flags", 0) or 0
            if not (flags & fitz.PDF_TX_FIELD_IS_MULTILINE):
                w.field_flags = flags | fitz.PDF_TX_FIELD_IS_MULTILINE  # type: ignore[attr-defined]
                try:
                    w.update()
                except Exception:
                    pass
                changed += 1
    return changed


def _make_signature_fields_readonly(doc: fitz.Document) -> int:
    """Blank + read-only any text field that is actually a signature/notary line.

    Signature, notary, affiant, witness, sworn/subscribed, commission, and bank
    officer lines must stay ink (the tenant or the relevant officer signs by hand).
    Native form PDFs sometimes ship these as text fields with placeholders like
    ``/s/`` — we clear them and lock them so they stay blank and non-editable.
    Printed-name and date fields are left editable on purpose.
    """
    readonly = getattr(fitz, "PDF_FIELD_IS_READ_ONLY", 1)
    sig_words = ("sign", "notary", "affiant", "deponent", "witness",
                 "sworn", "subscribed", "attesting", "commission", "officer")
    exclude = ("print", "designat")
    locked = 0
    for page in doc:
        for w in page.widgets():
            w = cast(Any, w)
            if getattr(w, "field_type", None) != fitz.PDF_WIDGET_TYPE_TEXT:
                continue
            name = (getattr(w, "field_name", "") or "").lower()
            if not any(k in name for k in sig_words):
                continue
            if any(k in name for k in exclude):
                continue
            w.field_value = ""
            w.field_flags = (getattr(w, "field_flags", 0) or 0) | readonly  # type: ignore[attr-defined]
            # Some PDFs ship a '/s/' default (DV) that PyMuPDF's empty field_value
            # assignment won't override — force-clear the live /V key directly.
            try:
                doc.xref_set_key(int(w.xref), "V", "()")
            except Exception:
                pass
            try:
                w.update()
            except Exception:
                pass
            locked += 1
    return locked


def _make_scanned_form_editable(doc: fitz.Document, data: dict) -> None:
    """Add editable text/checkbox widgets at every blank + checkbox on a scanned form.

    Handles every blank representation: underscore runs, horizontal lines, rectangle
    boxes, and checkboxes drawn as "☐" glyphs or small vector squares. Signature/notary
    lines are left alone so the user signs with ink.
    """
    def _label_to_right(words, x0, y0, y1, maxdist=70) -> str:
        # Label usually sits to the right of the checkbox; some forms put it left.
        for w in words:
            wx0, wy0, wx1, wy1, word = w[0], w[1], w[2], w[3], w[4]
            if abs((wy0 + wy1) / 2 - (y0 + y1) / 2) < 6 and x0 - 1 <= wx0 <= x0 + maxdist:
                return str(word)
        for w in words:
            wx0, wy0, wx1, wy1, word = w[0], w[1], w[2], w[3], w[4]
            if abs((wy0 + wy1) / 2 - (y0 + y1) / 2) < 6 and x0 - maxdist <= wx1 <= x0 + 1:
                return str(word)
        return ""

    for pno in range(doc.page_count):
        page = doc[pno]
        PH = page.rect.height
        words = page.get_text("words")
        drawings = page.get_drawings()
        # Native widgets already on the page use top-down rects; flip them to the
        # page-content (bottom-up) space so auto-detection does not duplicate them.
        covered = [fitz.Rect(w.rect.x0, PH - w.rect.y1, w.rect.x1, PH - w.rect.y0)
                   for w in page.widgets() if w.rect is not None]

        def _flip(r):
            # page content is bottom-up; Widget.rect is top-down. Convert.
            return fitz.Rect(r.x0, PH - r.y1, r.x1, PH - r.y0)

        def _covered(rect, tol=4):
            r = fitz.Rect(rect.x0 - tol, rect.y0 - tol, rect.x1 + tol, rect.y1 + tol)
            return any(r.intersects(e) for e in covered)

        # 1. checkboxes drawn as "☐" glyphs
        for i, r in enumerate(page.search_for("\u2610")):
            rr = fitz.Rect(r.x0 - 1, r.y0 - 2, r.x1 + 1, r.y1 + 1)
            if _covered(rr):
                continue
            lb = _label_to_right(words, r.x1, r.y0, r.y1)
            m = _match_label_field(lb)
            _add_checkbox_widget(page, _flip(rr), f"cb_{pno}_{i}", m is not None and m[2] and _resolve_field_value(m[0], m[1], data) == "Yes")
            covered.append(rr)

        # 2. checkboxes drawn as small vector squares
        for i, dr in enumerate(drawings):
            r = dr["rect"]
            if 5 <= r.width <= 20 and 5 <= r.height <= 20 and abs(r.width - r.height) <= 5:
                if _covered(r):
                    continue
                lb = _label_to_right(words, r.x1, r.y0, r.y1)
                m = _match_label_field(lb)
                _add_checkbox_widget(page, _flip(r), f"vcb_{pno}_{i}", m is not None and m[2] and _resolve_field_value(m[0], m[1], data) == "Yes")
                covered.append(r)

        # 3. underscore runs -> text fields
        raw = page.get_text("rawdict")
        runs = []
        for blk in raw.get("blocks", []):
            if blk.get("type") != 0:
                continue
            for ln in blk.get("lines", []):
                for sp in ln.get("spans", []):
                    cur = []
                    for ch in sp.get("chars", []):
                        if ch["c"] == "_":
                            cur.append(ch["bbox"])
                        else:
                            if cur:
                                runs.append(cur); cur = []
                    if cur:
                        runs.append(cur)
        # Merge vertically-stacked underscore runs into ONE field so a multi-line
        # blank accepts the full input across every line (instead of one field
        # per underscore line, which clips long input to a single line).
        bboxes = []
        for run in runs:
            if len(run) < 3:
                continue
            bboxes.append([min(b[0] for b in run), max(b[2] for b in run),
                           min(b[1] for b in run), max(b[3] for b in run)])
        merged = []
        for bb in sorted(bboxes, key=lambda b: -b[3]):  # top-to-bottom
            placed = False
            for m in merged:
                if (abs(bb[0] - m[0]) < 8 and abs(bb[1] - m[1]) < 8
                        and 0 <= (m[2] - bb[3]) < 24):
                    m[0] = min(m[0], bb[0]); m[1] = max(m[1], bb[1])
                    m[2] = min(m[2], bb[2])
                    placed = True
                    break
            if not placed:
                merged.append(bb[:])
        for i, (x0, x1, y0, y1) in enumerate(merged):
            r = fitz.Rect(x0, y0 - 6, max(x1, x0 + 48), y1 + 4)
            if _covered(r) or _is_signature_line(page, r):
                continue
            _add_text_widget(page, _flip(r), f"ufill_{pno}_{i}", "")
            covered.append(r)

        # 4. horizontal lines -> text fields
        for i, dr in enumerate([d for d in drawings if d["rect"].height < 3 and d["rect"].width > 15]):
            r = dr["rect"]
            if _covered(r) or _is_signature_line(page, r):
                continue
            _add_text_widget(page, _flip(r), f"fill_{pno}_{i}", "")
            covered.append(r)

        # 5. rectangle boxes -> text fields
        for i, dr in enumerate([d for d in drawings if d["rect"].width > 40 and 3 <= d["rect"].height <= 30]):
            r = dr["rect"]
            if _covered(r):
                continue
            _add_text_widget(page, _flip(r), f"bfill_{pno}_{i}", "")
            covered.append(r)


def _add_text_widget(page, rect, name: str, value: str, font_size: float = 10) -> None:
    """Add a pre-filled, editable text field at the given rect."""
    if rect.x1 <= rect.x0 or rect.y1 <= rect.y0:
        return
    if rect.height < 10:
        rect = fitz.Rect(rect.x0, rect.y0 - 12, rect.x1, rect.y0 + 4)
    w = cast(Any, fitz.Widget())
    w.field_name = name
    w.field_type = fitz.PDF_WIDGET_TYPE_TEXT  # type: ignore[attr-defined]
    w.rect = rect
    w.field_value = str(value)
    w.field_flags = fitz.PDF_TX_FIELD_IS_MULTILINE  # type: ignore[attr-defined]
    page.add_widget(w)


def _add_checkbox_widget(page, rect, name: str, checked: bool = True) -> None:
    """Add an editable checkbox at the given rect."""
    if rect.x1 <= rect.x0 or rect.y1 <= rect.y0:
        return
    w = cast(Any, fitz.Widget())
    w.field_name = name
    w.field_type = fitz.PDF_WIDGET_TYPE_CHECKBOX  # type: ignore[attr-defined]
    w.rect = rect
    w.field_value = bool(checked)
    page.add_widget(w)


def _fill_via_overlay(doc: fitz.Document, data: dict, config: dict, form_key: str = "answer_form"):
    """Overlay text on scanned/non-fillable PDFs using coordinate positions.
    
    For fee waivers, uses fee_waiver_overlay if available, otherwise falls back
    to overlay_positions. Falls back to stamping info at the top of the form.
    """
    p = data.get("personal_info", {})
    l = data.get("landlord_info", {})
    c = data.get("case_details", {})
    
    # For fee waivers, use fee_waiver_overlay ONLY — don't fall back to answer form positions
    if form_key == "fee_waiver_form":
        positions = dict(config.get("fee_waiver_overlay", {}))
    else:
        # Answer form uses its own overlay positions only. fee_waiver_overlay
        # describes the *separate* fee-waiver PDF and must not override the
        # answer form's caption fields (same key, different page/position).
        positions = dict(config.get("overlay_positions", {}))
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        existing_rects = [w.rect for w in page.widgets()]
        
        if positions:
            # overlay_positions store y from the TOP of the page, which matches
            # PyMuPDF's Widget.rect convention (y=0 = top). Use it directly.
            for key, pos in positions.items():
                if pos.get("page", 1) - 1 != page_num:
                    continue
                x = pos["x"]
                w = pos.get("w", 200)
                h = pos.get("h", 20)
                y = pos["y"]
                _pr = fitz.Rect(x, y, x + w, y + h)
                if any(_pr.intersects(r) for r in existing_rects):
                    continue  # already filled via a fillable widget (rebuilt form)
                value = _get_field_value(key, data)
                # Check if this is a defense checkbox (small overlay rect)
                is_checkbox = key.startswith("def_") and pos.get("h", 20) <= 20
                if is_checkbox:
                    s = pos.get("h", 14)
                    _add_checkbox_widget(page, fitz.Rect(x, y, x + s, y + s), key, checked=bool(value))
                elif value:
                    _add_text_widget(page, _pr, key, str(value), font_size=pos.get("size", 10))




def _get_field_value(key: str, data: dict) -> Optional[str]:
    """Get a value from the nested data dict by key path.
    
    Handles regular data fields, defense checkbox overlay keys, and narrative text.
    When key starts with 'def_', returns 'X' if the defense is checked (triggers checkmark).
    When key is 'defense_narrative', returns formatted defense explanation text.
    """
    p = data.get("personal_info", {})
    l = data.get("landlord_info", {})
    c = data.get("case_details", {})
    defenses = data.get("defenses", {})
    
    mapper = {
        "full_name": p.get("full_name"),
        "defendant_name": p.get("full_name"),
        "printed_name": p.get("full_name"),
        "phone": p.get("phone"),
        "phone_bottom": p.get("phone"),
        "email": p.get("email"),
        "address": p.get("property_address"),
        "property_address": p.get("property_address"),
        "city": p.get("property_city"),
        "zip": p.get("property_zip"),
        "city_state_zip": f"{p.get('property_city', '')}, {data.get('state', '')} {p.get('property_zip', '')}".strip(", "),
        "county": p.get("county"),
        "court_type": "Magistrate Court",  # default, overridden for Bernalillo County
        "landlord_name": l.get("landlord_name"),
        "plaintiff_name": l.get("landlord_name"),
        "landlord_address": l.get("landlord_address"),
        "landlord_phone": l.get("landlord_phone"),
        "landlord_email": l.get("landlord_email"),
        "case_number": c.get("case_number"),
        "court_name": c.get("court_name"),
        "monthly_rent": str(c.get("monthly_rent", "")),
        "amount_demanded": str(c.get("notice_amount_demanded", "")),
    }
    
    # Handle defense narrative text generation
    if key == "defense_narrative":
        return _build_defense_narrative(defenses)
    
    # Handle numbered defense narrative lines (NM 4-907 style)
    if key.startswith("defense_narrative_"):
        try:
            idx = int(key.split("_")[-1]) - 1  # defense_narrative_1 → index 0
        except (ValueError, IndexError):
            idx = 0
        checked_defenses = [
            ("def_repairs", "Conditions: "),
            ("def_amount", "Amount disputed: "),
            ("def_attempted_pay", "Tried to pay: "),
            ("def_paid", "Already paid: "),
            ("def_waived", "Waiver: "),
            ("def_retaliation", "Retaliation: "),
            ("def_fair_housing", "Discrimination: "),
            ("def_accepted_rent", "Accepted rent: "),
            ("def_corrected", "Corrected issue: "),
            ("def_not_owner", "Not proper owner: "),
            ("def_bad_notice", "Defective notice: "),
            ("def_other", "Other: "),
        ]
        active = []
        for def_key, label in checked_defenses:
            d = defenses.get(def_key, {})
            if isinstance(d, dict) and d.get("checked"):
                expl = d.get("explanation", "")
                active.append(f"{label}{expl}" if expl else label)
        if idx < len(active):
            return active[idx][:100]  # fit within form line
        return None
    
    # Handle financial summary for overlay fee waiver forms
    if key == "financial_summary":
        return _build_financial_summary(data.get("financial_info", {}))
    
    # Handle defense checkbox overlay keys
    if key.startswith("def_"):
        # Map aliases for state-specific defense keys
        DEFENSE_ALIASES = {
            "def_not_owner2": "def_not_owner",
            "def_victim_status": "def_other",
            "def_rental_assistance": "def_other",
            "def_dismiss": "def_other",
            "def_counterclaim": "def_other",
            "def_failure_mitigate": "def_other",
            "def_wrong_reason": "def_bad_notice",
            "def_moved_out": "def_other",
            "def_foreclosure": "def_other",
            "def_pre_termination": "def_other",
            "def_other2": "def_other",
        }
        lookup_key = DEFENSE_ALIASES.get(key, key)
        def_data = defenses.get(lookup_key, {})
        checked = def_data.get("checked", False) if isinstance(def_data, dict) else False
        if checked:
            return "X"  # triggers overlay to draw checkmark lines
        return None
    
    return mapper.get(key)


def _get_financial_value(key: str, data: dict) -> Optional[str]:
    """Get a value from the FinancialInfo section for fee waiver forms.
    
    Returns formatted string for text fields, or "Yes" for boolean checkboxes.
    """
    financial = data.get("financial_info", {})
    if not financial:
        return None
    
    # Boolean checkbox fields
    bool_fields = ["receives_public_benefits", "receives_snap", "receives_ssi", "receives_medicaid",
                   "receives_tanf", "receives_section8", "receives_public_housing",
                   "receives_county_assistance", "receives_energy_assistance",
                   "receives_veterans_benefits", "receives_child_care_assistance",
                   "income_below_threshold", "unable_to_pay_fees", "owns_real_estate",
                   "has_requested_fee_waiver_before"]
    if key in bool_fields:
        val = financial.get(key, False)
        return "Yes" if val else None
    
    # Numeric fields — format as dollar amounts
    dollar_fields = ["monthly_gross_income", "monthly_net_income", "employment_income",
                     "self_employment_income", "social_security_income", "ssi_income",
                     "unemployment_income", "pension_income", "disability_income",
                     "veterans_benefits", "child_support_income", "alimony_income",
                     "other_income", "rent_or_mortgage", "utilities_expense",
                     "food_expense", "transportation_expense", "medical_expense",
                     "child_care_expense", "debt_payments", "other_expenses",
                     "total_monthly_expenses", "cash_on_hand", "checking_balance",
                     "savings_balance", "vehicle_value", "vehicle_loan_owed",
                     "real_estate_value", "real_estate_loan_owed", "other_assets_value"]
    if key in dollar_fields:
        val = financial.get(key)
        # Fallback: employment_income from monthly_gross_income
        if val is None and key == "employment_income":
            val = financial.get("monthly_gross_income")
        if val is not None and val != 0:
            return f"{_money(val, 2)}"
        return None
    
    # Text fields
    text_fields = ["vehicle_make_model", "other_income_description", "other_assets_description",
                   "previous_fee_waiver_case"]
    if key in text_fields:
        val = financial.get(key)
        return str(val) if val else None
    
    # Household numbers
    if key in ["household_adults", "household_children", "total_dependents"]:
        val = financial.get(key)
        return str(val) if val is not None else None
    
    # Computed summary fields
    if key == "assets_description":
        parts = []
        vehicle = financial.get("vehicle_make_model")
        vehicle_val = financial.get("vehicle_value")
        if vehicle:
            parts.append(f"Vehicle: {vehicle}" + (f" ({_money(vehicle_val, 0)})" if vehicle_val else ""))
        checking = financial.get("checking_balance")
        if checking:
            parts.append(f"Checking: {_money(checking, 2)}")
        savings = financial.get("savings_balance")
        if savings:
            parts.append(f"Savings: {_money(savings, 2)}")
        cash = financial.get("cash_on_hand")
        if cash:
            parts.append(f"Cash: {_money(cash, 2)}")
        if financial.get("owns_real_estate"):
            re_val = financial.get("real_estate_value")
            parts.append(f"Real estate" + (f" ({_money(re_val, 0)})" if re_val else ""))
        return "; ".join(parts) if parts else None
    if key == "obligations_description":
        parts = []
        debt = financial.get("debt_payments")
        if debt:
            parts.append(f"Monthly debt payments: {_money(debt, 2)}")
        vehicle_loan = financial.get("vehicle_loan_owed")
        if vehicle_loan:
            parts.append(f"Vehicle loan balance: {_money(vehicle_loan, 2)}")
        re_loan = financial.get("real_estate_loan_owed")
        if re_loan:
            parts.append(f"Mortgage balance: {_money(re_loan, 2)}")
        return "; ".join(parts) if parts else None

    # Computed totals (for GN10-style "Total Assets" / "Total Debts" fields)
    if key == "total_assets":
        asset_vals = [
            financial.get("cash_on_hand"),
            financial.get("checking_balance"),
            financial.get("savings_balance"),
            financial.get("vehicle_value"),
            financial.get("real_estate_value"),
            financial.get("other_assets_value"),
        ]
        total = sum(_to_float(v) for v in asset_vals if v)
        return f"${total:,.2f}" if total else None

    if key == "total_debts":
        debt_vals = [
            financial.get("real_estate_loan_owed"),
            financial.get("vehicle_loan_owed"),
        ]
        total = sum(_to_float(v) for v in debt_vals if v)
        return f"${total:,.2f}" if total else None

    return None


def _build_financial_summary(financial: dict) -> str:
    """Build a formatted summary of financial data for overlay fee waiver forms."""
    if not financial:
        return ""
    
    lines = []
    
    # Income
    income = financial.get('monthly_gross_income')
    if income:
        lines.append(f"Monthly Gross Income: {_money(income, 2)}")
    emp = financial.get('employment_income')
    if emp:
        lines.append(f"Employment: {_money(emp, 2)}")
    
    # Household
    adults = financial.get('household_adults', 1)
    children = financial.get('household_children', 0)
    lines.append(f"Household: {adults} adult(s), {children} child(ren)")
    
    # Benefits
    benefits = []
    if financial.get('receives_snap'): benefits.append('SNAP')
    if financial.get('receives_ssi'): benefits.append('SSI')
    if financial.get('receives_medicaid'): benefits.append('Medicaid')
    if financial.get('receives_tanf'): benefits.append('TANF')
    if financial.get('receives_section8'): benefits.append('Section 8')
    if benefits:
        lines.append(f"Public Benefits: {', '.join(benefits)}")
    
    # Expenses
    rent = financial.get('rent_or_mortgage')
    if rent:
        lines.append(f"Rent/Mortgage: {_money(rent, 2)}")
    total_exp = financial.get('total_monthly_expenses')
    if total_exp:
        lines.append(f"Total Monthly Expenses: {_money(total_exp, 2)}")
    
    # Assets
    cash_val = financial.get('cash_on_hand')
    if cash_val:
        lines.append(f"Cash on Hand: {_money(cash_val, 2)}")
    checking = financial.get('checking_balance')
    if checking:
        lines.append(f"Checking: {_money(checking, 2)}")
    savings = financial.get('savings_balance')
    if savings:
        lines.append(f"Savings: {_money(savings, 2)}")
    vehicle = financial.get('vehicle_make_model')
    if vehicle:
        vehicle_val = financial.get('vehicle_value')
        lines.append(f"Vehicle: {vehicle} ({_money(vehicle_val, 2)})" if vehicle_val else f"Vehicle: {vehicle}")
    
    return '\n'.join(lines)


def _build_defense_narrative(defenses: dict) -> str:
    """Build a formatted paragraph of defense explanations from checked defenses.
    Used for narrative court forms (AR, NM, TN) that have blank text areas.
    """
    DEFENSE_LABELS = {
        "def_repairs": "The landlord failed to make necessary repairs to the property despite being notified. "
                       "This includes [describe specific repair issues].",
        "def_did_repairs": "I made repairs to the property that the landlord should have made, "
                          "and I am entitled to deduct these costs from rent.",
        "def_amount": "I dispute the amount of rent the landlord claims I owe. "
                      "I believe the correct amount is [state amount and reason].",
        "def_paid": "I have already paid the rent that the landlord claims is owed. "
                    "I have proof of payment including [describe receipts, bank statements, etc.].",
        "def_attempted_pay": "I tried to pay my rent but the landlord refused to accept payment. "
                           "I made a good faith effort to pay on [date(s)].",
        "def_retaliation": "The landlord is evicting me in retaliation for exercising my legal rights. "
                         "Specifically, after I [complained to code enforcement / requested repairs / etc.], "
                         "the landlord filed this eviction.",
        "def_discrimination": "The eviction is discriminatory and violates fair housing laws. "
                             "I believe I am being treated differently because of [protected characteristic].",
        "def_bad_notice": "The landlord did not provide proper legal notice before filing this eviction. "
                         "The notice was [defective / not served properly / missing required information].",
        "def_landlord_breach": "The landlord breached the rental agreement by [describe violation].",
        "def_not_owner": "The person or company suing me is not the actual owner of the property.",
        "def_waived": "The landlord waived the right to evict by [accepting rent after notice / telling me I could stay / etc.].",
        "def_accepted_rent": "The landlord accepted my rent payment after sending the eviction notice, "
                            "which cancels the eviction.",
        "def_corrected": "I corrected the lease violation that the landlord complained about before the deadline.",
        "def_other": "I have additional reasons why I should not be evicted. [Describe here].",
        "def_contest": "This court does not have proper jurisdiction over this case.",
        "def_dismiss": "The complaint should be dismissed because [state reason].",
    }
    
    checked = []
    for key, label in DEFENSE_LABELS.items():
        d = defenses.get(key, {})
        if isinstance(d, dict) and d.get("checked"):
            explanation = d.get("explanation", "")
            text = label
            if explanation:
                # Replace placeholder with actual explanation
                text = text.replace("[describe specific repair issues]", explanation)
                text = text.replace("[state amount and reason]", explanation)
                text = text.replace("[describe receipts, bank statements, etc.]", explanation)
                text = text.replace("[date(s)]", explanation)
                text = text.replace("[complained to code enforcement / requested repairs / etc.]", explanation)
                text = text.replace("[protected characteristic]", explanation)
                text = text.replace("[defective / not served properly / missing required information]", explanation)
                text = text.replace("[describe violation]", explanation)
                text = text.replace("[accepting rent after notice / telling me I could stay / etc.]", explanation)
                text = text.replace("[Describe here]", explanation)
                text = text.replace("[state reason]", explanation)
            checked.append(text)
    
    if not checked:
        return "The defendant requests that the court deny the eviction and allow the defendant to remain in possession of the premises."
    
    # Number the defenses
    lines = []
    for i, def_text in enumerate(checked, 1):
        lines.append(f"{i}. {def_text}")
    
    return "\n\n".join(lines)
