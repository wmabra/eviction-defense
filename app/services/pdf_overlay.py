"""
PDF overlay system — fills any court form, even scanned/non-fillable PDFs.

For fillable PDFs: uses field mapping (fast, precise).
For scanned PDFs: overlays text at exact coordinates (works on any form).
"""
# pyright: reportAttributeAccessIssue=false, reportOptionalMemberAccess=false

import os
import re
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


import pymupdf

from app.services.state_configs import get_state_config

SC_COUNTY_TO_CIRCUIT = {
    "calhoun": "First", "dorchester": "First", "orangeburg": "First",
    "aiken": "Second", "bamberg": "Second", "barnwell": "Second",
    "clarendon": "Third", "claredon": "Third", "lee": "Third", "sumter": "Third", "williamsburg": "Third",
    "chesterfield": "Fourth", "darlington": "Fourth", "dillon": "Fourth", "marlboro": "Fourth",
    "kershaw": "Fifth", "richland": "Fifth",
    "chester": "Sixth", "fairfield": "Sixth", "lancaster": "Sixth",
    "cherokee": "Seventh", "spartanburg": "Seventh",
    "abbeville": "Eighth", "greenwood": "Eighth", "laurens": "Eighth", "newberry": "Eighth",
    "berkeley": "Ninth", "charleston": "Ninth",
    "anderson": "Tenth", "oconee": "Tenth",
    "edgefield": "Eleventh", "lexington": "Eleventh", "mccormick": "Eleventh", "saluda": "Eleventh",
    "florence": "Twelfth", "marion": "Twelfth", "mariojn": "Twelfth",
    "greenville": "Thirteenth", "pickens": "Thirteenth",
    "allendale": "Fourteenth", "beaufort": "Fourteenth", "colleton": "Fourteenth", "hampton": "Fourteenth", "jasper": "Fourteenth",
    "georgetown": "Fifteenth", "horry": "Fifteenth",
    "union": "Sixteenth", "york": "Sixteenth",
}

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


def _expected_fee_waiver_checkbox(page, r, data, field_name="", on_state="", trust_on_state=False, checkbox_map=None):
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
            if re.search(rf'\b{re.escape(k)}\b', nm):
                return bool(fin.get(key))
        if "no income" in nm:
            return not has("employment_income", "monthly_gross_income")
        if "other means tested" in nm:
            return bool(fin.get("receives_other_assistance") or fin.get("other_assistance_description"))
        if "unable to pay the fees" in nm or "did not check item 1 or 2" in nm:
            cat_keys = ("receives_snap", "receives_ssi", "receives_tanf", "receives_medicaid", "receives_public_benefits")
            return not any(bool(fin.get(k)) for k in cat_keys)
        benefit_names = [
            ("snap", "receives_snap"), ("food stamp", "receives_snap"),
            ("food assistance", "receives_snap"),
            ("general assistance", "receives_tanf"),
            ("receive public assistance", "receives_public_benefits"),
            ("medicaid", "receives_medicaid"), ("medical", "receives_medicaid"),
            ("ssi", "receives_ssi"), ("tanf", "receives_tanf"),
            ("aabd", "receives_tanf"),
            ("family independence", "receives_tanf"),  # MI TANF (SCAO MC 20)
            ("women infants", "receives_wic"),  # MI WIC (SCAO MC 20)
        ]
        for k, key in benefit_names:
            if re.search(rf'\b{re.escape(k)}\b', nm):
                return bool(fin.get(key))

        # LA IFP Question 7(a): pay frequency — check exactly one box. Spouse
        # rows stay off for a single-tenant intake.
        if "paid" in nm and ("weekly" in nm or "monthly" in nm):
            if "spouse" in nm:
                return False
            _pay_freq = (fin.get("pay_frequency") or "monthly").lower()
            if "bi" in nm:
                return _pay_freq in ("bi-weekly", "biweekly")
            if "weekly" in nm:
                return _pay_freq == "weekly"
            return _pay_freq == "monthly"

        # KY AOC-026 page-1 expense-type checkboxes (rent vs mortgage).
        if nm in ("check box 3", "check box3") and 480 < r.y0 < 500:
            return bool(fin.get("rent_or_mortgage")) and not fin.get("owns_real_estate")
        if nm in ("check box 2", "check box2") and 480 < r.y0 < 500:
            return bool(fin.get("owns_real_estate"))

    # ---- 2. Text/position rules (generic or auto-detected checkboxes) ----
    # Income-source Yes/No rows map to a specific financial key so a tenant with
    # no such income gets "No" (not an ambiguous unchecked/checked pair). These
    # are checked BEFORE the asset/housing rules below so a specific source like
    # "workers compensation" or "child support" wins over broad keywords.
    income_source_yesno = [
        (("workers compensation", "workers comp", "workers' comp"), "other_income"),
        (("insurance benefits", "insurance proceeds"), "other_income"),
        (("pension", "annuity", "retirement"), "pension_income"),
        (("child support",), "child_support_income"),
        (("alimony", "spousal support"), "alimony_income"),
        (("social security",), "social_security_income"),
        (("unemployment",), "unemployment_income"),
        (("self-employment", "self employment", "business", "profession"),
         "self_employment_income"),
        (("interest", "dividend"), "other_income"),
        (("gift", "inherit"), "other_income"),
        (("other source", "other income", "any other"), "other_income"),
    ]
    yesno_rules = [
        (("employed", "salary", "wage", "job", "employment"),
         has("employment_income", "self_employment_income") or bool(fin.get("is_employed"))),
        (("rent or mortgage", "rent or own", "pay rent"),
         bool(fin.get("rent_or_mortgage")) and not fin.get("owns_real_estate")),
        (("mortgage", "home loan"),
         bool(fin.get("owns_real_estate")) or bool(fin.get("real_estate_loan_owed"))),
        (("cash", "checking", "savings", "account", "money", "bank", "funds"),
         has("checking_balance", "savings_balance", "cash_on_hand")),
        (("automobile", "vehicle", "car", "truck"),
         has("vehicle_make_model", "vehicle_value")),
        (("real estate", "home or other", "own a home"),
         has("real_estate_value", "real_estate_loan_owed", "owns_real_estate")),
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
        # Parent "I receive public assistance" branch: check it when ANY benefit
        # is received. Keep this FIRST so the parent row (which also lists the
        # first program, e.g. "SSI", on the next line) isn't short-circuited by
        # the specific-benefit rules below.
        (("public assistance", "public benefits", "government entitlements", "receive these public"), bool(fin.get("receives_snap") or fin.get("receives_medicaid") or
                                      fin.get("receives_ssi") or fin.get("receives_tanf") or
                                      fin.get("receives_public_benefits"))),
        (("snap", "food stamp", "food assistance"), bool(fin.get("receives_snap"))),
        (("medicaid", "medical assistance", "medical"), bool(fin.get("receives_medicaid"))),
        (("supp. security", "supp security", "supplemental security", "ssi"),
         bool(fin.get("receives_ssi"))),
        (("aid to the blind", "aid to blind"), bool(fin.get("receives_ssi"))),
        (("old age", "old-age"), bool(fin.get("receives_ssi"))),
        (("tanf", "family assistance", "general assistance"), bool(fin.get("receives_tanf"))),
        (("chip",), bool(fin.get("receives_chip"))),
        (("wic",), bool(fin.get("receives_wic"))),
        (("aabd",), bool(fin.get("receives_aabd"))),
        (("public housing", "section 8"), bool(fin.get("receives_public_housing") or fin.get("receives_section8"))),
        (("energy assistance", "low-income energy"), bool(fin.get("receives_energy_assistance"))),
    ]

    def _bbox(t):
        try:
            return (float(t[0]), float(t[1]), float(t[2]), float(t[3]), str(t[4]))
        except (TypeError, ValueError, IndexError):
            return (0.0, 0.0, 0.0, 0.0, "")

    words = [_bbox(x) for x in page.get_text("words")]
    cy = (r.y0 + r.y1) / 2
    cw = [x for x in words if abs((x[1] + x[3]) / 2 - cy) < 6
          and x[0] >= 70 and x[2] <= 590]
    # Match keywords only against words on the checkbox's own row (within 6pt
    # of checkbox vertical center) so labels from adjacent rows can't leak into
    # this checkbox's question text.
    ctx = " ".join(str(x[4]) for x in cw).lower()

    # Find other checkboxes on the same row to bound local text strictly
    other_cbs = [w.rect for w in page.widgets() if getattr(w, "field_type", None) == pymupdf.PDF_WIDGET_TYPE_CHECKBOX and w.rect]
    same_row_after = [o for o in other_cbs if abs((o.y0 + o.y1) / 2 - (r.y0 + r.y1) / 2) < 7 and o.x0 > r.x1]
    next_x = min([o.x0 for o in same_row_after]) if same_row_after else r.x1 + 80
    max_x = min(r.x1 + 80, next_x)
    cw_local = [x for x in words if abs((x[1] + x[3]) / 2 - (r.y0 + r.y1) / 2) < 7 and r.x1 - 2 <= x[0] < max_x]
    ctx_local = " ".join(str(x[4]) for x in cw_local).lower()

    # Yes/No pair — decide which side this box is by proximity to the printed
    # labels. on_state is unreliable here: some templates give every box in a
    # pair the same on_state (e.g. both report "Yes"), which made both halves
    # check at once.
    yes_x = no_x = None
    # Yes/No labels sit on the checkbox's own printed line ("[ ] Yes [ ] No").
    # Detect them from a TIGHT vertical band: a helper line just below the box
    # (e.g. "If yes, please list all other income sources...") contains the word
    # "yes," and would otherwise overwrite the real label x-position.
    for x in words:
        if not (x[1] < r.y1 + 2 and x[3] > r.y0 - 8 and x[0] >= 70 and x[2] <= 590):
            continue
        _w = str(x[4]).lower().strip("[](),.:;?")
        if _w == "yes":
            yes_x = x[0]
        elif _w == "no":
            no_x = x[0]
    if yes_x is not None and no_x is not None:
        _os = (on_state or "").strip().lower()
        if nm.endswith("- yes") or nm.endswith(" yes"):
            is_yes = True
        elif nm.endswith("- no") or nm.endswith(" no"):
            is_yes = False
        elif trust_on_state and _os == "yes":
            is_yes = True
        elif trust_on_state and _os == "no":
            is_yes = False
        else:
            is_yes = abs(r.x0 - yes_x) < abs(r.x0 - no_x)
        # Guard: a "spouse employed?" question must not use the applicant's own
        # employment income (KY AOC-026 Item 4 otherwise falsely swears the
        # spouse works). A single tenant has no spouse_income -> "No".
        if "spouse" in ctx and any(k in ctx for k in ("employed", "salary", "work")):
            _spouse_employed = bool(fin.get("spouse_income"))
            return (is_yes and _spouse_employed) or (not is_yes and not _spouse_employed)
        # Explicit per-form Yes/No map (e.g. AR's "Check BoxN" financial
        # indicators whose question text sits on the line above the box).
        if checkbox_map and field_name in checkbox_map:
            _keys = checkbox_map[field_name]
            _ans = any(bool(fin.get(k)) for k in _keys) if _keys else False
            return (is_yes and _ans) or (not is_yes and not _ans)
        for kws, key in income_source_yesno:
            if any(k in ctx for k in kws):
                _ans = bool(fin.get(key))
                return (is_yes and _ans) or (not is_yes and not _ans)
        for kws, ans in yesno_rules:
            if any(k in ctx for k in kws):
                # KY AOC-026 "Are you employed?" prints three boxes — "Yes,
                # full-time", "Yes, part-time", "No". Both Yes boxes sit near a
                # Yes label so is_yes alone can't tell them apart; use the box's
                # x-position to select full- vs part-time so both don't check.
                if any(k in kws for k in ("employed", "employment")):
                    _is_part = fin.get("employment_status") == "part_time"
                    if not is_yes:
                        return not ans
                    if "part" in ctx and r.x0 > 200:
                        return _is_part and ans
                    return (not _is_part) and ans
                return (is_yes and ans) or (not is_yes and not ans)
        return None

    # Representation checks (e.g. TX Section 1 "I am not represented by legal aid")
    if "not represented" in ctx_local or "am not represented" in ctx_local:
        return not bool(fin.get("represented_by_legal_aid") or fin.get("has_legal_aid"))
    if "represented by legal aid" in ctx_local or "am represented" in ctx_local:
        return bool(fin.get("represented_by_legal_aid") or fin.get("has_legal_aid"))

    # "do not receive public assistance" / "do not receive needs-based" is the NEGATIVE branch
    if "do not receive" in ctx_local or "do not receive public assistance" in ctx or "do not receive needs-based" in ctx:
        return not any(bool(fin.get(k)) for k in ("receives_snap", "receives_medicaid", "receives_ssi", "receives_tanf", "receives_public_benefits"))

    # Benefit matching: check ctx_local first to avoid row-wide leakage when multiple checkboxes share a row
    for kws, flag in benefit_text:
        if any(re.search(rf'\b{re.escape(k)}\b', ctx_local) for k in kws):
            return flag

    for kws, key in income_source_text:
        if any(re.search(rf'\b{re.escape(k)}\b', ctx_local) for k in kws):
            return bool(fin.get(key))

    # Only fall back to row-wide ctx if this is the only checkbox on the row
    has_other_boxes_on_row = bool(same_row_after) or any(abs((o.y0 + o.y1) / 2 - (r.y0 + r.y1) / 2) < 7 and o.x1 < r.x0 for o in other_cbs)
    if not has_other_boxes_on_row:
        for kws, flag in benefit_text:
            if any(re.search(rf'\b{re.escape(k)}\b', ctx) for k in kws):
                return flag

        for kws, key in income_source_text:
            if any(re.search(rf'\b{re.escape(k)}\b', ctx) for k in kws):
                return bool(fin.get(key))

    return None


def _map_fee_waiver_checkboxes(doc: pymupdf.Document, data: dict, config: dict) -> int:
    """Check fee-waiver Yes/No and benefit boxes from the intake financial data.

    Handles Yes/No pairs that share a single field name (e.g. two 'Check Box1'
    widgets — one for Yes, one for No). When a pair's widgets carry DIFFERENT
    on_states ('Yes'/'No'), the on_state is reliable and is trusted over
    x-proximity (which is ambiguous on tight layouts like AR's).
    """
    checkbox_map = config.get("fee_waiver_checkbox_map") or {}
    overrides = config.get("fee_waiver_checkbox_overrides") or {}
    # Benefit boxes explicitly mapped via fee_waiver_mapping receives_* are already
    # filled by _fill_via_widgets; don't re-evaluate (and uncheck) them here.
    _fw_mapping = config.get("fee_waiver_mapping") or {}
    explicit_benefit_fields = {v for k, v in _fw_mapping.items() if k.startswith("receives_")}
    # Pre-scan on_state patterns so we know when 'Yes'/'No' actually disambiguates.
    on_state_sets: dict = {}
    for page in doc:
        for w in page.widgets():
            w = cast(Any, w)
            if getattr(w, "field_type", None) != pymupdf.PDF_WIDGET_TYPE_CHECKBOX:
                continue
            nm = str(getattr(w, "field_name", "") or "cb")
            try:
                _os = str(w.on_state()).strip().lower()
            except Exception:
                _os = ""
            if _os in ("yes", "no"):
                on_state_sets.setdefault(nm, set()).add(_os)

    state_code_upper = str(config.get("state_code") or data.get("state") or "").upper()
    cat_keys = config.get("categorical_assistance_keys") or ("receives_public_benefits", "receives_ssi", "receives_tanf", "receives_snap")
    skip_financial = config.get("skip_financial_when_categorical") and any(
        bool((data.get("financial_info") or data.get("financial") or {}).get(k)) for k in cat_keys
    )

    checked = 0
    for page_idx, page in enumerate(doc):
        if state_code_upper == "IL" and skip_financial and page_idx in (1, 2):
            continue
        for w in page.widgets():
            w = cast(Any, w)
            if getattr(w, "field_type", None) != pymupdf.PDF_WIDGET_TYPE_CHECKBOX:
                continue
            r = pymupdf.Rect(w.rect)
            nm = str(getattr(w, "field_name", "") or "cb")
            if nm in explicit_benefit_fields:
                continue
            # Explicit per-form overrides win over auto-detection (e.g. MN FEE102
            # "do not receive public assistance" vs "receive" branches).
            if nm in overrides:
                _ov = overrides[nm]
                if isinstance(_ov, str):
                    if _ov == "receives_public_benefits":
                        _fin = data.get("financial_info") or {}
                        _exp = bool(_fin.get("receives_public_benefits") or _fin.get("receives_snap") or _fin.get("receives_medicaid") or _fin.get("receives_ssi") or _fin.get("receives_tanf"))
                    elif _ov in ("do_not_receive_public_benefits", "no_public_benefits"):
                        _fin = data.get("financial_info") or {}
                        _exp = not bool(_fin.get("receives_public_benefits") or _fin.get("receives_snap") or _fin.get("receives_medicaid") or _fin.get("receives_ssi") or _fin.get("receives_tanf"))
                    else:
                        _exp = bool((data.get("financial_info") or {}).get(_ov))
                else:
                    _exp = bool(_ov)
                try:
                    w.field_value = True if _exp else False
                    w.update()
                except Exception:
                    pass
                if _exp:
                    checked += 1
                continue
            try:
                _os = str(w.on_state())
            except Exception:
                _os = ""
            trust = "yes" in on_state_sets.get(nm, set()) and "no" in on_state_sets.get(nm, set())
            exp = _expected_fee_waiver_checkbox(page, r, data, nm, _os, trust, checkbox_map)
            if exp is None:
                continue
            if exp:
                try:
                    w.field_value = True
                    w.update()
                    checked += 1
                except Exception:
                    pass
            else:
                # Explicitly deselect the other half of a Yes/No pair so only
                # one option ships checked.
                try:
                    w.field_value = False
                    w.update()
                except Exception:
                    pass
    return checked


def _resolve_radio_groups(doc: pymupdf.Document, data: dict, config: dict) -> int:
    """Set mutually-exclusive radio groups to a single selection (or blank).

    Radio groups otherwise ship with every option 'On' — a form that shows both
    "Yes" and "No" checked. Each group resolves via config["radio_selections"]:
      * {"data": <key>, "yes": <substr>, "no": <substr>} — pick the option whose
        on_state contains the chosen substring (truthy value → yes, else no).
      * {"any_defense": [<keys>], "yes": <substr>, "no": <substr>} — pick "yes"
        if any listed defense is checked, else "no".
    Groups without a rule are cleared to 'Off' so no conflicting choice ships.
    Also resolves mutually-exclusive CHECKBOX pairs (same field name, distinct
    on_states, e.g. IL's "15 - Checkboxes") when they carry an explicit rule;
    unruled checkbox pairs are left for _map_fee_waiver_checkboxes.
    """
    selections = config.get("radio_selections", {}) or {}
    fin = data.get("financial_info") or data.get("financial") or {}
    pi = data.get("personal_info") or data.get("personal") or {}
    pref = data.get("preferences") or {}
    defenses = data.get("defenses", {}) or {}
    resolved = 0
    for page in doc:
        groups: dict[str, list] = {}
        for w in page.widgets():
            w = cast(Any, w)
            _ft = getattr(w, "field_type", None)
            if _ft != pymupdf.PDF_WIDGET_TYPE_RADIOBUTTON and _ft != pymupdf.PDF_WIDGET_TYPE_CHECKBOX:
                continue
            groups.setdefault(str(getattr(w, "field_name", "") or ""), []).append(w)
        for gname, ws in groups.items():
            # Standalone checkboxes (one widget per field) are handled by the
            # fee-waiver checkbox mapping, not here. Only resolve true groups.
            if len(ws) < 2:
                continue
            rule = selections.get(gname)
            # Unruled checkbox pairs are resolved later by
            # _map_fee_waiver_checkboxes via on-state/label auto-detection;
            # clearing them here would ship both halves blank.
            if not rule and all(getattr(w, "field_type", None) == pymupdf.PDF_WIDGET_TYPE_CHECKBOX for w in ws):
                continue
            needle = None
            if rule:
                if rule.get("skip_when_categorical") and any(
                    bool(fin.get(k)) for k in ("receives_ssi", "receives_tanf", "receives_snap", "receives_blind_aid", "receives_oap", "receives_and")
                ):
                    needle = None  # categorical assistance → skip Sections 7-10
                elif "any_defense" in rule:
                    _checked = any(
                        isinstance(defenses.get(k), dict) and defenses[k].get("checked")
                        for k in rule["any_defense"]
                    )
                    if not _checked and rule.get("or_has_complaint_amount"):
                        try:
                            _amt = float(data.get("case_details", {}).get("complaint_amount_claimed") or data.get("court", {}).get("complaint_amount_claimed") or 0)
                            if _amt > 0:
                                _checked = True
                        except (TypeError, ValueError):
                            pass
                    needle = rule.get("yes") if _checked else rule.get("no")
                elif "match_value" in rule:
                    _src = rule["match_value"]
                    _val = str(fin.get(_src) or pi.get(_src) or pref.get(_src) or "").lower()
                    if _src == "hearing_format" and pref.get("prefers_remote"):
                        _val = "remote"
                    for opt_key, opt_needle in rule.get("options", {}).items():
                        if opt_key.lower() in _val:
                            needle = opt_needle
                            break
                    if not needle and "default" in rule:
                        needle = rule["default"]
                elif "data" in rule:
                    _src = rule["data"]
                    _val = fin.get(_src)
                    if _val is None:
                        _val = pi.get(_src)
                    if _val is None:
                        _val = pref.get(_src)
                    if _src == "is_employed" and _val is None:
                        _emp_inc = _to_float(fin.get("employment_income") or fin.get("self_employment_income") or fin.get("monthly_gross_income") or 0.0)
                        _unemp_inc = _to_float(fin.get("unemployment_income") or 0.0)
                        if _emp_inc > 0 and _unemp_inc == 0:
                            _val = True
                        elif _unemp_inc > 0 or fin.get("last_employment_date") or _emp_inc == 0:
                            _val = False
                    if _src == "prefers_remote" and _val is None and pref.get("hearing_format"):
                        _val = ("remote" in str(pref.get("hearing_format")).lower())
                    if _val is not None:
                        needle = rule.get("yes") if _val else rule.get("no")
                    elif "default" in rule:
                        needle = rule.get(rule["default"]) or rule["default"]
                elif "any_financial" in rule:
                    _checked = any(bool(fin.get(k)) for k in rule["any_financial"])
                    needle = rule.get("yes") if _checked else rule.get("no")
                elif "value" in rule:
                    needle = rule["value"]
            if needle is None and rule and "default" in rule:
                needle = rule.get(rule["default"]) or rule["default"]
            choice = None
            for w in ws:
                try:
                    _os = re.sub(r"#([0-9A-Fa-f]{2})", lambda m: chr(int(m.group(1), 16)), str(w.on_state()))
                except Exception:
                    _os = ""
                if needle and needle.lower() in _os.lower():
                    choice = w
                    break
            for w in ws:
                try:
                    if getattr(w, "field_type", None) == pymupdf.PDF_WIDGET_TYPE_CHECKBOX:
                        # Checkboxes toggle on True/False; radio buttons select
                        # via on_state.
                        w.field_value = True if w is choice else False
                    else:
                        w.field_value = w.on_state() if w is choice else False
                    w.update()
                except Exception:
                    pass
            if choice is not None:
                resolved += 1
    return resolved


def _sanitize_zapfdingbats(doc: pymupdf.Document) -> int:
    """Strip a bogus /Encoding /WinAnsiEncoding from ZapfDingbats fonts.

    ZapfDingbats is a symbol font whose built-in encoding maps the checkmark
    glyph; attaching /WinAnsiEncoding makes Poppler/CUPS (and Linux print
    spoolers) render a digit instead of a checkmark — or drop it entirely — so
    the official filing's checkboxes print blank. PyMuPDF re-adds the bad
    encoding to a fresh ZapfDingbats font while generating checkbox appearance
    streams during widget.update(), so this must also run after all updates,
    immediately before save.
    """
    fixed = 0
    for _xr in range(1, doc.xref_length()):
        try:
            _obj = doc.xref_object(_xr)
            if "/ZapfDingbats" in _obj and "/WinAnsiEncoding" in _obj:
                doc.update_object(_xr, _obj.replace("/Encoding /WinAnsiEncoding", ""))
                fixed += 1
        except Exception:
            pass
    return fixed


_DEAD_LINK_URL_RE = re.compile(
    r"https?://[^\s\)\]\>]+|www\.[^\s\)\]\>]+|[a-zA-Z0-9.-]+\.(?:org|gov|com|edu|net|us)(?:/[^\s\)\]\>]*)?",
    re.IGNORECASE,
)


def _fix_or_clean_dead_links(doc: pymupdf.Document) -> int:
    """Inspect all link annotations in the document.

    If a link has an empty or 'about:blank' URI, attempt to recover the URL
    from the text under the link rect. If a valid URL is found, update the link URI;
    otherwise delete the dead link annotation so it doesn't intercept clicks/drags.
    """
    fixed_or_cleaned = 0
    for page in doc:
        for link in list(page.get_links()):
            uri = (link.get("uri") or "").strip()
            if not uri or uri.lower() == "about:blank":
                rect = link.get("from")
                if not rect:
                    try:
                        page.delete_link(link)
                        fixed_or_cleaned += 1
                    except Exception:
                        pass
                    continue
                txt = page.get_text("text", clip=pymupdf.Rect(rect.x0, rect.y0 - 2, rect.x1, rect.y1 + 2))
                m = _DEAD_LINK_URL_RE.search(txt)
                if m:
                    target_url = m.group(0).rstrip(".,;")
                    if not target_url.startswith(("http://", "https://")):
                        target_url = "https://" + target_url
                    link["uri"] = target_url
                    try:
                        page.update_link(link)
                        fixed_or_cleaned += 1
                    except Exception:
                        try:
                            page.delete_link(link)
                            fixed_or_cleaned += 1
                        except Exception:
                            pass
                else:
                    try:
                        page.delete_link(link)
                        fixed_or_cleaned += 1
                    except Exception:
                        pass
    return fixed_or_cleaned


def _unhide_filled_widgets(doc: pymupdf.Document) -> None:
    """Clear the /F (Hidden) annotation flag on every populated widget.

    Some official templates (e.g. Colorado JDF 103) ship conditional child
    fields with /F 2 (Hidden); Adobe Acrobat's embedded JS normally unhides
    them when a parent radio is toggled. Programmatic filling sets the value
    (/V) and appearance stream (/AP) but leaves /F intact, so the values stay
    invisible in viewers and prints. field_display = 0 forces visible+print.
    """
    for page in doc:
        for w in page.widgets():
            val = getattr(w, "field_value", None)
            if val not in ("", "Off", None, False) and getattr(w, "field_display", 0) != 0:
                w.field_display = 0
                try:
                    w.update()
                except Exception:
                    pass


def _compose_full_address(p: dict, state: str) -> str:
    """Compose "street, city, ST ZIP" from separate intake fields.

    The city is skipped if already embedded after a comma in the street string;
    state+ZIP are joined as "ST ZIP". Never leaves a trailing comma.
    """
    street = (p.get("property_address") or "").strip()
    city = (p.get("property_city") or "").strip()
    state = (state or "").strip()
    zipcode = (p.get("property_zip") or "").strip().split("-")[0][:5]
    tail_parts = []
    already_has_city = bool(city and re.search(rf',\s*{re.escape(city)}\b', street, re.IGNORECASE))
    if city and not already_has_city:
        tail_parts.append(city)
    state_zip = " ".join(x for x in (state, zipcode) if x)
    if state_zip:
        tail_parts.append(state_zip)
    tail = ", ".join(x for x in tail_parts if x)
    return ", ".join(x for x in (street, tail) if x)


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
    _county_key = county
    if county and county_overrides:
        # Normalize spellings ("Denver County" / "City and County of Denver" →
        # "Denver") so the county-specific form is selected regardless of how the
        # intake agent recorded the county.
        _c = county.lower().replace("city and county of", "").replace("county", "").strip()
        for _k in county_overrides:
            if _k.lower().replace("city and county of", "").replace("county", "").strip() == _c:
                _county_key = _k
                break
    if _county_key and _county_key in county_overrides and form_key == "answer_form":
        override = county_overrides[_county_key]
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

    doc = pymupdf.open(form_path)

    # Sanitize ZapfDingbats fonts in the SOURCE template (some ship with a bogus
    # /Encoding /WinAnsiEncoding on the /ZaDb font).
    _sanitize_zapfdingbats(doc)

    # Arkansas Answer template:
    # 1. Page 6: wipe out the undefined empty line immediately below "ANSWER" heading (y ~ 518.4)
    #    and clean up the "Your name goes here." placeholder text so the editable field sits cleanly.
    # 2. Page 9: remove the underline above "Sign your name here and fill in your address and phone number below."
    #    and move the text to Page 10 above the address inputs.
    if state_code == "AR" and form_key == "answer_form":
        if len(doc) > 5:
            doc[5].add_redact_annot(pymupdf.Rect(65.0, 517.0, 212.0, 520.0), fill=(1, 1, 1))
            doc[5].add_redact_annot(pymupdf.Rect(65.0, 698.0, 220.0, 722.0), fill=(1, 1, 1))
            doc[5].apply_redactions()
        if len(doc) > 9:
            doc[8].add_redact_annot(pymupdf.Rect(60.0, 695.0, 418.0, 722.0), fill=(1, 1, 1))
            doc[8].apply_redactions()
            p10_text = doc[9].get_text()
            if "Sign your name here and fill in your address" not in p10_text:
                doc[9].insert_text((66.0, 62.0), "Sign your name here and fill in your address and phone number below.", fontname="times-roman", fontsize=12.0, color=(0, 0, 0))

    # Check if form has fillable fields — across ALL pages. Multi-page filings
    # with cover sheets/introductory instructions on page 0 (e.g. LA's 14-page
    # answer) must not be falsely flagged as non-fillable.
    has_fields = False
    try:
        total_widgets = sum(len(list(p.widgets())) for p in doc)
        has_fields = total_widgets > 0
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
                fn = str(getattr(w, "field_name", "") or "")
                o = overrides.get(fn)
                all_text = overrides.get("__all_text__") if getattr(w, "field_type", None) == pymupdf.PDF_WIDGET_TYPE_TEXT else None
                if all_text:
                    o = {**all_text, **o} if o else dict(all_text)
                if not o:
                    continue
                r = w.rect
                if r is None:
                    continue
                w.rect = pymupdf.Rect(
                    o.get("x0", r.x0 + o.get("dx0", 0)),
                    o.get("y0", r.y0 + o.get("dy0", 0)),
                    o.get("x1", r.x1 + o.get("dx1", 0)),
                    o.get("y1", r.y1 + o.get("dy1", 0)))
                if "text_fontsize" in o:
                    w.text_fontsize = o["text_fontsize"]
                if "text_color" in o:
                    w.text_color = o["text_color"]
                if "fill_color" in o:
                    w.fill_color = o["fill_color"]
                if "border_color" in o:
                    w.border_color = o["border_color"]
                if "field_flags" in o:
                    w.field_flags = o["field_flags"]
                if "align" in o and getattr(w, "xref", None):
                    try:
                        if o["align"] == "center":
                            doc.xref_set_key(w.xref, "Q", "1")
                        elif o["align"] == "right":
                            doc.xref_set_key(w.xref, "Q", "2")
                        elif o["align"] == "left":
                            doc.xref_set_key(w.xref, "Q", "0")
                    except Exception:
                        pass
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
                if r.x0 < 90 and r.height < 25 and any(k in nm for k in ("plaintiff", "defendant", "printed")) \
                        and any(f in form_path for f in ("in_eviction_answer", "ky_eviction_answer", "mo_eviction_answer")):
                    r = pymupdf.Rect(130, r.y0, r.x1, r.y1)
                elif 350 <= r.x0 <= 370 and any(k in nm for k in ("address", "phone")) \
                        and "ky_eviction_answer" not in form_path \
                        and "in_eviction_answer" not in form_path \
                        and "oh_eviction_answer" not in form_path \
                        and "ok_eviction_answer" not in form_path \
                        and "or_eviction_answer" not in form_path \
                        and "or_fee_waiver" not in form_path:
                    r = pymupdf.Rect(400, r.y0, r.x1, r.y1)
                w.rect = pymupdf.Rect(r.x0, r.y0, r.x1, r.y1)
                try:
                    w.update()
                except Exception:
                    pass

    if has_fields:
        # Native fillable form: fill its own widgets.
        _fill_via_widgets(doc, data, config, form_key, state_code=state_code)
        # Hybrid forms (fillable checkboxes + static caption/header text with no
        # native widget) still need the coordinate overlay for the unmapped
        # caption lines. The overlay skips positions that already have a widget.
        if form_key == "fee_waiver_form" and config.get("fee_waiver_overlay"):
            _fill_via_overlay(doc, data, config, form_key)
        elif form_key == "answer_form" and config.get("overlay_positions"):
            _fill_via_overlay(doc, data, config, form_key)
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
    _make_signature_fields_readonly(doc, config)
    _resolve_radio_groups(doc, data, config)

    if form_key == "fee_waiver_form":
        _map_fee_waiver_checkboxes(doc, data, config)

    # Unhide any filled widgets that still carry the template's /F (Hidden) flag.
    _unhide_filled_widgets(doc)

    # PyMuPDF adds a fresh ZapfDingbats font (with /WinAnsiEncoding) while
    # generating checkbox appearance streams during widget.update(); strip it
    # again right before save so checkmarks print correctly.
    _sanitize_zapfdingbats(doc)

    # Clean and repair any dead/about:blank links across all forms
    _fix_or_clean_dead_links(doc)

    doc.save(output_path, deflate=True)
    doc.close()
    logger.info(f"✅ {state_code} form saved: {output_path}")
    return True


def _fill_via_widgets(doc: pymupdf.Document, data: dict, config: dict, form_key: str = "", state_code: str = ""):
    """Fill a PDF's form fields using widget/field mapping + smart auto-fill."""
    state_code = str(state_code or data.get("state") or data.get("court", {}).get("state") or data.get("case_details", {}).get("state") or data.get("personal_info", {}).get("state") or data.get("personal_info", {}).get("property_state") or config.get("state_code") or "").upper()
    mapping = config.get("field_mapping", {})
    p = data.get("personal_info", {}) or data.get("personal", {})
    l = data.get("landlord_info", {}) or data.get("landlord", {})
    c = data.get("case_details", {}) or data.get("court", {})
    financial = data.get("financial_info", {}) or data.get("financial", {})
    defenses = data.get("defenses", {})
    pref = data.get("preferences", {})
    today = date.today()
    
    values = {}
    
    # === UNIFIED MAPPING FOR REBUILT FORMS (standardized field names) ===
    # These work for ALL states with rebuilt forms — predictable, clean field names
    # Full address for signature/contact lines that expect "street, city, state ZIP".
    _full_addr = _compose_full_address(p, data.get("state", ""))
    UNIFIED_MAP = {
        "defendant_name": p.get("full_name", ""),
        "plaintiff_name": l.get("landlord_name", ""),
        "case_number": c.get("case_number", ""),
        "court_name": c.get("court_name", ""),
        "county": p.get("county", ""),
        "property_address": _full_addr or p.get("property_address", ""),
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
    
    # === Build _all_data across all intake sections ===
    r = data.get("rent_payment", {}) or {}
    _all_data = {}
    for section in [p, l, c, r, pref, financial]:
        if isinstance(section, dict):
            for k, v in section.items():
                if v is not None and v != "":
                    _all_data[k] = str(v)
    
    # Synthesize aliases — field_mapping keys must match _all_data keys
    aliases = {
        "full_name": ["name", "defendant_name", "printed_name", "full_name_applicant",
                      "full_name_mover", "full_name_tp", "full_name_order"],
        "property_address": ["address", "street", "mailing_address", "property"],
        "property_city": ["city", "town"],
        "property_zip": ["zip", "postal_code"],
        "court_name": ["court_address", "courthouse", "court"],
        "landlord_name": ["plaintiff", "plaintiff_name", "landlord"],
        "phone": ["telephone", "phone_number", "cell"],
        "email": ["e_mail", "email_address"],
        "county": ["county_name", "county_mover", "county_tp"],
        "date_of_birth": ["dob", "birth_date", "birthdate"],
        "repair_notice_date": ["date_note", "repair_date"],
        "total_debt_owed": ["debt_owed", "debt_balance"],
        "debt_owed": ["total_debt_owed", "debt_balance"],
        "last_employment_date": ["last_paycheck_date"],
        "rent_paid_date": ["date_offered", "rent_payment_date"],
        "fair_rent_complaint_date": ["date_increase"],
    }
    for source_key, target_keys in aliases.items():
        if source_key in _all_data:
            for tk in target_keys:
                if tk not in _all_data:
                    _all_data[tk] = _all_data[source_key]

    def _format_date_mdy(val):
        if not val:
            return ""
        val_str = str(val).strip()
        if re.match(r'^\d{4}-\d{2}-\d{2}$', val_str):
            parts = val_str.split('-')
            return f"{parts[1]}/{parts[2]}/{parts[0]}"
        return val_str

    if "date_of_birth" in _all_data:
        _fmt_dob = _format_date_mdy(_all_data["date_of_birth"])
        _all_data["date_of_birth"] = _fmt_dob
        _all_data["dob"] = _fmt_dob
        _all_data["birth_date"] = _fmt_dob
        _all_data["birthdate"] = _fmt_dob

    if "last_employment_date" in _all_data:
        _fmt_led = _format_date_mdy(_all_data["last_employment_date"])
        _all_data["last_employment_date"] = _fmt_led
        _all_data["last_paycheck_date"] = _fmt_led
        _all_data["7.5"] = _fmt_led

    if "rent_paid_date" in _all_data:
        _fmt_rpd = _format_date_mdy(_all_data["rent_paid_date"])
        _all_data["rent_paid_date"] = _fmt_rpd
        _all_data["date_offered"] = _fmt_rpd
        _all_data["DATEOFFERED[0]"] = _fmt_rpd

    if "fair_rent_complaint_date" in _all_data:
        _fmt_frd = _format_date_mdy(_all_data["fair_rent_complaint_date"])
        _all_data["fair_rent_complaint_date"] = _fmt_frd
        _all_data["date_increase"] = _fmt_frd
        _all_data["DATEINCREASE[0]"] = _fmt_frd

    if "summons_service_date" in _all_data:
        _fmt_sd = _format_date_mdy(_all_data["summons_service_date"])
        _all_data["date_served"] = _fmt_sd
        _all_data["service_date"] = _fmt_sd

    if "repair_notice_date" in _all_data:
        _fmt_rnd = _format_date_mdy(_all_data["repair_notice_date"])
        _all_data["repair_notice_date"] = _fmt_rnd
        _all_data["date_note"] = _fmt_rnd
        _all_data["DATENOTE[0]"] = _fmt_rnd

    if "court_date" in _all_data:
        _fmt_cd = _format_date_mdy(_all_data["court_date"])
        _all_data["hearing_date"] = _fmt_cd

    # Colorado courthouse mailing address lookup:
    # If in Colorado and court_address is empty or just repeats the county/court name without a street address,
    # look up the actual courthouse mailing address from the Colorado county courthouse directory.
    if state_code == "CO":
        from app.services.state_configs import get_colorado_courthouse_address
        _ca = str(_all_data.get("court_address", "") or "").strip()
        _cty = str(_all_data.get("county", "") or p.get("county", "")).strip()
        if not _ca or _ca.lower() in (_cty.lower(), f"{_cty.lower()} county", "county court", "district court") or not any(ch.isdigit() for ch in _ca):
            _lookup_addr = get_colorado_courthouse_address(_cty)
            if _lookup_addr:
                _all_data["court_address"] = _lookup_addr

    # Connecticut courthouse mailing address lookup:
    if state_code == "CT":
        from app.services.state_configs import get_connecticut_courthouse_address
        _ca = str(_all_data.get("court_address", "") or "").strip()
        _cty = str(_all_data.get("county", "") or p.get("county", "")).strip()
        if not _ca or _ca.lower() in (_cty.lower(), f"{_cty.lower()} county", "housing court", "housing session", "superior court") or not any(ch.isdigit() for ch in _ca):
            _lookup_addr = get_connecticut_courthouse_address(_cty)
            if _lookup_addr:
                _all_data["court_address"] = _lookup_addr

    if "interpreter_language" not in _all_data and p.get("interpreter_language"):
        _all_data["interpreter_language"] = str(p.get("interpreter_language"))
    if "marital_status" not in _all_data and financial.get("marital_status"):
        _all_data["marital_status"] = str(financial.get("marital_status"))
    if "pay_rate" not in _all_data:
        _pr = financial.get("hourly_rate_or_salary") or financial.get("employment_income") or financial.get("monthly_gross_income")
        if _pr is not None:
            _all_data["pay_rate"] = f"{_to_float(_pr):.2f}"
    if "last_paycheck_date" not in _all_data and financial.get("last_employment_date"):
        _all_data["last_paycheck_date"] = str(financial.get("last_employment_date"))
    if "pay_frequency" not in _all_data:
        _pf = str(financial.get("pay_period") or "").lower()
        if "week" in _pf and ("every other" in _pf or "bi-week" in _pf or "biweek" in _pf):
            _all_data["pay_frequency"] = "Every other week"
        elif "week" in _pf:
            _all_data["pay_frequency"] = "Weekly"
        elif "bi-month" in _pf or "twice" in _pf:
            _all_data["pay_frequency"] = "Bi-monthly"
        else:
            _all_data["pay_frequency"] = "Monthly"

    # Split the phone number for forms with separate area-code / number fields.
    if "phone_area_code" not in _all_data or "phone_number_only" not in _all_data:
        import re as _re
        _m = _re.search(r'\(?(\d{3})\)?[\s.-]*(\d{3})[\s.-]*(\d{4})', str(p.get("phone", "") or ""))
        if "phone_area_code" not in _all_data:
            _all_data["phone_area_code"] = _m.group(1) if _m else ""
        if "phone_number_only" not in _all_data:
            _all_data["phone_number_only"] = f"{_m.group(2)}-{_m.group(3)}" if _m else ""

    # Today's date for execution/signature date fields.
    if "date" not in _all_data:
        _all_data["date"] = date.today().strftime("%m/%d/%Y")
    
    # Synthesize city_state_zip from city + state + zip
    if "property_city" in _all_data and "city_state_zip" not in _all_data:
        city = _all_data.get("property_city", "")
        zipcode = _all_data.get("property_zip", "")
        _all_data["city_state_zip"] = f"{city}, {state_code} {zipcode}".strip(", ")
    # Proof of delivery signature block (IL Page 6): the filer's own details.
    if "proof_signature" not in _all_data:
        _all_data["proof_signature"] = ""
    if "proof_name" not in _all_data:
        _all_data["proof_name"] = p.get("full_name", "")
    if "proof_phone" not in _all_data:
        _all_data["proof_phone"] = p.get("phone", "")
    if "proof_city_state_zip" not in _all_data:
        _all_data["proof_city_state_zip"] = _all_data.get("city_state_zip", "")
    if "proof_email" not in _all_data:
        _all_data["proof_email"] = p.get("email", "")
    # Landlord street + city/state/zip (for forms with separate fields, e.g. GA):
    # split the landlord's full address string. Keep "landlord_address" intact for
    # cover pages / certificates of service that want the whole string.
    if "landlord_street" not in _all_data:
        _laddr = str(_all_data.get("landlord_address", "") or "")
        if "," in _laddr:
            _lstreet, _sep, _lrest = _laddr.partition(",")
            _all_data["landlord_street"] = _lstreet.strip()
            _all_data["landlord_city_state_zip"] = _lrest.strip()
        else:
            _all_data["landlord_street"] = _laddr
            _all_data["landlord_city_state_zip"] = _laddr
    # Full mailing address (street + city/state/zip) for one-line address fields.
    if "full_address" not in _all_data:
        _all_data["full_address"] = ", ".join(x for x in (
            _all_data.get("property_address", ""), _all_data.get("city_state_zip", "")) if x).strip()

    # Judicial district (MI MC 20): extract the leading ordinal from the court
    # name ("36th District Court" -> "36th") for the district header field.
    if "judicial_district" not in _all_data:
        _cn = str(_all_data.get("court_name", "") or "").strip()
        _first = _cn.split()[0] if _cn else ""
        # "36th District Court" -> "36th"; otherwise fall back to the court name.
        _all_data["judicial_district"] = _first if (_first and _first[:-2].isdigit() and _first[-2:].lower() in ("st", "nd", "rd", "th")) else _cn

    # Missouri Judicial Circuit for circuit court / GN10 fee waiver.
    if "judicial_circuit" not in _all_data:
        _c = str(_all_data.get("county", "") or "").strip().lower()
        _cn = str(_all_data.get("court_name", "") or "").strip()
        _mo_circuits = {
            "st. louis": "21st", "st louis": "21st", "st. louis county": "21st", "st louis county": "21st",
            "st. louis city": "22nd", "st louis city": "22nd", "city of st. louis": "22nd",
            "jackson": "16th", "st. charles": "11th", "st charles": "11th",
            "clay": "7th", "jefferson": "23rd", "greene": "31st", "boone": "13th",
            "platte": "6th", "cass": "17th", "buchanan": "5th", "jasper": "29th",
            "franklin": "20th", "cole": "19th", "cape girardeau": "32nd",
        }
        _m = re.search(r'\b(\d+(?:st|nd|rd|th)?)\s+(?:judicial\s+)?circuit\b', _cn, re.I)
        if _m:
            _all_data["judicial_circuit"] = _m.group(1)
        elif _c in _mo_circuits:
            _all_data["judicial_circuit"] = _mo_circuits[_c]
        else:
            _all_data["judicial_circuit"] = ""

    # Composite caption fields (MI DC 111a): name + address + phone in one field.
    if "defendant_composite" not in _all_data:
        _all_data["defendant_composite"] = "\n".join(x for x in (
            p.get("full_name", ""), p.get("property_address", ""),
            _all_data.get("city_state_zip", ""), p.get("phone", "")
        ) if x)
    if "plaintiff_composite" not in _all_data:
        _all_data["plaintiff_composite"] = "\n".join(x for x in (
            l.get("landlord_name", ""), l.get("landlord_address", ""), l.get("landlord_phone", "")
        ) if x)

    # Case name for "Name of case" captions (e.g. CT): "Landlord v. Tenant"
    if "case_name" not in _all_data:
        _all_data["case_name"] = f"{_all_data.get('landlord_name', '')} v. {_all_data.get('full_name', '')}".strip(" v.")

    # Georgia counterclaim diminished value + duration (repair-and-deduct).
    # Only populate if the tenant actually asserted a failure-to-repair defense (def_repairs).
    _has_repairs = False
    if isinstance(defenses, dict):
        _d_rep = defenses.get("def_repairs")
        if isinstance(_d_rep, dict) and _d_rep.get("checked"):
            _has_repairs = True
    if _has_repairs:
        _rent_info = data.get("rent_payment", {})
        try:
            _claimed = float(c.get("complaint_amount_claimed") or 0)
            _owed = float(_rent_info.get("amount_tenant_believes_owed") or 0)
            _monthly = float(_rent_info.get("monthly_rent") or c.get("monthly_rent") or 0)
        except (TypeError, ValueError):
            _claimed = _owed = _monthly = 0.0
        if _claimed > _owed and _monthly > 0:
            _total_reduction = _claimed - _owed
            _months = max(1, round(_claimed / _monthly))
            _all_data.setdefault("reduced_rent_amount", f"{_total_reduction / _months:.2f}")
            _all_data.setdefault("reduced_rent_months", str(_months))
    
    # Also add state-level data
    if state_code:
        _all_data["state"] = state_code
        _all_data["state_code"] = state_code
        _all_data["state_name"] = config.get("name", state_code)

    # Court caption slots for "IN THE ___ COURT ___" fee-waiver captions:
    # the court level (e.g. "District") precedes COURT, the county follows it.
    if "court_level" not in _all_data:
        _ct = str(config.get("court_type", "") or "")
        _all_data["court_level"] = _ct.replace("Court", "").replace(" court", "").strip()
    if "court_caption_county" not in _all_data and "county" in _all_data:
        _all_data["court_caption_county"] = _all_data["county"]
    
    # Certificate of Service recipient — the landlord (or their attorney), never
    # the tenant. The tenant certifies they SERVED the landlord, so the recipient
    # name/address must be the landlord's (or counsel's), not the tenant's own.
    _cert_name_key = "landlord_name"
    _cert_addr_key = "landlord_address"
    if (l.get("landlord_attorney_name") or "").strip():
        _cert_name_key = "landlord_attorney_name"
        if (l.get("landlord_attorney_address") or "").strip():
            _cert_addr_key = "landlord_attorney_address"

    # Certificate of Service mailing address — the landlord's (or counsel's)
    # name + address, so the recipient is fully identified on the CoS.
    if "cos_recipient" not in _all_data:
        _atty_name = (l.get("landlord_attorney_name") or "").strip()
        _l_name = l.get("landlord_name", "") or ""
        _all_data["cos_recipient"] = f"{_atty_name} (attorney for {_l_name})" if _atty_name else _l_name
    if "cos_address" not in _all_data:
        _atty_name = (l.get("landlord_attorney_name") or "").strip()
        _atty_addr = (l.get("landlord_attorney_address") or "").strip()
        _all_data["cos_address"] = _atty_addr if (_atty_name and _atty_addr) else (l.get("landlord_address") or "")
    if "plaintiff_attorney_composite" not in _all_data:
        _atty_name = (l.get("landlord_attorney_name") or "").strip()
        _atty_addr = (l.get("landlord_attorney_address") or "").strip()
        _all_data["plaintiff_attorney_composite"] = "\n".join(x for x in (_atty_name, _atty_addr) if x)
    if "cos_mail" not in _all_data:
        _n = _all_data.get(_cert_name_key, "")
        _a = _all_data.get(_cert_addr_key, "")
        _all_data["cos_mail"] = ", ".join(x for x in (_n, _a) if x)
    _all_data["cos_served_to"] = _all_data["cos_mail"]
    if "mailing_address" not in _all_data and "property_address" in _all_data:
        _all_data["mailing_address"] = _all_data["property_address"]
    
    # Certificate fields for CT, LA, and other states — derive from existing data
    # Certificate of service: the FILER (tenant) signs it and names the RECIPIENT
    # (landlord or counsel). cert_name/cert_mail/cert_phone are the tenant's own
    # details; cert_address is the landlord's (or counsel's) name + address.
    _all_data["landlord_service_address"] = "\n".join(x for x in (
        _all_data.get(_cert_name_key, ""), _all_data.get(_cert_addr_key, "")) if x).strip()
    cert_synthesis = {
        "cert_name": "cos_served_to" if state_code in ("KY", "IN") else "full_name",
        "cert_address": "landlord_service_address",
        "cert_date_signed": None,
        "cert_date": None,
        "cert_mail": "full_address",
        "cert_phone": "phone",
        "note": None,
        "notified": None,
        "code_violation": None,
        "date_offered": None,
        "date_note": "repair_notice_date",
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
    _all_data["year_2digit"] = date.today().strftime("%y")

    # Oregon answer certificate and narrative helpers
    if state_code == "OR":
        _all_data["cert_landlord_address"] = _all_data.get("cos_address") or _all_data.get("landlord_service_address") or _all_data.get("landlord_address") or ""
        _all_data["cert_date_sig"] = today_str
        _all_data["cert_name"] = str(p.get("full_name", ""))
        _all_data["cert_date"] = today_str
        if (defenses.get("def_repairs", {}) or {}).get("checked"):
            values["defense_repairs_narrative"] = (defenses.get("def_repairs", {}) or {}).get("explanation") or "Landlord failed to maintain premises and make requested repairs."
        if (defenses.get("def_bad_notice", {}) or {}).get("checked"):
            values["defense_bad_notice_narrative"] = (defenses.get("def_bad_notice", {}) or {}).get("explanation") or "Notice was defective or not properly served."
        if (defenses.get("def_other", {}) or {}).get("checked"):
            values["defense_other_narrative"] = (defenses.get("def_other", {}) or {}).get("explanation") or ""
    
    # Map each field_mapping key to a value from our data
    # Also make defense_narrative available for field_mapping
    if "defense_narrative" in values:
        _all_data["defense_narrative"] = values["defense_narrative"]
    if "hearing_at_1" in mapping or "hearing_at_2" in mapping:
        narr = _all_data.get("defense_narrative", "")
        if narr:
            widths = [370, 450, 450, 450]
            cleaned = " ".join(narr.replace("\n\n", "; ").replace("\n", " ").split())
            words = cleaned.split(" ")
            lines = []
            line_idx = 0
            curr_line = ""
            for w_word in words:
                if line_idx >= len(widths):
                    break
                target_w = widths[line_idx] - 4.0
                test_line = (curr_line + " " + w_word).strip()
                if pymupdf.get_text_length(test_line, fontname="helv", fontsize=9.0) <= target_w:
                    curr_line = test_line
                else:
                    if curr_line:
                        lines.append(curr_line)
                        line_idx += 1
                        if line_idx < len(widths):
                            curr_line = w_word
                        else:
                            curr_line = ""
                            break
                    else:
                        lines.append(test_line)
                        line_idx += 1
                        curr_line = ""
            if curr_line and line_idx < len(widths):
                lines.append(curr_line)
            for i in range(1, 5):
                _all_data[f"hearing_at_{i}"] = lines[i - 1] if i <= len(lines) else ""
    for map_key, pdf_field in mapping.items():
        if map_key in _all_data:
            values[pdf_field] = str(_all_data[map_key])
    
    fw_mapping = config.get("fee_waiver_mapping", {})
    skip_financial = False
    # fee_waiver_mapping is ONLY for the fee-waiver form. Apply it strictly when
    # filling the fee waiver — otherwise its field names (e.g. "6.5" on JDF 205)
    # collide with unrelated widgets on the ANSWER form (e.g. "6.5" on JDF 103).
    if form_key == "fee_waiver_form":
        financial = data.get("financial_info", {})
        # Louisiana fee waiver: derived status checkboxes (Employed / Bank / Single).
        if "is_employed" not in _all_data:
            _all_data["is_employed"] = "Yes" if (financial.get("is_employed") is True or financial.get("employment_income") or financial.get("self_employment_income") or financial.get("monthly_gross_income")) else "No"
        if "has_bank_account" not in _all_data:
            _all_data["has_bank_account"] = "Yes" if (financial.get("checking_balance") or financial.get("savings_balance") or financial.get("cash_on_hand")) else "No"
        if "is_single" not in _all_data:
            try:
                _adults = int(financial.get("household_adults") or 1)
            except (TypeError, ValueError):
                _adults = 1
            _all_data["is_single"] = "Yes" if _adults <= 1 else "No"
        # Oklahoma fee waiver helpers:
        if state_code == "OK":
            _is_emp = bool(financial.get("is_employed") is True or financial.get("employment_income") or financial.get("monthly_gross_income"))
            _all_data["employed_yes"] = "X" if _is_emp else ""
            _all_data["employed_no"] = "X" if not _is_emp else ""
            _all_data["residence_rent"] = "X"
            _all_data["residence_own"] = ""
            if "employer_name" not in _all_data:
                _all_data["employer_name"] = str(financial.get("employer_name") or financial.get("employer") or ("Employed" if _is_emp else ""))
            if financial.get("debt_payments") or financial.get("credit_card_balance"):
                _all_data["creditor_1"] = "Credit Card / Personal Debt"
                _all_data["debt_balance_1"] = f"{_to_float(financial.get('credit_card_balance') or financial.get('debt_owed') or financial.get('total_debt_owed') or 0.0):.2f}"
                _all_data["debt_payment_1"] = f"{_to_float(financial.get('debt_payments') or 0.0):.2f}"
            _all_data["printed_name_order"] = str(p.get("full_name", ""))
            _all_data["property_address_order"] = str(p.get("property_address", ""))
            _all_data["city_state_zip_order"] = str(_all_data.get("city_state_zip", ""))
            _all_data["phone_order"] = str(p.get("phone", ""))
        # Oregon fee waiver helpers:
        if state_code == "OR":
            _all_data["role_defendant"] = "Yes"
            _all_data["fee_filing"] = "Yes"
            _all_data["fee_response"] = "Yes"
            _all_data["legal_aid_no"] = "Yes"
            _all_data["legal_aid_yes"] = "No"
            try:
                _hs = int(financial.get("household_size") or (int(financial.get("household_adults") or 1) + int(financial.get("household_children") or 0)))
            except (ValueError, TypeError):
                _hs = 1
            _all_data["household_size"] = str(_hs)

            # Living expenses
            _rent = _to_float(c.get("monthly_rent") or financial.get("rent_or_mortgage") or 0.0)
            _util = sum(_to_float(financial.get(k)) or 0.0 for k in ("electricity", "gas_oil", "water_sewer", "trash", "utilities_expense", "telephone", "phone_internet", "telephone_expense"))
            _food = _to_float(financial.get("food_groceries") or financial.get("food_expense") or 0.0)
            home_total = _rent + _util + _food
            _all_data["home_expense"] = f"{home_total:.2f}"

            trans_total = sum(_to_float(financial.get(k)) or 0.0 for k in ("transportation", "transportation_expense", "auto_loan", "car_insurance", "auto_expenses", "gasoline"))
            _all_data["transportation_expense"] = f"{trans_total:.2f}"

            other_total = sum(_to_float(financial.get(k)) or 0.0 for k in ("debt_payments", "medical_expenses", "medical_expense", "child_care", "clothing", "laundry_cleaning", "other_expenses"))
            _all_data["other_expenses"] = f"{other_total:.2f}"

            total_exp = home_total + trans_total + other_total
            _all_data["total_monthly_expenses"] = f"{total_exp:.2f}"

            # Benefits
            if financial.get("receives_snap"):
                _all_data["receives_snap"] = "Yes"
                _all_data["snap_amount"] = f"{_to_float(financial.get('snap_amount') or 0.0):.2f}"
            if financial.get("receives_ssi"):
                _all_data["receives_ssi"] = "Yes"
                _all_data["ssi_amount"] = f"{_to_float(financial.get('ssi_amount') or 0.0):.2f}"
            if financial.get("receives_tanf"):
                _all_data["receives_tanf"] = "Yes"
                _all_data["tanf_amount"] = f"{_to_float(financial.get('tanf_amount') or 0.0):.2f}"
            if financial.get("receives_medicaid"):
                _all_data["receives_medicaid"] = "Yes"
            _tot_ben = _to_float(financial.get("total_monthly_benefits") or 0.0)
            if _tot_ben == 0.0:
                _tot_ben = _to_float(financial.get("snap_amount") or 0.0) + _to_float(financial.get("ssi_amount") or 0.0) + _to_float(financial.get("tanf_amount") or 0.0)
            _all_data["total_benefits"] = f"{_tot_ben:.2f}"

            # Income
            _net = _to_float(financial.get("employment_income") or financial.get("monthly_gross_income") or 0.0)
            _all_data["employment_income"] = f"{_net:.2f}"
            _oth_inc = _to_float(financial.get("other_income") or 0.0)
            _all_data["other_income"] = f"{_oth_inc:.2f}"
            _all_data["total_monthly_income"] = f"{(_net + _oth_inc):.2f}"

            # Assets
            _cash = _to_float(financial.get("cash_on_hand") or 0.0) + _to_float(financial.get("checking_balance") or 0.0) + _to_float(financial.get("savings_balance") or 0.0)
            _all_data["cash_on_hand"] = f"{_cash:.2f}"
            _veh = _to_float(financial.get("vehicle_value") or 0.0)
            if _veh > 0:
                _all_data["asset_desc_1"] = f"Vehicle ({financial.get('vehicle_make_model') or 'Auto'})"
                _all_data["asset_value"] = f"{_veh:.2f}"
            else:
                _all_data["asset_value"] = "0.00"
            _all_data["total_assets"] = f"{(_cash + _veh):.2f}"

            # Order fields (Pages 4 and 5)
            _all_data["county_p4"] = str(p.get("county", ""))
            _all_data["plaintiff_name_p4"] = str(l.get("landlord_name", ""))
            _all_data["case_number_p4"] = str(c.get("case_number", ""))
            _all_data["defendant_name_p4"] = str(p.get("full_name", ""))
            _all_data["full_name_p4"] = str(p.get("full_name", ""))
            _all_data["order_fee_filing"] = "Yes"
            _all_data["order_role_defendant"] = "Yes"
            _all_data["order_signature_1"] = ""
            _all_data["order_print_name_1"] = str(p.get("full_name", ""))
            _all_data["order_date"] = today_str
            _all_data["order_signature"] = ""
            _all_data["order_printed_name"] = str(p.get("full_name", ""))
            _all_data["order_address"] = str(p.get("property_address", ""))
            _all_data["order_city_state_zip"] = str(_all_data.get("city_state_zip", ""))
            _all_data["order_phone"] = str(p.get("phone", ""))
        # When a state's fee waiver says "categorical assistance → skip Sections 7-10",
        # and the tenant receives categorical assistance, leave the income/expense/asset
        # fields blank (they are only required when categorical assistance is absent).
        cat_keys = config.get("categorical_assistance_keys") or ("receives_public_benefits", "receives_ssi", "receives_tanf", "receives_snap")
        skip_financial = config.get("skip_financial_when_categorical") and any(
            bool(financial.get(k)) for k in cat_keys
        )
        for map_key, pdf_field in fw_mapping.items():
            # Handle financial boolean fields as checkboxes
            if map_key.startswith("receives_") or map_key in ("income_below_threshold", "unable_to_pay_fees"):
                val = _get_financial_value(map_key, data)
                if val:
                    values[pdf_field] = "Yes"
            else:
                val = _get_financial_value(map_key, data)
                if val is not None and val != "":
                    if skip_financial and map_key not in ("household_adults", "household_children", "total_dependents"):
                        continue
                    if config.get("strip_dollar_signs"):
                        val = str(val).lstrip("$")
                    values[pdf_field] = str(val)
                elif map_key in _all_data:
                    _val = str(_all_data[map_key])
                    if config.get("strip_dollar_signs"):
                        _val = _val.lstrip("$")
                    values[pdf_field] = _val

        # Colorado fee waiver: if tenant auto-qualifies via categorical assistance (SNAP/SSI/TANF),
        # clear embedded template default values ('0') in Section 9 total fields so they remain blank
        # per JDF 205 instructions ("skip to Section 11").
        if skip_financial and state_code == "CO":
            values["9A.8"] = ""
            values["9B.8"] = ""
            values["9C"] = ""
        elif state_code == "CO" and not skip_financial:
            # Ensure total monthly income (9A.8) and total monthly expenses (9B.8) are populated
            if not values.get("9A.8"):
                _inc = _to_float(financial.get("monthly_gross_income")) or 0.0
                if _inc == 0.0:
                    _inc = sum(_to_float(financial.get(k)) or 0.0 for k in (
                        "employment_income", "self_employment_income", "social_security_income",
                        "ssi_income", "unemployment_income", "pension_income", "disability_income",
                        "alimony_income", "child_support_income", "other_income"
                    ))
                values["9A.8"] = f"{_inc:.2f}"
            if not values.get("9B.8"):
                _exp = _to_float(financial.get("total_monthly_expenses")) or 0.0
                if _exp == 0.0:
                    _exp = sum(_to_float(financial.get(k)) or 0.0 for k in (
                        "rent_or_mortgage", "food_expense", "utilities_expense",
                        "child_care_expense", "medical_expense", "transportation_expense",
                        "debt_payments", "other_expenses"
                    ))
                values["9B.8"] = f"{_exp:.2f}"
            # Section 9C: explanation if income < expenses
            try:
                _tot_i = float(str(values.get("9A.8", "0")).replace("$", "").replace(",", ""))
                _tot_e = float(str(values.get("9B.8", "0")).replace("$", "").replace(",", ""))
                if _tot_i < _tot_e and not values.get("9C"):
                    values["9C"] = "Assistance from family and friends, community resources, and prioritizing essential expenses."
            except Exception:
                pass

        if state_code == "CO":
            # Bank Name mapping for Colorado (JDF 205 lines 10A.2B and 10A.3B)
            _bname = financial.get("bank_name") or financial.get("checking_bank_name") or financial.get("savings_bank_name")
            if _bname:
                values["10A.3B"] = str(financial.get("checking_bank_name") or _bname)
                if float(financial.get("savings_balance") or 0) > 0 or financial.get("savings_bank_name"):
                    values["10A.2B"] = str(financial.get("savings_bank_name") or _bname)

            # Household table for Colorado (JDF 205 Section 8)
            # Populates 8A.1-8A.3, 8B.1-8B.3, 8C.1-8C.3, 8D.1-8D.3 and Group8A-Group8D
            raw_members = financial.get("household_members") or financial.get("dependents_detail") or []
            members = []
            if isinstance(raw_members, str):
                if ';' in raw_members:
                    raw_items = [x.strip() for x in raw_members.split(';') if x.strip()]
                elif '\n' in raw_members:
                    raw_items = [x.strip() for x in raw_members.split('\n') if x.strip()]
                else:
                    parts = []
                    current = []
                    depth = 0
                    for char in raw_members:
                        if char == '(':
                            depth += 1
                            current.append(char)
                        elif char == ')':
                            depth = max(0, depth - 1)
                            current.append(char)
                        elif char == ',' and depth == 0:
                            item = ''.join(current).strip()
                            if item:
                                parts.append(item)
                            current = []
                        else:
                            current.append(char)
                    last = ''.join(current).strip()
                    if last:
                        parts.append(last)
                    raw_items = parts
            elif isinstance(raw_members, list):
                raw_items = raw_members
            else:
                raw_items = []

            for item in raw_items:
                if isinstance(item, dict):
                    members.append(item)
                elif isinstance(item, str):
                    item = item.strip()
                    if not item:
                        continue
                    if '(' in item and ')' in item:
                        m = re.match(r'^([^(]+)\(([^)]+)\)$', item)
                        if m:
                            name = m.group(1).strip()
                            extra = m.group(2).strip()
                            parts = [p.strip() for p in extra.split(',')]
                            age = parts[0]
                            rel = parts[1] if len(parts) > 1 else ('Child' if any(c.isdigit() for c in age) and int(re.search(r'\d+', age).group(0)) < 18 else 'Family')
                            members.append({'name': name, 'age': age, 'relationship': rel, 'dependent': True})
                            continue
                    if ',' in item:
                        parts = [p.strip() for p in item.split(',')]
                        name = parts[0]
                        age = parts[1] if len(parts) > 1 else ''
                        rel = parts[2] if len(parts) > 2 else ('Child' if any(c.isdigit() for c in age) and int(re.search(r'\d+', age).group(0)) < 18 else 'Family')
                        members.append({'name': name, 'age': age, 'relationship': rel, 'dependent': True})
                    else:
                        members.append({'name': item, 'age': '', 'relationship': 'Family', 'dependent': True})

            if not members:
                ch_count = int(financial.get("household_children") or 0)
                ad_count = max(0, int(financial.get("household_adults") or 1) - 1)
                members = []
                for idx in range(1, ch_count + 1):
                    members.append({
                        "name": f"Dependent Child {idx}" if ch_count > 1 else "Dependent Child",
                        "age": "Minor",
                        "relationship": "Child",
                        "dependent": True,
                    })
                for idx in range(1, ad_count + 1):
                    members.append({
                        "name": f"Adult Member {idx}" if ad_count > 1 else "Adult Member",
                        "age": "Adult",
                        "relationship": "Roommate/Family",
                        "dependent": False,
                    })

            row_letters = ["A", "B", "C", "D"]
            for idx, member in enumerate(members[:4]):
                if not isinstance(member, dict):
                    continue
                row_letter = row_letters[idx]
                values[f"8{row_letter}.1"] = str(member.get("name", ""))
                values[f"8{row_letter}.2"] = str(member.get("age", ""))
                values[f"8{row_letter}.3"] = str(member.get("relationship", ""))
                dep = bool(member.get("dependent", True))
                financial[f"dep_{idx+1}_dependent"] = dep
                _all_data[f"dep_{idx+1}_dependent"] = dep
                if "financial_info" in data and isinstance(data["financial_info"], dict):
                    data["financial_info"][f"dep_{idx+1}_dependent"] = dep

            # Colorado JDF 205 Section 10: "Is there anything else you want the court to know about your financial situation?" (10C)
            if not values.get("10C"):
                _hardship = pref.get("hardship_reason") or ""
                if _hardship:
                    values["10C"] = str(_hardship).strip()

            # Colorado JDF 205 Section 9A: Self-employment description (9A.6A)
            _self_emp = _to_float(financial.get("self_employment_income") or 0.0)
            if _self_emp > 0 and not values.get("9A.6A"):
                values["9A.6A"] = str(financial.get("employer_name") or "Self-employed")

        # Additional native fields that hold the tenant's full name (e.g. the "I, ___"
        # affidavit blank and the "Petitioner" line) beyond the single mapped name field.
        for fname in config.get("fee_waiver_name_fields", []):
            if fname not in values:
                values[fname] = p.get("full_name", "")

        # KY AOC-026: populate dependents count/relationship, marital status,
        # public assistance (SNAP, K-TAP, LIHEAP), and bank accounts.
        if state_code == "KY" and form_key == "fee_waiver_form":
            try:
                _ch = int(financial.get("household_children") or 0)
            except (TypeError, ValueError):
                _ch = 0
            try:
                _adults = int(financial.get("household_adults") or 1)
            except (TypeError, ValueError):
                _adults = 1
            if _ch:
                values["Text Field 16"] = str(_ch)
                values["Text Field 17"] = "Children"
            values["Text Field 14"] = "Single" if _adults <= 1 else "Married"

            # SNAP / Food Stamps (Text Field 20)
            if financial.get("receives_snap"):
                _snap = financial.get("snap_amount") or financial.get("food_stamps_amount")
                values["Text Field 20"] = str(_snap).lstrip("$") if _snap else "Yes"

            # K-TAP / TANF (Text Field 25)
            if financial.get("receives_tanf"):
                _tanf = financial.get("tanf_income") or financial.get("public_assistance_income")
                values["Text Field 25"] = str(_tanf).lstrip("$") if _tanf else "Yes"

            # LIHEAP (Text Field 27)
            if financial.get("receives_liheap") or financial.get("receives_energy_assistance"):
                values["Text Field 27"] = "Yes"

            # Bank accounts: checking & savings (Assests 2 & Assests 3)
            if "cash_on_hand" in financial:
                if not values.get("Assests 2"):
                    values["Assests 2"] = "0.00"
                if not values.get("Assests 3"):
                    values["Assests 3"] = "0.00"

        # Illinois Fee Waiver (ATJ 601.9):
        if state_code == "IL":
            # Section 1: For Myself
            values["5 - Checkboxes"] = "For Myself"

            # Section 2: Household adults (not counting myself) & children
            _ha = financial.get("household_adults")
            if _ha is not None:
                try:
                    _adults_val = int(float(str(_ha)))
                    values["8 - # of Adults"] = str(max(0, _adults_val - 1))
                except (ValueError, TypeError):
                    pass
            _hc = financial.get("household_children")
            if _hc is not None:
                try:
                    values["9 - Number of Children Under 18"] = str(int(float(str(_hc))))
                except (ValueError, TypeError):
                    pass

            # Section 5: Hardship
            _hardship = str(pref.get("hardship_reason") or "").strip()
            if _hardship and not values.get("107-110 - Hardship"):
                values["107-110 - Hardship"] = _hardship

            # Hearing preference (Section 6 / Page 4)
            _is_remote = bool(pref.get("hearing_format") == "remote" or pref.get("prefers_remote"))
            values["111 - Checkboxes"] = "Remote" if _is_remote else "In-Person"

        # Georgia Fee Waiver: split vehicle year/make/model into separate native
        # fields, populate dependents schedule, employer, bank accounts, liabilities, and hardship.
        if state_code == "GA":
            _v = str(financial.get("vehicle_make_model") or "").strip().split()
            if len(_v) >= 3 and _v[0].isdigit() and len(_v[0]) == 4:
                values["Year"] = _v[0]
                values["Make"] = _v[1]
                values["Model"] = " ".join(_v[2:])
            elif len(_v) == 2 and _v[0].isdigit() and len(_v[0]) == 4:
                values["Year"] = _v[0]
                values["Make"] = _v[1]

            # GA Fee Waiver Page 2: Dependents Table
            _deps = financial.get("dependents_detail") or financial.get("household_members")
            _ch_count = int(financial.get("household_children") or 0)
            _dep_fields = ["undefined_5", "undefined_6", "undefined_7", "undefined_8", "undefined_9"]
            _dep_yes = ["Check Box8", "Check Box9", "Check Box10", "Check Box11", "Check Box12"]
            _dep_no = ["Check Box17", "Check Box16", "Check Box15", "Check Box14", "Check Box13"]
            if _deps and isinstance(_deps, list):
                for idx, dep in enumerate(_deps[:5]):
                    if isinstance(dep, dict):
                        d_name = dep.get("name") or f"Dependent {idx+1}"
                        d_age = dep.get("age") or "Minor"
                        d_rel = dep.get("relationship") or "Child"
                        values[_dep_fields[idx]] = f"{d_name}, Age {d_age}, {d_rel}"
                    else:
                        values[_dep_fields[idx]] = str(dep)
                    values[_dep_yes[idx]] = "Yes"
                    values[_dep_no[idx]] = "Off"
            elif _ch_count > 0:
                for idx in range(min(_ch_count, 5)):
                    values[_dep_fields[idx]] = f"Child {idx+1}, Minor, Dependent Child"
                    values[_dep_yes[idx]] = "Yes"
                    values[_dep_no[idx]] = "Off"

            # GA Fee Waiver Page 3: Employer Details
            _emp_name = financial.get("employer_name") or ""
            _emp_phone = financial.get("employer_phone") or ""
            _emp_wage = _to_float(financial.get("employment_income") or financial.get("monthly_gross_income") or 0.0)
            _is_emp = financial.get("is_employed")
            if _emp_name or _is_emp or _emp_wage > 0:
                _parts = []
                if _emp_name:
                    _parts.append(str(_emp_name))
                if _emp_phone:
                    _parts.append(str(_emp_phone))
                if _emp_wage > 0:
                    _parts.append(f"${_emp_wage:,.2f}/mo")
                values["Employer Name 1"] = " | ".join(_parts) if _parts else "Employed"

            # GA Fee Waiver Page 4: Checking & Savings Financial Institutions
            _bname = financial.get("checking_bank_name") or financial.get("bank_name")
            if _bname and not values.get("If so at what financial institution"):
                values["If so at what financial institution"] = str(_bname)
            _sbname = financial.get("savings_bank_name") or financial.get("bank_name")
            if _sbname and not values.get("If so at what financial institution_2"):
                values["If so at what financial institution_2"] = str(_sbname)

            # GA Fee Waiver Page 5: Liabilities Breakdown & Total
            _rent = _to_float(financial.get("rent_or_mortgage") or c.get("monthly_rent") or 0.0)
            _debt = _to_float(financial.get("debt_payments") or 0.0)
            _debt_bal = _to_float(financial.get("debt_owed") or financial.get("total_debt_owed") or financial.get("debt_balance") or 0.0)
            _med = _to_float(financial.get("medical_expense") or 0.0)

            row_idx = 1
            if _rent > 0:
                values[f"Source of Debt {row_idx}"] = "Housing rent"
                values[f"Total Amount Owed {row_idx}"] = "Current"
                values[f"Monthly Payment {row_idx}"] = f"{_rent:,.2f}"
                row_idx += 1
            if _debt > 0 or _debt_bal > 0:
                values[f"Source of Debt {row_idx}"] = "Credit cards / personal loans"
                values[f"Total Amount Owed {row_idx}"] = f"{_debt_bal:,.2f}" if _debt_bal > 0 else "N/A"
                values[f"Monthly Payment {row_idx}"] = f"{_debt:,.2f}"
                row_idx += 1
            if _med > 0 and row_idx <= 4:
                values[f"Source of Debt {row_idx}"] = "Medical expenses"
                values[f"Total Amount Owed {row_idx}"] = "N/A"
                values[f"Monthly Payment {row_idx}"] = f"{_med:,.2f}"
                row_idx += 1

            _liab = _rent + _debt
            if _liab > 0:
                values["Total_2"] = f"{_liab:,.2f}"

            # GA Fee Waiver Page 6: Other Circumstances / Hardship Statement
            _hardship = str(pref.get("hardship_reason") or "").strip()
            if _hardship:
                values["Check Box3"] = "Yes"
                values["Check Box4"] = "Off"
                _words = _hardship.split()
                _hlines = []
                _cur = []
                for wd in _words:
                    if len(" ".join(_cur + [wd])) <= 80:
                        _cur.append(wd)
                    else:
                        _hlines.append(" ".join(_cur))
                        _cur = [wd]
                if _cur:
                    _hlines.append(" ".join(_cur))
                for l_idx, line in enumerate(_hlines[:4]):
                    values[f"pay the required fees {l_idx+1}"] = line
            else:
                values["Check Box3"] = "Off"
                values["Check Box4"] = "Yes"

        # Connecticut Fee Waiver (JD-CV-120):
        # 1. Total Monthly Income (B+C) = Net employment income (B) + other income (C).
        # 2. Debt schedule row 1 breakdown (DEBTTYPE1, DEBTOWED1, DEBTPAY1).
        # 3. How supported explanation on Page 2 (HOWSUPPORT) if zero income.
        # 4. Other income source description (SOURCE).
        if state_code == "CT":
            _net = _to_float(financial.get("monthly_net_income"))
            if _net is None:
                _net = _to_float(financial.get("employment_income") or financial.get("monthly_gross_income") or 0.0)
            _oth = _to_float(financial.get("other_income") or 0.0)
            _tot_inc = _net + _oth
            values["TOTALMONTHLYINCOME"] = f"${_tot_inc:,.2f}"
            if not values.get("INCOMEOTHER") and _oth == 0.0:
                values["INCOMEOTHER"] = "$0.00"

            _debt_pmt = _to_float(financial.get("debt_payments") or 0.0)
            _debt_owed = _to_float(financial.get("debt_owed") or financial.get("total_debt_owed") or financial.get("debt_balance") or 0.0)
            if _debt_pmt > 0 or _debt_owed > 0:
                if not values.get("topmostSubform[0].Page1[0].DEBTTYPE1[0]"):
                    values["topmostSubform[0].Page1[0].DEBTTYPE1[0]"] = "Credit cards / personal loans"
                if _debt_owed > 0:
                    values["DEBTOWED1"] = f"${_debt_owed:,.2f}"
                    values["DEBTOWEDTOTAL"] = f"${_debt_owed:,.2f}"
                else:
                    values["DEBTOWED1"] = "$0.00"
                    values["DEBTOWEDTOTAL"] = "$0.00"
                if _debt_pmt > 0:
                    values["DEBTPAY1"] = f"${_debt_pmt:,.2f}"
                    values["DEBTPAYTOTAL"] = f"${_debt_pmt:,.2f}"
            else:
                values["DEBTOWED1"] = "$0.00"
                values["DEBTOWEDTOTAL"] = "$0.00"
                values["DEBTPAY1"] = "$0.00"
                values["DEBTPAYTOTAL"] = "$0.00"

            # Ensure zero-value asset and expense schedules have $0.00 defaults
            if not values.get("EQUITYRE"):
                values["EQUITYRE"] = "$0.00"
            if not values.get("REEV"):
                values["REEV"] = "$0.00"
            if not values.get("RELOANBAL"):
                values["RELOANBAL"] = "$0.00"
            if not values.get("EQUITYOPP"):
                values["EQUITYOPP"] = "$0.00"
            if not values.get("OPPEV"):
                values["OPPEV"] = "$0.00"
            if not values.get("OPPLOANBAL"):
                values["OPPLOANBAL"] = "$0.00"
            if not values.get("EQUITYOA"):
                values["EQUITYOA"] = "$0.00"
            for _me_k in ("ME2", "ME5", "ME6", "ME9"):
                if not values.get(_me_k):
                    values[_me_k] = "$0.00"

            # Section 3 Monthly Expenses: map other_expenses or debt_payments to row J (ME10)
            _oth_exp = _to_float(financial.get("other_expenses") or 0.0)
            if _oth_exp > 0:
                values["ME10"] = f"${_oth_exp:,.2f}"
                if not values.get("topmostSubform[0].Page1[0].COLUMN1[0].OTHEREXPENSES[0]"):
                    values["topmostSubform[0].Page1[0].COLUMN1[0].OTHEREXPENSES[0]"] = str(financial.get("other_expenses_description") or "Other expenses")
            elif _debt_pmt > 0:
                values["ME10"] = f"${_debt_pmt:,.2f}"
                if not values.get("topmostSubform[0].Page1[0].COLUMN1[0].OTHEREXPENSES[0]"):
                    values["topmostSubform[0].Page1[0].COLUMN1[0].OTHEREXPENSES[0]"] = "Credit cards / personal loans"

            # Reconcile TOTALME so it matches the exact mathematical sum of lines ME1 through ME10
            _exp_sum = sum(_to_float(values.get(f"ME{i}")) or 0.0 for i in range(1, 11))
            if _exp_sum > 0:
                values["TOTALME"] = f"${_exp_sum:,.2f}"

            _gross = _to_float(financial.get("monthly_gross_income") or 0.0)
            if _gross == 0.0 and _tot_inc == 0.0:
                values["topmostSubform[0].Page2[0].HOWSUPPORT[0]"] = "Assistance from family, friends, and community assistance programs."

            if not values.get("topmostSubform[0].Page1[0].COLUMN1[0].SOURCE[0]"):
                _sources = []
                if financial.get("receives_snap"):
                    _sources.append("SNAP")
                if financial.get("receives_medicaid"):
                    _sources.append("Medicaid")
                if financial.get("receives_ssi"):
                    _sources.append("SSI")
                if financial.get("receives_tanf"):
                    _sources.append("TFA / TANF")
                if financial.get("unemployment_income"):
                    _sources.append("Unemployment")
                if financial.get("disability_income"):
                    _sources.append("Disability")
                if financial.get("pension_income"):
                    _sources.append("Pension")
                if _sources:
                    values["topmostSubform[0].Page1[0].COLUMN1[0].SOURCE[0]"] = ", ".join(_sources)
    
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
        "def_repairs": ["def_repairs", "def_conditions", "def_failed_repair", "def_repair", "def_failed_maintain", "def_habitability", "def_disagree_7", "box 7.", "def_no_free_pay", "def_costs_not_rent", "def_deny_all"],
        "def_amount": ["def_amount", "def_amount_wrong", "def_disagree_amount", "def_no_rent_due", "def_not_owed", "def_dispute_amount", "def_disagree_5", "def_disagree_8", "8. disagree that", "def_disagree_9", "9. disagree", "def_admit_partial", "def_deny_all"],
        "def_attempted_pay": ["def_attempted_pay", "def_offered_pay", "def_offered_refused", "def_tried_to_pay", "def_refused_payment", "def_refused_rent", "def_partial_payment", "def_deny_all"],
        "def_paid": ["def_paid", "def_rent_paid", "def_rent_paid_full", "def_admit_all", "def_deny_all"],
        "def_waived": ["def_waived", "def_waiver", "def_deny_all"],
        "def_retaliation": ["def_retaliation", "def_contest", "def_deny_all"],
        "def_fair_housing": ["def_fair_housing", "def_discrimination", "def_deny_all"],
        "def_accepted_rent": ["def_accepted_rent", "def_accepted_late", "def_foreclosure", "def_deny_all"],
        "def_corrected": ["def_corrected", "def_cured", "def_did_repairs", "def_moved_out", "def_deny_all"],
        "def_not_owner": ["def_not_owner", "def_landlord_not_entitled", "def_ownership", "def_disagree_3", "def_deny_all"],
        "def_regulated_housing": ["def_regulated_housing", "def_disagree_6", "box 6.", "def_deny_all"],
        "def_bad_notice": ["def_bad_notice", "def_no_notice", "def_invalid", "def_improper_notice", "def_late_fee", "def_deny_all"],
        "def_other": ["def_other", "def_other2", "def_other_defenses", "def_admit_all", "def_partial", "def_deny_all", "def_contest", "def_jury_trial", "def_no_breach", "def_lease_violation", "def_justifiable", "def_disagree_10", "10 disagree", "def_costs_not_rent", "def_no_free_pay", "def_late_fee", "def_foreclosure", "def_moved_out", "def_partial_payment", "def_discrimination"],
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

    # Master "Affirmative Defenses" checkbox — auto-select when any defense applies.
    if any(isinstance(d, dict) and d.get("checked") for d in defenses.values()):
        values["√ Affirmative Defenses"] = "Yes"
    if data.get("preferences", {}).get("trial_by") == "jury":
        values["√  Jury Trial"] = "Yes"
    # Louisiana LSBA answer Section 1: auto-check the "I have exceptions and/or
    # defenses..." master box whenever any defense is asserted (intake carries
    # no separate def_exceptions flag).
    if state_code == "LA" and any(isinstance(d, dict) and d.get("checked") for d in defenses.values()):
        values["I have exceptions andor defenses to the claims made in the eviction paperwork"] = "Yes"

    # South Carolina SCCA703: resolve mutually exclusive defenses and populate explanation fields
    if state_code == "SC" and form_key == "answer_form":
        _rent_info = data.get("rent_payment", {})
        _claimed = _to_float(c.get("complaint_amount_claimed") or 0.0)
        _believed = _to_float(_rent_info.get("amount_tenant_believes_owed") or 0.0)
        _agree = _rent_info.get("agree_with_amount", True)

        if not _agree and _believed > 0:
            values["I admit that I am responsible, but not for the total amount claimed by the Plaintiff(s)"] = "Yes"
            values["I deny that I am responsible at all"] = "Off"
            _reason = f"Plaintiff claims ${_claimed:,.2f}, but Defendant believes the proper amount is ${_believed:,.2f}."
            _amt_def = defenses.get("def_amount", {})
            if isinstance(_amt_def, dict) and _amt_def.get("explanation"):
                _reason += f" {_amt_def['explanation']}"
            elif _rent_info.get("why_disagree"):
                _reason += f" {_rent_info['why_disagree']}"
            values["Reason Not Responsible for Total Amount Claimed, Use Additional Pages if Necessary"] = _reason
            values["Reason Not Responsible at All For Amount Claimed, Use Additional Pages if Necessary"] = ""
        else:
            values["I deny that I am responsible at all"] = "Yes"
            values["I admit that I am responsible, but not for the total amount claimed by the Plaintiff(s)"] = "Off"
            _active_reasons = []
            for _k in ("def_amount", "def_repairs", "def_bad_notice", "def_paid", "def_retaliation", "def_fair_housing"):
                _d = defenses.get(_k, {})
                if isinstance(_d, dict) and _d.get("checked") and _d.get("explanation"):
                    _active_reasons.append(_d["explanation"])
            _reason = "; ".join(_active_reasons) if _active_reasons else "Defendant denies all allegations of the Complaint and denies owing the amount claimed."
            values["Reason Not Responsible at All For Amount Claimed, Use Additional Pages if Necessary"] = _reason
            values["Reason Not Responsible for Total Amount Claimed, Use Additional Pages if Necessary"] = ""

        if values.get("I contest the jurisdiction of the court") == "Yes":
            _contest_exp = defenses.get("def_contest", {}).get("explanation") if isinstance(defenses.get("def_contest"), dict) else ""
            values["Reason of Contestation, Use Additional Pages if Necessary"] = _contest_exp or "Defendant contests the jurisdiction of this Court."

    # South Carolina SCCA405 Fee Waiver: set circuit and clean fields
    if state_code == "SC" and form_key == "fee_waiver_form":
        _cty_key = str(p.get("county") or "").strip().lower().replace(" county", "").strip()
        _circuit = SC_COUNTY_TO_CIRCUIT.get(_cty_key)
        if _circuit:
            values["Select Judicial Circuit Number"] = _circuit
        if _cty_key:
            values["Select the County"] = _cty_key.title()
        values["Plaintiff’s Address"] = _compose_full_address(p, state_code)
        values["Plaintiff’s Age"] = ""
        values["Plaintiff’s Occupation"] = ""
        values["Plaintiff’s Employer"] = ""
        values["Employer Address"] = ""

    # Virginia DC-442 Grounds of Defense: populate numbered defense paragraphs User.1 - User.5
    if state_code == "VA" and form_key == "answer_form":
        active_defenses = []
        for _k, _label in [
            ("def_amount", "Dispute of amount claimed: "),
            ("def_repairs", "Failure to maintain premises / repairs: "),
            ("def_bad_notice", "Defective or lack of notice: "),
            ("def_paid", "Rent paid: "),
            ("def_attempted_pay", "Tender of rent refused: "),
            ("def_retaliation", "Retaliation: "),
            ("def_fair_housing", "Discrimination: "),
            ("def_other", "Additional defense: "),
        ]:
            _d = defenses.get(_k, {})
            if isinstance(_d, dict) and _d.get("checked"):
                _expl = _d.get("explanation", "").strip()
                active_defenses.append(f"{_label}{_expl}" if _expl else _label.rstrip(": "))
        for idx in range(5):
            fld = f"User.{idx + 1}"
            if idx < len(active_defenses):
                values[fld] = active_defenses[idx]
            else:
                values[fld] = ""
        values["User.CB1"] = "Yes" if len(active_defenses) > 5 else "Off"

    # Populate per-item explanation text areas (e.g. DC 111a "details N" fields)
    # with the tenant's defense explanations.
    for detail in config.get("defense_details", []):
        dkey = detail.get("key", "")
        dfld = detail.get("field", "")
        if not dkey or not dfld:
            continue
        ddata = defenses.get(dkey, {})
        if isinstance(ddata, dict) and ddata.get("checked"):
            explanation = ddata.get("explanation", "")
            if explanation:
                values[dfld] = explanation

    # Aggregate several affirmative defenses into one "Other statements" field
    # (e.g. MI DC 111a Item 11 collects retaliation, notice, fair-housing, etc.).
    for _target_field, _agg_keys in (config.get("defense_details_aggregate") or {}).items():
        _parts = []
        for _k in _agg_keys:
            _d = defenses.get(_k, {})
            if isinstance(_d, dict) and _d.get("checked"):
                _parts.append(_d.get("explanation") or _d.get("label") or _k)
        if _parts:
            values[_target_field] = "; ".join(_parts)

    # Static values: fixed text that doesn't come from user data
    # Used for fields like CA's "In Pro Per" attorney firm notation
    static_values = config.get("static_values", {})
    for pdf_field, static_text in static_values.items():
        values[pdf_field] = static_text

    # CO JDF 103: bind statutory defenses and options when alleged
    if state_code == "CO" and form_key == "answer_form":
        _narr = str(values.get("defense_narrative", "")).lower()
        _why_disagree = str(data.get("rent_payment", {}).get("why_disagree", "")).lower()
        _all_text = f"{_narr} {_why_disagree}"

        # 7E.2: Illegal or unenforceable late fees (C.R.S. 38-12-105)
        # Check if tenant mentions late fees, unallowed interest/charges, or extra fees
        has_late_fee = any(k in _all_text for k in (
            "late fee", "late charge", "interest", "extra", "unauthorized fee",
            "illegal fee", "unallowed fee", "penalty"
        )) or any(
            isinstance(defenses.get(k), dict) and defenses[k].get("checked")
            for k in ("def_amount", "def_unlawful_fees")
        )
        if has_late_fee and (any(k in _all_text for k in ("fee", "extra", "interest", "charge", "late", "dollar", "$")) or (isinstance(defenses.get("def_amount"), dict) and defenses["def_amount"].get("checked"))):
            values["7E.2"] = "Yes"

        # 7E.1: Unallowed fees under lease
        if (isinstance(defenses.get("def_unlawful_fees"), dict) and defenses["def_unlawful_fees"].get("checked")) or "attorney fee" in _all_text or "unallowed fee" in _all_text:
            values["7E.1"] = "Yes"

        # 7E.3: Improper notice / cure period
        if isinstance(defenses.get("def_bad_notice"), dict) and defenses["def_bad_notice"].get("checked"):
            values["7E.3"] = "Yes"

        # 7E.4: Unfair Housing Act violation
        if (isinstance(defenses.get("def_fair_housing"), dict) and defenses["def_fair_housing"].get("checked")) or (isinstance(defenses.get("def_housing_discrimination"), dict) and defenses["def_housing_discrimination"].get("checked")):
            values["7E.4"] = "Yes"

        # 7E.5: Mandatory mediation failure
        if isinstance(defenses.get("def_mediation_failure"), dict) and defenses["def_mediation_failure"].get("checked"):
            values["7E.5"] = "Yes"
            fin = data.get("financial_info", {})
            if fin.get("receives_ssi"):
                values["7E.5A"] = "Yes"
            if fin.get("disability_income") or fin.get("ssdi_income"):
                values["7E.5B"] = "Yes"
            if fin.get("receives_tanf") or fin.get("receives_and"):
                values["7E.5C"] = "Yes"

        # 7F.1 & 7F.2: Other defenses
        _other_def = defenses.get("def_other")
        if isinstance(_other_def, dict) and _other_def.get("checked"):
            _other_exp = str(_other_def.get("explanation") or "").strip()
            if _other_exp:
                _first_line = _other_exp.split("\n")[0].strip()
                if len(_first_line) > 55:
                    _first_line = _first_line[:52] + "..."
                values["7F.1"] = f"{_first_line} (See Section 8)"

        # Certificate of Service method handling
        cos_meth = str(pref.get("certificate_of_service_method") or c.get("certificate_of_service_method") or "").lower()
        if "other" in cos_meth or "hand" in cos_meth:
            values["CoS_Other"] = pref.get("certificate_of_service_other") or c.get("certificate_of_service_other") or "Hand delivery"
        elif "efile" in cos_meth or "online" in cos_meth:
            # If e-filing, clear CoS_Mail
            values["CoS_Mail"] = ""

    # GA Answer Form: Summary for Answer.AdditionalReasons to prevent text truncation/overflow
    if state_code == "GA" and form_key == "answer_form":
        _narr = str(values.get("Answer.AdditionalReasons") or "").strip()
        if _narr:
            if len(_narr) > 55 or "\n" in _narr:
                _def_labels = []
                for _dk in ("def_repairs", "def_amount", "def_bad_notice", "def_not_owner", "def_other", "def_attempted_pay", "def_corrected", "def_paid"):
                    if isinstance(defenses.get(_dk), dict) and defenses[_dk].get("checked"):
                        _lbl = defenses[_dk].get("label") or _dk.replace("def_", "").replace("_", " ").title()
                        _def_labels.append(_lbl)
                _summary = ", ".join(_def_labels[:3]) if _def_labels else "See attached"
                values["Answer.AdditionalReasons"] = f"See attached Defenses (Doc 05): {_summary}"
            values["Reason.LandlordNotEntitled"] = "Yes"

    # IL Eviction Answer Form (il_eviction_answer.pdf)
    if state_code == "IL" and form_key == "answer_form":
        # 1. Defenses & Supporting Facts
        # Bad notice (43 + 44)
        if any(isinstance(defenses.get(k), dict) and defenses[k].get("checked") for k in ("def_bad_notice", "def_notice")):
            values["43 - Checkbox"] = "Yes"
            values["44 - Checkbox"] = "Yes"

        # Repairs / Habitability (52 + 53, 54, 55)
        if any(isinstance(defenses.get(k), dict) and defenses[k].get("checked") for k in ("def_repairs", "def_conditions", "def_habitability")):
            values["52 - Checkbox"] = "Yes"
            _rep_exp = (defenses.get("def_repairs", {}) or {}).get("explanation") or ""
            if not _rep_exp:
                for k in ("def_conditions", "def_habitability"):
                    if isinstance(defenses.get(k), dict) and defenses[k].get("explanation"):
                        _rep_exp = defenses[k]["explanation"]
                        break
            values["53 - Serious Problems"] = _rep_exp or "See attached Defenses (Doc 05): Bad Property Conditions"
            _r_date = data.get("rent_payment", {}).get("repair_notice_date") or _all_data.get("repair_notice_date") or "Ongoing"
            values["54 - Date"] = str(_r_date)
            values["55 - Date"] = "Not repaired"

        # Cure / Corrected (48 + 49)
        if any(isinstance(defenses.get(k), dict) and defenses[k].get("checked") for k in ("def_corrected", "def_cured")):
            values["48 - Checkbox"] = "Yes"
            _cor_exp = (defenses.get("def_corrected", {}) or {}).get("explanation") or "Cured alleged lease violation within notice period."
            values["49 - Additional Details"] = _cor_exp

        # Retaliation (63 + 67 + 74.1)
        if any(isinstance(defenses.get(k), dict) and defenses[k].get("checked") for k in ("def_retaliation", "def_retaliate")):
            values["63 - Checkbox"] = "Yes"
            values["67 - "] = "Yes"
            _ret_exp = (defenses.get("def_retaliation", {}) or {}).get("explanation") or "Exercised tenant rights / requested repairs."
            values["74.1 - What You Told Them or Did"] = _ret_exp

        # Waiver (77 + 78 + 80)
        if any(isinstance(defenses.get(k), dict) and defenses[k].get("checked") for k in ("def_waived", "def_accepted_rent")):
            values["77 - Checkbox"] = "Yes"
            _w_date = data.get("rent_payment", {}).get("rent_paid_date") or "After notice"
            values["78 - Date"] = str(_w_date)
            values["80 - Details"] = "Landlord accepted rent payment after issuing notice, waiving notice."

        # Tender / Refusal to accept payment (84 + 85 + 86 + 87)
        if any(isinstance(defenses.get(k), dict) and defenses[k].get("checked") for k in ("def_attempted_pay", "def_tender")):
            values["84 - Checkbox"] = "Yes"
            _p_date = data.get("rent_payment", {}).get("rent_paid_date") or "Before filing"
            values["85 - Date"] = str(_p_date)
            _rent_amt = c.get("monthly_rent") or data.get("rent_payment", {}).get("monthly_rent") or ""
            if _rent_amt:
                values["86 - Amount"] = f"{_to_float(_rent_amt):,.2f}"
            values["87 - Details"] = "Offered full rent payment within notice period, but landlord refused to accept."

        # Disputed amount / Other affirmative defense (90 + 91 + 92)
        if any(isinstance(defenses.get(k), dict) and defenses[k].get("checked") for k in ("def_amount", "def_other")):
            values["90 - Checkbox"] = "Yes"
            if isinstance(defenses.get("def_amount"), dict) and defenses["def_amount"].get("checked"):
                values["91 - Other Affirmative Defense"] = "Improper Rent Claimed / Accounting Dispute"
                values["92 - Facts"] = defenses["def_amount"].get("explanation") or "Dispute amount of rent/fees claimed by landlord."
            else:
                values["91 - Other Affirmative Defense"] = "Other Affirmative Defense"
                values["92 - Facts"] = (defenses.get("def_other", {}) or {}).get("explanation") or "See attached Defenses (Doc 05)"

        # 2. Service / Proof of Delivery (Pages 5-6)
        cos_meth = str(pref.get("certificate_of_service_method") or c.get("certificate_of_service_method") or "regular_mail").lower()
        if "efile" in cos_meth or "email" in cos_meth or "electronic" in cos_meth:
            values["4 - By checkboxes"] = "Electronically"
            values["4 - Email / EFSP checkboxes"] = "Email"
            values["1A - Email of Party - Page 4"] = l.get("landlord_email") or ""
        else:
            values["4 - By checkboxes"] = "Sending Another Way"
            values["4 - Sending the Document"] = "Mail or 3rd Party Carrier"
            values["4 - Document Date"] = today.strftime("%m/%d/%Y")
            values["4 - Sent Time"] = "9:00 AM"

        values["4B - Delivery Address"] = ""

    # IN Fee Waiver form handling (CCA-GF-0819-3004)
    if state_code == "IN" and form_key == "fee_waiver_form":
        # Item 3: "I live with the following persons who are over eighteen (18) years of age"
        adults = int(financial.get("household_adults") or 1)
        if adults <= 1:
            values["HouseholdAdults"] = "None (applicant only)"
        else:
            values["HouseholdAdults"] = f"{adults - 1} other adult(s)"

        # Item 4: "I live with the following persons who are under eighteen (18) years of age"
        children = int(financial.get("household_children") or 0)
        if children == 0:
            values["HouseholdChildren"] = "None"
        elif children == 1:
            values["HouseholdChildren"] = "1 minor child"
        else:
            values["HouseholdChildren"] = f"{children} minor children"

        # Item 5: "I am responsible for the financial support of the following people who live in my household"
        if children > 0:
            values["FinancialSupport"] = f"{children} minor child" if children == 1 else f"{children} minor children"
        elif adults > 1:
            values["FinancialSupport"] = f"Self and {adults - 1} other adult(s)"
        else:
            values["FinancialSupport"] = "Self only"

        # Monthly benefits (AFDC/TANF row)
        tanf_val = financial.get("tanf_income") or financial.get("public_assistance_income") or "0.00"
        if config.get("strip_dollar_signs"):
            tanf_val = str(tanf_val).lstrip("$")
        values["MonthlyBenefits"] = str(tanf_val) if tanf_val else "0.00"

        # Zero fill unpopulated expense items to avoid lone "$" in template
        if not values.get("MonthlyInsurance"):
            values["MonthlyInsurance"] = "0.00"
        if not values.get("MonthlyChildSupportPaid"):
            values["MonthlyChildSupportPaid"] = "0.00"

    # LA Fee Waiver form handling
    if state_code == "LA" and form_key == "fee_waiver_form":
        # Section 5: Children Live With You & Other Dependents
        ch_count = int(financial.get("household_children") or 0)
        ad_count = max(0, int(financial.get("household_adults") or 1) - 1)
        values["Children Live With You"] = str(ch_count) if ch_count > 0 else "0"
        values["Any other Dependents"] = str(ad_count) if ad_count > 0 else "0"

        # Dependents table (Rows 1 to 5)
        raw_members = financial.get("household_members") or financial.get("dependents_detail") or []
        la_members = []
        if isinstance(raw_members, list):
            for item in raw_members:
                if isinstance(item, dict):
                    la_members.append(item)
                elif isinstance(item, str) and item.strip():
                    la_members.append({"name": item.strip(), "age": "Minor", "relationship": "Child"})
        elif isinstance(raw_members, str) and raw_members.strip():
            for part in re.split(r'[;\n]+', raw_members):
                part = part.strip()
                if part:
                    la_members.append({"name": part, "age": "Minor", "relationship": "Child"})

        if not la_members:
            for idx in range(1, ch_count + 1):
                la_members.append({
                    "name": f"Dependent Child {idx}" if ch_count > 1 else "Dependent Child",
                    "age": "Minor",
                    "relationship": "Child",
                })
            for idx in range(1, ad_count + 1):
                la_members.append({
                    "name": f"Adult Member {idx}" if ad_count > 1 else "Adult Member",
                    "age": "Adult",
                    "relationship": "Family",
                })

        for idx, m in enumerate(la_members[:5]):
            row_num = idx + 1
            values[f"Dependents Name 0{row_num}"] = str(m.get("name", ""))
            values[f"Dependents Age 0{row_num}"] = str(m.get("age", ""))
            values[f"Dependents Relationship 0{row_num}"] = str(m.get("relationship", ""))

        # Item 4: Student status
        if not financial.get("is_student"):
            values["Student - No"] = "Yes"
            values["Student - Yes"] = "Off"

        # Item 7: Net monthly income & tax deductions
        inc = _to_float(financial.get("monthly_net_income") or financial.get("monthly_gross_income") or financial.get("employment_income") or 0.0)
        if inc > 0:
            values["Total Net Monthly Income"] = f"{inc:,.2f}"
        if not values.get("Monthly Federal Tax Deductions"):
            values["Monthly Federal Tax Deductions"] = "0.00"
        if not values.get("Monthly FICA Tax Deductions"):
            values["Monthly FICA Tax Deductions"] = "0.00"
        if not values.get("Total Monthly Deductions"):
            values["Total Monthly Deductions"] = "0.00"

        # Section 8(b): Public assistance checkboxes and fields
        has_support = any(
            bool(financial.get(k)) for k in (
                "receives_snap", "receives_tanf", "receives_ssi", "receives_medicaid",
                "receives_public_benefits", "ssi_income", "disability_income", "unemployment_income"
            )
        )
        if has_support:
            values["Any Support - Yes"] = "Yes"
            values["Any Support - No"] = "Off"
            if financial.get("receives_snap"):
                _snap = financial.get("snap_amount") or financial.get("food_stamps_amount")
                values["Food Stamps"] = f"{_to_float(_snap):,.2f}" if _snap else "Yes"
            if financial.get("receives_tanf"):
                _tanf = financial.get("tanf_income") or financial.get("public_assistance_income")
                values["TANF"] = f"{_to_float(_tanf):,.2f}" if _tanf else "Yes"
            if financial.get("receives_ssi") or financial.get("ssi_income"):
                _ssi = financial.get("ssi_income")
                values["SSI Support"] = f"{_to_float(_ssi):,.2f}" if _ssi else "Yes"
        else:
            values["Any Support - Yes"] = "Off"
            values["Any Support - No"] = "Yes"

        # Bank accounts
        _bank = financial.get("checking_bank_name") or financial.get("bank_name") or financial.get("savings_bank_name")
        if _bank:
            values["Name/Location of Bank"] = str(_bank)
        if financial.get("checking_balance") or financial.get("cash_on_hand") or financial.get("has_bank_account"):
            values["Checking"] = "Yes"

        # Section B.i: Living expenses subtotal
        rent = _to_float(financial.get("rent_or_mortgage") or 0.0)
        util = _to_float(financial.get("utilities_expense") or 0.0)
        food = _to_float(financial.get("food_expense") or 0.0)
        trans = _to_float(financial.get("transportation_expense") or 0.0)
        med = _to_float(financial.get("medical_expense") or 0.0)
        daycare = _to_float(financial.get("child_care_expense") or 0.0)
        subtotal_i = rent + util + food + trans + med + daycare
        if subtotal_i > 0:
            values["Total Itemized Monthly Expenses"] = f"{subtotal_i:,.2f}"

        # Section B.ii: Credit cards / loans
        debt = _to_float(financial.get("debt_payments") or 0.0)
        if debt > 0:
            values["Credit Card Name 01"] = "Credit Card / Personal Debts"
            values["Credit Card Monthly Payment 01"] = f"{debt:,.2f}"
            values["Total Monthly Credit Card Payment"] = f"{debt:,.2f}"
        if not values.get("Total Monthly Financial Loans"):
            values["Total Monthly Financial Loans"] = "0.00"

        # Page 3 questions
        values["Help with Expenses - No"] = "Yes"
        values["Help with Expenses - Yes"] = "Off"
        values["Additional Income/Assets - No"] = "Yes"
        values["Additional Income/Assets - Yes"] = "Off"
        values["False Answer - Yes"] = "Yes"
        values["False Answer - No"] = "Off"

    # MI Fee Waiver form handling (Form MC 20)
    if state_code == "MI" and form_key == "fee_waiver_form":
        cat_keys = ("receives_snap", "receives_ssi", "receives_tanf", "receives_medicaid", "receives_public_benefits")
        has_cat = any(bool(financial.get(k)) for k in cat_keys)
        if has_cat:
            values["Option 1 of 2: I Receive Public Assistance Because Of Indigence"] = "Yes"
            values["3 I am unable to pay the fees and I did not check item 1 or 2 above"] = "Off"
            values["Week and or Two Weeks and or  Month and or Year "] = ""
            values["My Gross Household Income is in Dollars"] = ""
            values["Number in household"] = ""
            values["My Source Of Income Is"] = ""
            values["Assets"] = ""
            values["Obligations"] = ""
        else:
            values["Option 1 of 2: I Receive Public Assistance Because Of Indigence"] = "Off"
            values["3 I am unable to pay the fees and I did not check item 1 or 2 above"] = "Yes"
            if not values.get("Week and or Two Weeks and or  Month and or Year "):
                values["Week and or Two Weeks and or  Month and or Year "] = "Month"

    # CT JD-HM-5: Summary Process Answer defenses and service handling
    if state_code == "CT" and form_key == "answer_form":
        # Rent paid after notice (Box a):
        if (data.get("rent_payment", {}).get("paid_after_notice") is True) or any(
            isinstance(defenses.get(k), dict) and defenses[k].get("checked") for k in ("def_paid", "def_paid_after_notice")
        ):
            values["form1[0].FRONT[0].RENTPAID[0]"] = "Yes"
        # Habitability / Code violations (Boxes d and e):
        if any(isinstance(defenses.get(k), dict) and defenses[k].get("checked") for k in ("def_repairs", "def_conditions", "def_habitability")):
            values["form1[0].FRONT[0].NORENTDUE[0]"] = "Yes"
            values["form1[0].FRONT[0].NOTIFIED[0]"] = "Yes"
            values["form1[0].FRONT[0].NOTE[0]"] = "Yes"
            _rep_exp = (defenses.get("def_repairs", {}) or {}).get("explanation") or ""
            if _rep_exp:
                values["form1[0].FRONT[0].CODEVIOLA[0]"] = _rep_exp
            _r_date = _all_data.get("repair_notice_date") or _all_data.get("date_note")
            if _r_date:
                values["form1[0].FRONT[0].DATENOTE[0]"] = str(_r_date)

        # Retaliation (Box f):
        if any(isinstance(defenses.get(k), dict) and defenses[k].get("checked") for k in ("def_retaliation", "def_retaliate")):
            values["form1[0].FRONT[0].EVICTION[0]"] = "Yes"
            values["form1[0].FRONT[0].LANDLORD[0]"] = "Yes"

        # Pre-termination cure (Box j):
        if any(isinstance(defenses.get(k), dict) and defenses[k].get("checked") for k in ("def_corrected", "def_cured", "def_pre_termination")):
            values["form1[0].FRONT[0].PRETERMINATION[0]"] = "Yes"

        # Tender of rent refused (Box b):
        if any(isinstance(defenses.get(k), dict) and defenses[k].get("checked") for k in ("def_attempted_pay", "def_offered_pay")):
            values["form1[0].FRONT[0].RENTOFFERED[0]"] = "Yes"
            _p_date = _all_data.get("rent_payment_date") or _all_data.get("date_offered")
            if _p_date:
                values["form1[0].FRONT[0].DATEOFFERED[0]"] = str(_p_date)

        # Rent accepted / waived (Box c):
        if any(isinstance(defenses.get(k), dict) and defenses[k].get("checked") for k in ("def_accepted_rent", "def_waived")):
            values["form1[0].FRONT[0].RENTACCEPTED[0]"] = "Yes"

        # Fair Rent Commission complaint (Box g):
        if any(isinstance(defenses.get(k), dict) and defenses[k].get("checked") for k in ("def_rent_increase", "def_fair_rent")):
            values["form1[0].FRONT[0].RENTINCREA[0]"] = "Yes"
            _i_date = _all_data.get("fair_rent_complaint_date") or _all_data.get("date_increase")
            if _i_date:
                values["form1[0].FRONT[0].DATEINCREASE[0]"] = str(_i_date)

        # Protected tenant status (Box h):
        if any(isinstance(defenses.get(k), dict) and defenses[k].get("checked") for k in ("def_elderly_disabled", "def_disability", "def_senior")):
            values["form1[0].FRONT[0].STATUS[0]"] = "Yes"
            _exp = str((defenses.get("def_elderly_disabled") or {}).get("explanation") or "").lower()
            if re.search(r'\b(6[2-9]|[7-9]\d|\d{2}\s*years?\s*old|senior|elder|older|age)\b', _exp):
                values["form1[0].FRONT[0].AGE[1]"] = "2"
            else:
                values["form1[0].FRONT[0].AGE[0]"] = "1"

        # Foreclosure (Box i):
        if any(isinstance(defenses.get(k), dict) and defenses[k].get("checked") for k in ("def_foreclosure",)):
            values["form1[0].FRONT[0].FORECLOSE[0]"] = "Yes"
            values["form1[0].FRONT[0].LEASE[0]"] = "1"

        # Additional reasons / Other defenses (Box k):
        # Includes def_other, def_bad_notice, def_amount (unauthorized fees/charges)
        other_explanations = []
        for _ok in ("def_other", "def_bad_notice", "def_amount", "def_fair_housing", "def_not_owner"):
            _od = defenses.get(_ok)
            if isinstance(_od, dict) and _od.get("checked"):
                _exp = _od.get("explanation", "").strip()
                if _exp:
                    other_explanations.append(_exp)
                elif _ok == "def_bad_notice":
                    other_explanations.append("Improper or defective notice to quit served.")
        if other_explanations or (isinstance(defenses.get("def_other"), dict) and defenses["def_other"].get("checked")):
            values["form1[0].FRONT[0].ADDITIONALREASONS[0]"] = "Yes"
            if not values.get("form1[0].FRONT[0].ADDINFO[0]"):
                values["form1[0].FRONT[0].ADDINFO[0]"] = "; ".join(other_explanations)

    # RI District Court (DC-53 Answer & DC-66 Fee Waiver)
    if state_code == "RI":
        county_str = str(p.get("county", "") or "").lower()
        city_str = str(p.get("property_city", "") or "").lower()

        # Determine judicial complex
        complex_name = "Garrahy Judicial Complex"  # default 6th Division (Providence/Bristol)
        if any(w in county_str or w in city_str for w in ("newport", "jamestown", "tiverton", "portsmouth", "little compton")):
            complex_name = "Murray Judicial Complex"
        elif any(w in county_str or w in city_str for w in ("kent", "warwick", "coventry", "east greenwich", "west greenwich", "west warwick")):
            complex_name = "Noel Judicial Complex"
        elif any(w in county_str or w in city_str for w in ("washington", "wakefield", "south kingstown", "north kingstown", "narragansett", "westerly")):
            complex_name = "McGrath Judicial Complex"

        if form_key == "answer_form":
            values[complex_name] = "Yes"
            for other_c in ("Garrahy Judicial Complex", "Murray Judicial Complex", "Noel Judicial Complex", "McGrath Judicial Complex"):
                if other_c != complex_name:
                    values[other_c] = "Off"

            # Page 1 pro se defendant contact info
            if not values.get("Attorney for the DefendantTenant or the DefendantTenant"):
                values["Attorney for the DefendantTenant or the DefendantTenant"] = p.get("full_name", "")
            if not values.get("Address of the DefendantTenants Attorney or the DefendantTenant"):
                values["Address of the DefendantTenants Attorney or the DefendantTenant"] = _full_addr or p.get("property_address", "")
            if not values.get("Attorney for the PlaintiffLandlord or the PlaintiffLandlord"):
                values["Attorney for the PlaintiffLandlord or the PlaintiffLandlord"] = l.get("landlord_name", "")
            if not values.get("Address of the PlaintiffLandlords Attorney or the PlaintiffLandlord"):
                values["Address of the PlaintiffLandlords Attorney or the PlaintiffLandlord"] = l.get("landlord_address", "")

            # Page 2 defense details
            if (defenses.get("def_amount", {}) or {}).get("checked") or (defenses.get("def_other", {}) or {}).get("checked"):
                values["I have other defenses as follows"] = "Yes"
                _other_exp = (defenses.get("def_other", {}) or {}).get("explanation") or (defenses.get("def_amount", {}) or {}).get("explanation") or "Dispute amount claimed and unauthorized fees."
                if len(_other_exp) > 42:
                    _words = _other_exp.split()
                    _l1, _l2 = [], []
                    for _w in _words:
                        if len(" ".join(_l1 + [_w])) <= 42:
                            _l1.append(_w)
                        else:
                            _l2.append(_w)
                    values["undefined_2"] = " ".join(_l1)
                    values["undefined_3"] = " ".join(_l2)
                else:
                    values["undefined_2"] = _other_exp
            if (defenses.get("def_retaliation", {}) or {}).get("checked"):
                _ret_exp = (defenses.get("def_retaliation", {}) or {}).get("explanation") or "Asserted legal rights regarding tenancy."
                if len(_ret_exp) > 75:
                    _words = _ret_exp.split()
                    _l1, _l2 = [], []
                    for _w in _words:
                        if len(" ".join(_l1 + [_w])) <= 75:
                            _l1.append(_w)
                        else:
                            _l2.append(_w)
                    values["calling 1"] = " ".join(_l1)
                    values["calling 2"] = " ".join(_l2)
                else:
                    values["calling 1"] = _ret_exp

            # Page 3 signatures (leave blank for physical ink signature) and Certificate of Service
            values["s"] = ""
            values["s_2"] = ""
            if not values.get("Date"):
                values["Date"] = today.strftime("%m/%d/%Y")
            if not values.get("Telephone Number"):
                values["Telephone Number"] = p.get("phone", "")

            # Certificate of Service
            day_num = today.day
            suffix = "th" if 11 <= day_num <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(day_num % 10, "th")
            values["I hereby certify that on the"] = f"{day_num}{suffix}"
            values["day of"] = today.strftime("%B")
            values["20"] = today.strftime("%y")
            values["I mailed or"] = "Yes"
            values["handdelivered this document to the attorney for the opposing party andor"] = "Off"
            values["the opposing party if selfrepresented whose name is"] = l.get("landlord_name", "")
            values["at the following address"] = l.get("landlord_address", "") or "Address of record"

            # Page 4 Caption
            values["Plaintiff"] = l.get("landlord_name", "")
            values["Defendant"] = p.get("full_name", "")
            values["Civil Action File NumberRow1"] = c.get("case_number", "")

        elif form_key == "fee_waiver_form":
            values[complex_name] = "Yes"
            for other_c in ("Garrahy Judicial Complex", "Murray Judicial Complex", "Noel Judicial Complex", "McGrath Judicial Complex"):
                if other_c != complex_name:
                    values[other_c] = "Off"

            # Caption across pages (Tenant is Defendant/Respondent in eviction defense)
            values["PlaintiffPetitioner"] = l.get("landlord_name", "")
            values["DefendantRespondent"] = p.get("full_name", "")
            values["Civil Action File NumberRow1"] = c.get("case_number", "")
            values["PlaintiffPetitioner_2"] = l.get("landlord_name", "")
            values["DefendantRespondent_2"] = p.get("full_name", "")
            values["Civil Action File NumberRow1_2"] = c.get("case_number", "")
            values["PlaintiffPetitioner_3"] = l.get("landlord_name", "")
            values["DefendantRespondent_3"] = p.get("full_name", "")
            values["Civil Action File NumberRow1_3"] = c.get("case_number", "")

            # Page 1 signature (leave blank for ink signature) & contact
            values["s"] = ""
            if not values.get("Date"):
                values["Date"] = today.strftime("%m/%d/%Y")
            if not values.get("Telephone Number"):
                values["Telephone Number"] = p.get("phone", "")

            # Page 2 Financials
            hh_size = financial.get("household_adults") or financial.get("household_size") or 1
            values["The PlaintiffPetitioner states that there are"] = str(hh_size)
            inc_src = financial.get("other_income_description") or financial.get("income_source") or "Employment"
            values["income is"] = str(inc_src)
            gross_inc = _to_float(financial.get("monthly_gross_income") or financial.get("employment_income") or 0.0)
            if gross_inc > 0:
                values["in the amount of"] = f"{gross_inc:,.2f}"

            rent_val = _to_float(financial.get("rent_or_mortgage") or 0.0)
            util_val = _to_float(financial.get("utilities_expense") or 0.0)
            food_val = _to_float(financial.get("food_expense") or 0.0)
            cloth_val = _to_float(financial.get("clothing_expense") or 0.0)
            med_val = _to_float(financial.get("medical_expense") or 0.0)
            trans_val = _to_float(financial.get("transportation_expense") or 0.0)
            diaper_val = _to_float(financial.get("diaper_expense") or financial.get("childcare_expense") or 0.0)
            hh_supp_val = _to_float(financial.get("household_supplies_expense") or 0.0)
            other_val = _to_float(financial.get("other_expenses") or 0.0)
            total_exp = rent_val + util_val + food_val + cloth_val + med_val + trans_val + diaper_val + hh_supp_val + other_val
            if total_exp == 0.0:
                raw_total = _to_float(financial.get("total_monthly_expenses") or 0.0)
                if raw_total > 0.0:
                    rent_val = round(raw_total * 0.55, 2)
                    util_val = round(raw_total * 0.12, 2)
                    food_val = round(raw_total * 0.18, 2)
                    trans_val = round(raw_total * 0.10, 2)
                    hh_supp_val = round(raw_total - (rent_val + util_val + food_val + trans_val), 2)
                    total_exp = raw_total

            values["undefined"] = f"{rent_val:,.2f}" if rent_val > 0 else "0.00"
            values["undefined_2"] = f"{util_val:,.2f}" if util_val > 0 else "0.00"
            values["undefined_3"] = f"{food_val:,.2f}" if food_val > 0 else "0.00"
            values["undefined_4"] = f"{cloth_val:,.2f}" if cloth_val > 0 else "0.00"
            values["undefined_5"] = f"{med_val:,.2f}" if med_val > 0 else "0.00"
            values["undefined_6"] = f"{trans_val:,.2f}" if trans_val > 0 else "0.00"
            values["undefined_7"] = f"{diaper_val:,.2f}" if diaper_val > 0 else "0.00"
            values["Household Supplies"] = f"{hh_supp_val:,.2f}" if hh_supp_val > 0 else "0.00"
            values["undefined_8"] = f"{other_val:,.2f}" if other_val > 0 else "0.00"
            values["undefined_9"] = f"{total_exp:,.2f}" if total_exp > 0 else "0.00"

            # Page 3 Notary Block
            values["State of"] = "Rhode Island"
            values["County of"] = p.get("county", "Providence County")
            day_num = today.day
            suffix = "th" if 11 <= day_num <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(day_num % 10, "th")
            values["On this"] = f"{day_num}{suffix}"
            values["day of"] = today.strftime("%B")
            values["20"] = today.strftime("%y")
            values["personally appeared"] = p.get("full_name", "")
            values["proved to the notary through satisfactory evidence of identification which"] = "Yes"
            values["personally"] = "Off"
            values["was"] = "Government-issued photo ID"

            # Page 4 Order lines: keep judge/court lines blank
            values["Entered as an Order of the court on"] = ""
            values["BY ORDER OF"] = ""
            values["ENTER"] = ""

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
        ("property", _full_addr or p.get("property_address", "")),
        ("street", p.get("property_address", "")),
        ("city or town", p.get("property_city", "")),
        ("signed", today.strftime("%m/%d/%Y")),
        ("date of birth", p.get("date_of_birth", "")),
        ("birth date", p.get("date_of_birth", "")),
        ("dob", p.get("date_of_birth", "")),
    ]
    # Word-boundary-only rules: match "Date" or "Date3" but not "TrialDate" or "BOPDueDate"
    # Also handles camelCase like "ResidenceAddress" → "address"
    word_boundary_rules = [
        (re.compile(r'(?<![a-zA-Z])address|(?<=[a-z])Address', re.IGNORECASE), _full_addr or p.get("property_address", "")),
        (re.compile(r'(?<![a-zA-Z])date(?![a-zA-Z])|(?<=[a-z])Date$', re.IGNORECASE), today.strftime("%m/%d/%Y")),
        (re.compile(r'(?<![a-zA-Z])court(?![a-zA-Z])', re.IGNORECASE), c.get("court_name", "")),
        (re.compile(r'city\s*(?:and|&)\s*state', re.IGNORECASE), f"{p.get('property_city', '')}, {state_code}".strip(", ")),
        (re.compile(r'(?<![a-zA-Z])city', re.IGNORECASE), p.get("property_city", "")),
    ]
    # Field names that should NOT receive auto-fill from substring rules
    auto_fill_skip = re.compile(r'(court|ct|trial|bop|file|attorney|judge|jury|clerk|issue|order|delivery|prison|jail).*(address|date)|'
                                r'landlord.*(accepted|date|payment|partial)|'
                                r'(notice|amount|date).*(landlord)|'
                                r'(damages|owes|reduced|repairs|amt|fees|costs|number|months)|'
                                r'(real.*estate|home|property.*owned|mortgage|other.*assets)|'
                                r'other.*property|property.*text|property.*value|liquid.*asset|'
                                r'plaintiff.*(address|age|occupation|employer)|defendant.*(address|phone|email)|'
                                r'birthday|employer|immovable|(property.*tax|tax.*property)|complaint|'
                                r'(start|fixed|repair|lease|rent|notice|problem).*(date)|'
                                r'(\d+.*-\s*date|document\s*date)|'
                                r'entered as an order|order of the court|by order of|'
                                r'telephone|utility|expense|bill|monthly|section|move[- ]?out|vacate|proposed', re.IGNORECASE)
    
    # Apply to each page
    for page_num in range(len(doc)):
        page = doc[page_num]
        for widget in page.widgets():
            widget = cast(Any, widget)  # PyMuPDF widget: dynamic attributes
            field_name = cast(str, widget.field_name)
            if not field_name:
                continue
            if widget.field_type == pymupdf.PDF_WIDGET_TYPE_TEXT:
                h = widget.rect.height if widget.rect else 0
                val_str = str(values.get(field_name, "") or "")
                if h >= 20.0 or "\n" in val_str:
                    widget.field_flags = (widget.field_flags or 0) | pymupdf.PDF_TX_FIELD_IS_MULTILINE
                else:
                    widget.field_flags = (widget.field_flags or 0) & ~pymupdf.PDF_TX_FIELD_IS_MULTILINE
            
            # 1. Check explicit mapping first
            if field_name in values:
                val = values[field_name]
                if val == "":
                    widget.field_value = " "
                    widget.update()
                    try:
                        doc.xref_set_key(widget.xref, "V", "()")
                    except Exception:
                        pass
                    if skip_financial and state_code == "CO" and field_name in ("9A.8", "9B.8", "9C"):
                        try:
                            doc.xref_set_key(widget.xref, "AA", "null")
                        except Exception:
                            pass
                else:
                    if widget.field_type == pymupdf.PDF_WIDGET_TYPE_CHECKBOX:
                        if isinstance(val, bool):
                            widget.field_value = val
                        elif isinstance(val, str) and val.lower() in ("yes", "on", "true", "1"):
                            widget.field_value = True
                        elif isinstance(val, str) and val.lower() in ("", "off", "no", "false", "0"):
                            widget.field_value = False
                        else:
                            try:
                                os_raw = str(widget.on_state() or "")
                                os_clean = os_raw.replace("#20", " ").replace("#28", "(").replace("#29", ")").strip().lower()
                                val_clean = str(val).strip().lower()
                                widget.field_value = (val_clean in os_clean or os_clean in val_clean)
                            except Exception:
                                widget.field_value = (val not in ("", "Off", "off", False, "False", "0"))
                    else:
                        widget.field_value = val
                    widget.update()
                continue
            
            # 1a. Substring matching for truncated widget names
            matched_substring = False
            for val_key, val_value in list(values.items()):
                if len(val_key) > 30 and len(field_name) > 20:
                    # Skip sibling rows of a repeated section: "…value of the
                    # vehicle" vs "…value of the vehicle_2" are distinct fields;
                    # substring-matching one row's value into another would fill
                    # a second vehicle/account the tenant never reported.
                    if re.sub(r'_\d+$', '', field_name) == re.sub(r'_\d+$', '', val_key) \
                            and field_name != val_key:
                        continue
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
            name_keywords = {"plaintiff", "defendant", "tenant", "landlord", "party1", "party2", "applicant"}
            name_disqualifiers = re.compile(r'(address|street|city|state|zip|phone|tel|email|age|occupation|employer|job|work|attorney|counsel|lawyer|sign|date|dob|birth)', re.IGNORECASE)
            for keyword, value in auto_fill_rules:
                if keyword in name_keywords and name_disqualifiers.search(fn_lower):
                    continue
                if keyword == "property" and re.search(r'(other.*property|property.*text|property.*value|property.*owned|liquid.*asset)', fn_lower):
                    continue
                if value and keyword in fn_lower:
                    widget.field_value = str(value)
                    widget.update()
                    matched = True
                    break
            if matched:
                continue
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
    ("date of birth", "personal_info", "date_of_birth", False),
    ("birth date", "personal_info", "date_of_birth", False),
    ("dob", "personal_info", "date_of_birth", False),
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
        c = d.get("checking_balance")
        s = d.get("savings_balance")
        if c is not None or s is not None:
            return f"{(c or 0) + (s or 0):,.2f}"
        return ""
    if key == "household_size":
        a = d.get("household_adults")
        ch = d.get("household_children")
        if a is not None or ch is not None:
            return str((a or 0) + (ch or 0))
        return ""
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
    clip = pymupdf.Rect(rect.x0 - 60, rect.y0 - 14, rect.x1 + 160, rect.y1 + 14)
    txt = page.get_text("text", clip=clip).lower()
    return any(k in txt for k in ("signature", "notary", "affiant", "officer", "sworn", "subscribed", "witness", "deponent", "attesting"))


def _force_multiline_text_widgets(doc: pymupdf.Document) -> int:
    """Ensure every text widget is multiline and mask filled values' underlines.

    Native form fields (especially on fee-waiver forms) often carry only the
    rich-text flag or no flags at all, so a long value overflows a single line.
    This is a final, idempotent pass applied to every text widget regardless of
    how it was created (native AcroForm, overlay, or auto-detected blank).

    It also gives any widget that already has a value an opaque white background
    so the template's pre-printed underline/line art does not strike through the
    overlaid or native text. Empty fields (and signature lines) stay transparent
    so their printed baseline remains visible.
    """
    changed = 0
    for page in doc:
        for w in page.widgets():
            w = cast(Any, w)
            if getattr(w, "field_type", None) != pymupdf.PDF_WIDGET_TYPE_TEXT:
                continue
            dirty = False
            flags = getattr(w, "field_flags", 0) or 0
            h = w.rect.height if w.rect else 0
            val_str = str(getattr(w, "field_value", "") or "")
            if h >= 20.0 or "\n" in val_str:
                if not (flags & pymupdf.PDF_TX_FIELD_IS_MULTILINE):
                    w.field_flags = flags | pymupdf.PDF_TX_FIELD_IS_MULTILINE  # type: ignore[attr-defined]
                    dirty = True
            else:
                if flags & pymupdf.PDF_TX_FIELD_IS_MULTILINE:
                    w.field_flags = flags & ~pymupdf.PDF_TX_FIELD_IS_MULTILINE  # type: ignore[attr-defined]
                    dirty = True
            if val_str.strip():
                # Only large multi-line narrative areas (height > 30) get an opaque
                # white background to cleanly mask pre-printed ruled lines.
                # Single-line fields keep their transparent background so pre-printed
                # underlines remain continuous without being chopped into dashes.
                if h > 30 and getattr(w, "fill_color", None) is None:
                    w.fill_color = (1, 1, 1)
                    dirty = True
            if dirty:
                try:
                    w.update()
                except Exception:
                    pass
                changed += 1
    return changed


# Field names that mark a signature / notary area. Rebuilt forms commonly use
# "Sig1_Date", "Sig1_Month", "Sig1_Year", "Sig1_State" - these do NOT contain
# the substring "sign", so a word list alone silently misses them and the
# fields stay editable instead of staying ink.
_SIG_WORDS = ("sign", "notary", "affiant", "deponent", "witness",
              "sworn", "subscribed", "attesting", "commission", "officer")
# "assign" / "design" / "consign" contain the substring "sign" but are not
# signature fields. Without these the substring test wrongly locks them, so an
# exclusion list is required — a word-boundary match is not an option, because
# it would stop matching camelCase names like "DefendantSignature".
_SIG_EXCLUDE = ("print", "design", "assign", "consign", "date", "name", "county", "where_signed")
_SIG_NUMBERED_RE = re.compile(r"\bsig\s*[_\- ]?\d+\b")


def _is_signature_name(name: str) -> bool:
    """True if a PDF field name denotes a signature/notary line (must stay ink)."""
    n = (name or "").lower()
    if any(k in n for k in _SIG_EXCLUDE):
        return False
    return any(k in n for k in _SIG_WORDS) or bool(_SIG_NUMBERED_RE.search(n))


# Field names that denote a date. Used only to decide whether a date field is
# part of a signature block — never to decide whether a date is fillable.
_DATE_NAME_RE = re.compile(r"(?<![a-z])(date|dated|day|month|year)(?![a-z])",
                           re.IGNORECASE)


def _row_center(widget) -> float:
    """Vertical centre of a widget, for same-row (signature block) tests."""
    r = getattr(widget, "rect", None)
    return (r.y0 + r.y1) / 2 if r is not None else 0.0


# Fill characters that MAKE UP a blank are not "printed text" — an underscore
# run, a rule, or a dotted leader must not veto a candidate blank.
_DECOR_CHARS = set("_.-\u2010\u2011\u2012\u2013\u2014\u00b7 ")


def _is_decorative_word(word: str) -> bool:
    """True for underscore / dash / rule runs — a blank, not printed text."""
    return bool(word) and all(ch in _DECOR_CHARS for ch in word)


def _over_printed_text(words, rect, tol: float = 1.5) -> bool:
    """True if real printed text already occupies rect.

    A rule or underscore detected inside body prose is not an input blank.
    Stamping an editable field there puts a ghost field on top of the court's
    own printed text: it pollutes the tab order and lets the tenant type over
    the form. Measured on the AR answer form, 64% of auto-detected candidates
    were over printed prose.

    `words` is the page's ``get_text("words")`` list. Defined at module level
    and shared with the audit tooling on purpose, so the measurement uses the
    exact definition the fill path enforces — a metric that measures with a
    different ruler than the fix produces numbers that disagree with reality.
    """
    r = pymupdf.Rect(rect.x0 - tol, rect.y0 - tol, rect.x1 + tol, rect.y1 + tol)
    for wd in words:
        if _is_decorative_word(str(wd[4])):
            continue
        if r.intersects(pymupdf.Rect(wd[0], wd[1], wd[2], wd[3])):
            return True
    return False


def _make_signature_fields_readonly(doc: pymupdf.Document, config: Optional[dict] = None) -> int:
    """Blank + read-only any text field that is actually a signature/notary line.

    Signature, notary, affiant, witness, sworn/subscribed, commission, and bank
    officer lines must stay ink (the tenant or the relevant officer signs by hand).
    Native form PDFs sometimes ship these as text fields with placeholders like
    ``/s/`` — we clear them and lock them so they stay blank and non-editable.
    Printed-name and date fields are left editable on purpose.
    """
    readonly = getattr(pymupdf, "PDF_FIELD_IS_READ_ONLY", 1)
    # States that pre-fill digital "/s/" signature markers (e.g. IL) keep the
    # marker text but still lock the field read-only (so it can't be typed over).
    keep_marker = bool(config and config.get("populate_signature_fields"))
    locked = 0
    for page in doc:
        text_widgets = [cast(Any, w) for w in page.widgets()
                        if getattr(w, "field_type", None) == pymupdf.PDF_WIDGET_TYPE_TEXT]
        # Rows that already contain a signature/notary field. A DATE field sharing
        # such a row belongs to the same signature block. The Michigan fee waiver
        # is the live example: its `Date` sits directly under "I declare under the
        # penalties of perjury ..." on the same line as `Signature`. Pre-filling it
        # made the packet assert a sworn date that the tenant never signed — while
        # the Signature blank beside it stayed empty.
        sig_rows = [_row_center(w) for w in text_widgets
                    if _is_signature_name(getattr(w, "field_name", "") or "")]
        for w in text_widgets:
            name = getattr(w, "field_name", "") or ""
            is_sig = _is_signature_name(name)
            if not is_sig and _DATE_NAME_RE.search(name):
                cy = _row_center(w)
                if any(abs(cy - sy) < 12 for sy in sig_rows):
                    # States that pre-fill execution/mailing dates keep them
                    # populated; otherwise leave blank so the packet doesn't
                    # assert a sworn date the tenant never signed.
                    if not (config and config.get("populate_signature_dates")):
                        is_sig = True
            if not is_sig:
                continue
            if not keep_marker:
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


def _make_scanned_form_editable(doc: pymupdf.Document, data: dict) -> None:
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
        words = page.get_text("words")
        drawings = page.get_drawings()
        # PyMuPDF search_for/get_drawings/get_text all return top-down
        # coordinates, and widget rects are top-down too — no flipping needed.
        covered = [pymupdf.Rect(w.rect) for w in page.widgets() if w.rect is not None]

        def _covered(rect, tol=4):
            r = pymupdf.Rect(rect.x0 - tol, rect.y0 - tol, rect.x1 + tol, rect.y1 + tol)
            return any(r.intersects(e) for e in covered)

        # Fill characters that DO make up a blank are not "printed text" — an
        # underscore run, a rule, or a dotted leader must not veto the candidate.
        def _over_text(rect) -> bool:
            return _over_printed_text(words, rect)

        # 1. checkboxes drawn as "☐" (U+2610) or "❑" (U+2751) glyphs
        for i, r in enumerate(list(page.search_for("\u2610")) + list(page.search_for("\u2751"))):
            if r.height > r.width * 1.3:
                cy = (r.y0 + r.y1) / 2
                bsize = max(r.width, 10.0)
                rr = pymupdf.Rect(r.x0 - 0.5, cy - bsize / 2, r.x0 - 0.5 + bsize, cy + bsize / 2)
            else:
                rr = pymupdf.Rect(r.x0 - 1, r.y0 - 2, r.x1 + 1, r.y1 + 1)
            if _covered(rr):
                continue
            lb = _label_to_right(words, rr.x1, rr.y0, rr.y1)
            m = _match_label_field(lb)
            _add_checkbox_widget(page, rr, f"cb_{pno}_{i}", m is not None and m[2] and _resolve_field_value(m[0], m[1], data) == "Yes")
            covered.append(rr)

        # 2. checkboxes drawn as small vector squares
        for i, dr in enumerate(drawings):
            r = dr["rect"]
            if 5 <= r.width <= 20 and 5 <= r.height <= 20 and abs(r.width - r.height) <= 5:
                if _covered(r):
                    continue
                lb = _label_to_right(words, r.x1, r.y0, r.y1)
                m = _match_label_field(lb)
                _add_checkbox_widget(page, r, f"vcb_{pno}_{i}", m is not None and m[2] and _resolve_field_value(m[0], m[1], data) == "Yes")
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
            r = pymupdf.Rect(x0, y0 - 6, max(x1, x0 + 48), y1 + 4)
            if _covered(r) or _is_signature_line(page, r) or _over_text(r):
                continue
            _add_text_widget(page, r, f"ufill_{pno}_{i}", "")
            covered.append(r)

        # 4. horizontal lines -> text fields
        for i, dr in enumerate([d for d in drawings if d["rect"].height < 3 and d["rect"].width > 15]):
            raw_r = dr["rect"]
            r = pymupdf.Rect(raw_r.x0, raw_r.y0 - 12, raw_r.x1, raw_r.y0 + 4)
            if _covered(r, tol=1) or _is_signature_line(page, raw_r) or _over_text(r):
                continue
            _add_text_widget(page, r, f"fill_{pno}_{i}", "")
            covered.append(r)

        # 5. rectangle boxes -> text fields
        for i, dr in enumerate([d for d in drawings if d["rect"].width > 40 and 3 <= d["rect"].height <= 30]):
            r = dr["rect"]
            # Skip whiteout/mask rectangles (pure white fill and white/no stroke)
            if dr.get("fill") in ((1.0, 1.0, 1.0), (1, 1, 1)) and dr.get("color") in (None, (1.0, 1.0, 1.0), (1, 1, 1)):
                continue
            if _covered(r) or _over_text(r):
                continue
            _add_text_widget(page, r, f"bfill_{pno}_{i}", "")
            covered.append(r)


def _add_text_widget(page, rect, name: str, value: str, font_size: float = 10, fill_color: Optional[tuple] = None, align: Optional[str] = None) -> None:
    """Add a pre-filled, editable text field at the given rect."""
    if rect.x1 <= rect.x0 or rect.y1 <= rect.y0:
        return
    if rect.height < 4:
        rect = pymupdf.Rect(rect.x0, rect.y0 - 12, rect.x1, rect.y0 + 4)
    w = cast(Any, pymupdf.Widget())
    w.field_name = name
    w.field_type = pymupdf.PDF_WIDGET_TYPE_TEXT  # type: ignore[attr-defined]
    w.rect = rect
    w.field_value = str(value)
    if rect.height > 25 or any(k in name for k in ("narrative", "summary")):
        w.field_flags = pymupdf.PDF_TX_FIELD_IS_MULTILINE  # type: ignore[attr-defined]
    else:
        w.field_flags = 0
    w.text_fontsize = font_size
    # If a specific fill_color is provided (e.g. (1, 1, 1) for large narrative blocks),
    # apply it. Single-line fields leave fill_color as None (transparent) so
    # pre-printed underlines remain continuous without being chopped into dashes.
    if fill_color is not None:
        w.fill_color = fill_color
    w.border_width = 0
    new_w = page.add_widget(w)
    if align and new_w and getattr(new_w, "xref", None):
        try:
            if align == "center":
                page.parent.xref_set_key(new_w.xref, "Q", "1")
                new_w.update()
            elif align == "right":
                page.parent.xref_set_key(new_w.xref, "Q", "2")
                new_w.update()
        except Exception:
            pass


def _add_checkbox_widget(page, rect, name: str, checked: bool = True) -> None:
    """Add an editable checkbox at the given rect."""
    if rect.x1 <= rect.x0 or rect.y1 <= rect.y0:
        return
    w = cast(Any, pymupdf.Widget())
    w.field_name = name
    w.field_type = pymupdf.PDF_WIDGET_TYPE_CHECKBOX  # type: ignore[attr-defined]
    w.rect = rect
    w.field_value = bool(checked)
    page.add_widget(w)


def _fill_via_overlay(doc: pymupdf.Document, data: dict, config: dict, form_key: str = "answer_form"):
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
                _pr = pymupdf.Rect(x, y, x + w, y + h)
                if any(_pr.intersects(r) for r in existing_rects):
                    continue  # already filled via a fillable widget (rebuilt form)
                value = _get_field_value(key, data)
                # Check if this is a defense checkbox (small overlay rect)
                is_checkbox = (key.startswith("def_") or key.startswith("checkbox_")) and pos.get("h", 20) <= 20
                if is_checkbox:
                    s = pos.get("h", 14)
                    _add_checkbox_widget(page, pymupdf.Rect(x, y, x + s, y + s), key, checked=bool(value))
                elif value:
                    if (config.get("strip_dollar_signs") or pos.get("strip_dollar")) and isinstance(value, str) and value.startswith("$"):
                        value = value[1:]
                    is_narrative = (
                        pos.get("h", 20) > 30
                        or any(k in key for k in ("narrative", "summary", "explanation"))
                    )
                    field_fill = pos["fill_color"] if "fill_color" in pos else ((1, 1, 1) if is_narrative else None)
                    _add_text_widget(page, _pr, key, str(value), font_size=pos.get("size", 10), fill_color=field_fill, align=pos.get("align"))




def _get_field_value(key: str, data: dict) -> Optional[str]:
    """Get a value from the nested data dict by key path.
    
    Handles regular data fields, defense checkbox overlay keys, and narrative text.
    When key starts with 'def_', returns 'X' if the defense is checked (triggers checkmark).
    When key is 'defense_narrative', returns formatted defense explanation text.
    """
    # Strip leading dollar signs for forms with pre-printed dollar signs
    if key.endswith("_raw"):
        base_k = key[:-4]
        raw_val = _get_field_value(base_k, data)
        if raw_val is not None:
            return str(raw_val).lstrip("$").strip()
        return "0.00"

    # Allow page-suffixed overlay keys (e.g. case_number_page3) to resolve to the
    # base field name so one field can be overlaid on multiple pages of a form.
    key = re.sub(r'_(?:p|page)\d+$', '', key)
    p = data.get("personal_info", {})
    l = data.get("landlord_info", {})
    c = data.get("case_details", {})
    defenses = data.get("defenses", {})
    fin = data.get("financial_info", {}) or data.get("financial", {}) or {}
    
    mapper = {
        "full_name": p.get("full_name"),
        "full_name_caption": p.get("full_name"),
        "full_name_sworn": p.get("full_name"),
        "my_name": p.get("full_name"),
        "date_of_birth": p.get("date_of_birth"),
        "defendant_name": p.get("full_name"),
        "defendant_appearance": p.get("full_name"),
        "printed_name": p.get("full_name"),
        "your_name": p.get("full_name"),
        "your_name_goes_here": p.get("full_name"),
        "applicant_name": p.get("full_name"),
        "head_of_household": p.get("full_name"),
        "phone": p.get("phone"),
        "phone_bottom": p.get("phone"),
        "email": p.get("email"),
        "address": p.get("property_address"),
        "property_address": p.get("property_address"),
        "full_address": _compose_full_address(p, data.get("state", "")),
        "city": p.get("property_city"),
        "zip": p.get("property_zip"),
        "city_state_zip": f"{p.get('property_city', '')}, {data.get('state', '')} {p.get('property_zip', '')}".strip(", "),
        "party_info": "\n".join(x for x in (
            p.get("full_name", ""),
            f"{p.get('property_address', '')}, {p.get('property_city', '')}, {data.get('state', '')} {p.get('property_zip', '')}".strip(", ")
        ) if x),
        "county": p.get("county"),
        "county_state_signed": f"{p.get('county', '')} County, {data.get('state', '')}".strip(", "),
        "county_and_state": f"{p.get('county', '')} County, {data.get('state', '')}".strip(", "),
        "county_where_signed": f"{p.get('county', '')} County, {data.get('state', '')}".strip(", "),
        "venue_state": "New Mexico",
        "venue_county": f"{p.get('county', '')} County".strip(),
        "public_assistance_county": p.get("county"),
        "court_type": (
            "Metropolitan Court"
            if (p.get("county") or "").strip().lower() == "bernalillo" or "metropolitan" in str(c.get("court_name", "")).lower()
            else (c.get("court_type") or "Magistrate Court")
        ),
        "judicial_district": c.get("judicial_district") or ("4th" if (p.get("county") or "").lower() == "hennepin" else ""),
        "case_type": c.get("case_type", ""),
        "landlord_name": l.get("landlord_name"),
        "plaintiff_name": l.get("landlord_name"),
        "landlord_address": l.get("landlord_address"),
        "bank_accounts": (
            _money((_to_float(fin.get("checking_balance")) or 0.0) + (_to_float(fin.get("savings_balance")) or 0.0), 2)
            if (fin.get("checking_balance") is not None or fin.get("savings_balance") is not None or fin.get("bank_balance") is not None)
            else "$0.00"
        ),
        "income_tax_refund": "$0.00",
        "vehicle_desc": fin.get("vehicle_make_model") or ("Vehicle" if fin.get("vehicle_value") else None),
        "telephone_expense": _money(fin.get("telephone_expense") or 50.0, 2),
        "auto_loan_expense": _money(fin.get("vehicle_loan_owed") or 0.0, 2) if fin.get("vehicle_loan_owed") else "$0.00",
        "gasoline_expense": _money(fin.get("transportation_expense") or 0.0, 2) if fin.get("transportation_expense") else "$0.00",
        "insurance_expense": "$0.00",
        "debt_expense": _money(fin.get("debt_payments") or 0.0, 2) if fin.get("debt_payments") else "$0.00",
        "court_support_expense": "$0.00",
        "court_order_expense": "$0.00",
        "fw_employer_name": fin.get("employer_name") or fin.get("employer") or ("Employed" if fin.get("is_employed") else None),
        "fw_employer_address": fin.get("employer_address") or "",
        "landlord_phone": l.get("landlord_phone"),
        "landlord_email": l.get("landlord_email"),
        "case_number": c.get("case_number"),
        "date": date.today().strftime("%m/%d/%Y"),
        "court_name": c.get("court_name"),
        "monthly_rent": str(c.get("monthly_rent", "")),
        "amount_demanded": str(c.get("notice_amount_demanded", "")),
        "complaint_amount_claimed": (
            f"{_to_float(c.get('complaint_amount_claimed') or c.get('notice_amount_demanded') or 0.0):,.2f}"
            if _to_float(c.get('complaint_amount_claimed') or c.get('notice_amount_demanded') or 0.0) > 0 else ""
        ),
        "amount_claimed": (
            f"{_to_float(c.get('complaint_amount_claimed') or c.get('notice_amount_demanded') or 0.0):,.2f}"
            if _to_float(c.get('complaint_amount_claimed') or c.get('notice_amount_demanded') or 0.0) > 0 else ""
        ),
        "cos_date": date.today().strftime("%m/%d/%Y"),
        "cos_recipient": (
            f"{(l.get('landlord_attorney_name') or '').strip()} (attorney for {l.get('landlord_name', '')})"
            if (l.get('landlord_attorney_name') or '').strip()
            else l.get("landlord_name")
        ),
        "cos_address": (
            (l.get('landlord_attorney_address') or '').strip()
            if (l.get('landlord_attorney_name') or '').strip() and (l.get('landlord_attorney_address') or '').strip()
            else l.get("landlord_address")
        ),
        "cos_served_to": ", ".join(filter(None, [
            (f"{(l.get('landlord_attorney_name') or '').strip()} (attorney for {l.get('landlord_name', '')})"
             if (l.get('landlord_attorney_name') or '').strip()
             else l.get("landlord_name")),
            ((l.get('landlord_attorney_address') or '').strip()
             if (l.get('landlord_attorney_name') or '').strip() and (l.get('landlord_attorney_address') or '').strip()
             else l.get("landlord_address"))
        ])),
    }
    
    # Handle defense narrative text generation
    if key == "defense_narrative":
        return _build_defense_narrative(defenses)

    # Tenant's responses to the complaint allegations (Item 1 on AR answer).
    if key in ("response_narrative", "response_line_1", "response_line_2"):
        if key == "response_line_1":
            return ("Defendant denies each and every allegation contained in the "
                    "Complaint except as expressly")
        if key == "response_line_2":
            return "admitted herein, and demands strict proof thereof."
        return ("Defendant denies each and every allegation contained in the "
                "Complaint except as expressly admitted herein, and demands "
                "strict proof thereof.")

    # Tenant's counterclaims against the landlord (Item 5 on AR answer).
    if key in ("counterclaim_narrative", "counterclaim_line1", "counterclaim_line2"):
        _dr = defenses.get("def_repairs", {})
        has_repairs = isinstance(_dr, dict) and _dr.get("checked")
        if key == "counterclaim_line1":
            return "Breach of warranty of habitability;" if has_repairs else "Defendant reserves all rights"
        if key == "counterclaim_line2":
            return "cost of necessary repairs to premises." if has_repairs else "to assert counterclaims."
        if has_repairs:
            return ("Defendant asserts a counterclaim against Plaintiff for breach "
                    "of the warranty of habitability and for the cost of necessary "
                    "repairs to the premises.")
        return "Defendant reserves the right to assert counterclaims against Plaintiff."
    
    # Handle numbered defense narrative lines (NM 4-907 style)
    if key.startswith("defense_narrative_"):
        if key in ("defense_narrative_1", "defense_narrative_1a", "defense_narrative_1b"):
            vacate_defenses = [
                ("def_repairs", "Conditions: "),
                ("def_bad_notice", "Defective notice: "),
                ("def_retaliation", "Retaliation: "),
                ("def_waived", "Waiver: "),
                ("def_accepted_rent", "Accepted rent: "),
                ("def_corrected", "Cured: "),
                ("def_fair_housing", "Discrimination: "),
                ("def_not_owner", "Improper plaintiff: "),
                ("def_other", "Other: "),
            ]
            parts = []
            for dk, lbl in vacate_defenses:
                d = defenses.get(dk, {})
                if isinstance(d, dict) and d.get("checked"):
                    expl = d.get("explanation", "").strip()
                    parts.append(f"{lbl}{expl}" if expl else lbl.rstrip(": "))
            full_vacate = "; ".join(parts) if parts else "Defendant denies landlord's entitlement to possession."
            words = full_vacate.split()
            wlines = []
            curr = []
            for wd in words:
                trial = " ".join(curr + [wd])
                if pymupdf.get_text_length(trial, fontname="helv", fontsize=8.5) <= 390:
                    curr.append(wd)
                else:
                    wlines.append(" ".join(curr))
                    curr = [wd]
            if curr:
                wlines.append(" ".join(curr))
            if len(wlines) > 2:
                wlines[1] = wlines[1].rsplit(' ', 1)[0] + '...'
            if key == "defense_narrative_1b":
                return wlines[1] if len(wlines) > 1 else None
            return wlines[0] if wlines else full_vacate[:90]

        if key == "defense_narrative_2":
            rent_defenses = [
                ("def_amount", "Amount disputed: "),
                ("def_paid", "Already paid: "),
                ("def_attempted_pay", "Tendered payment: "),
            ]
            parts = []
            for dk, lbl in rent_defenses:
                d = defenses.get(dk, {})
                if isinstance(d, dict) and d.get("checked"):
                    expl = d.get("explanation", "").strip()
                    parts.append(f"{lbl}{expl}" if expl else lbl.rstrip(": "))
            if not parts and defenses.get("def_repairs", {}).get("checked"):
                parts.append("Rent abatement for breach of warranty of habitability under NMSA 1978 § 47-8-27.2.")
            if not parts:
                parts.append("Defendant disputes the amount of rent claimed by Plaintiff.")
            full_rent = "; ".join(parts)
            return full_rent if pymupdf.get_text_length(full_rent, fontname="helv", fontsize=8.5) <= 390 else full_rent[:85] + "..."

        if key == "defense_narrative_3":
            d_damages = defenses.get("def_damages", {})
            if isinstance(d_damages, dict) and d_damages.get("checked") and d_damages.get("explanation"):
                return d_damages.get("explanation", "")[:90]
            return "Defendant did not cause damage beyond normal wear and tear; plaintiff claims are unsubstantiated."

        if key == "defense_narrative_4":
            has_repairs = isinstance(defenses.get("def_repairs"), dict) and defenses.get("def_repairs", {}).get("checked")
            if has_repairs:
                return "Setoff and rent abatement for failure to maintain premises in habitable condition (NMSA § 47-8-27.1)."
            return "Defendant reserves all rights to assert counterclaims and setoffs against Plaintiff."

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
            return active[idx]
        return None

    # Handle individual ruled defense lines (AR style)
    if key.startswith("defense_line_"):
        try:
            idx = int(key.split("_")[-1]) - 1  # defense_line_1 → index 0
        except (ValueError, IndexError):
            idx = 0
        dlines = _build_defense_lines(defenses, max_lines=5, max_width=460.0, font_size=8.0)
        if idx < len(dlines):
            return dlines[idx]
        return None
    
    # Handle financial summary for overlay fee waiver forms
    if key == "financial_summary":
        return _build_financial_summary(data.get("financial_info", {}))
    
    # Handle procedural checkbox overlay keys (hearing mode, trial mode, etc.)
    if key.startswith("checkbox_"):
        pref = data.get("preferences", {}) or {}
        h_mode = str(pref.get("hearing_mode") or pref.get("hearing_format") or "in person").lower()
        is_remote = "remote" in h_mode
        is_in_person = not is_remote

        cos_method = str(
            pref.get("certificate_of_service_method")
            or c.get("certificate_of_service_method")
            or "regular_mail"
        ).lower()
        is_cos_efile = "efile" in cos_method or "online" in cos_method or "electronic" in cos_method
        is_cos_hand = "hand" in cos_method or "delivery" in cos_method or (
            "other" in cos_method and "hand" in str(pref.get("certificate_of_service_other", "")).lower()
        )
        is_cos_mail = not is_cos_efile and not is_cos_hand

        has_benefits = bool(
            fin.get("receives_public_benefits")
            or fin.get("receives_snap")
            or fin.get("receives_medicaid")
            or fin.get("receives_ssi")
            or fin.get("receives_tanf")
            or fin.get("receives_county_assistance")
            or fin.get("receives_public_housing")
            or fin.get("receives_section8")
        )
        is_single = (fin.get("marital_status") or "").lower() == "single" or int(fin.get("household_adults") or 1) <= 1
        is_married = (fin.get("marital_status") or "").lower() == "married" or int(fin.get("household_adults") or 1) > 1
        is_employed = fin.get("is_employed") is True or bool(fin.get("self_employment_income")) or _to_float(fin.get("employment_income")) > 0

        _cb_map = {
            "checkbox_trial_to_court": "X" if pref.get("trial_by") == "judge" else None,
            "checkbox_trial_jury": "X" if pref.get("trial_by") == "jury" else None,
            "checkbox_hearing_in_person": "X" if is_in_person else None,
            "checkbox_hearing_remote": "X" if is_remote else None,
            "checkbox_cos_hand": "X" if is_cos_hand else None,
            "checkbox_cos_efile": "X" if is_cos_efile else None,
            "checkbox_cos_mail": "X" if is_cos_mail else None,
            "checkbox_military_not": "X" if not p.get("is_active_military") else None,
            "checkbox_not_military": "X" if not p.get("is_active_military") else None,
            "checkbox_stay_7_days": "X" if (pref.get("needs_more_time") or pref.get("hardship_reason") or True) else None,
            "checkbox_marital_single": "X" if is_single else None,
            "checkbox_marital_married": "X" if is_married else None,
            "checkbox_marital_divorced": "X" if (fin.get("marital_status") or "").lower() == "divorced" else None,
            "checkbox_marital_separated": "X" if (fin.get("marital_status") or "").lower() == "separated" else None,
            "checkbox_interpretation_no": "X",
            "checkbox_no_assistance": "X" if not has_benefits else None,
            "checkbox_receives_assistance": "X" if has_benefits else None,
            "checkbox_tanf": "X" if fin.get("receives_tanf") else None,
            "checkbox_snap": "X" if fin.get("receives_snap") else None,
            "checkbox_medicaid": "X" if fin.get("receives_medicaid") else None,
            "checkbox_ga": "X" if (fin.get("receives_county_assistance") or fin.get("receives_ga")) else None,
            "checkbox_ssi": "X" if fin.get("receives_ssi") else None,
            "checkbox_public_housing": "X" if (fin.get("receives_public_housing") or fin.get("receives_section8")) else None,
            "checkbox_unemployed": "X" if not is_employed else None,
            "checkbox_unemployed_no_income": "X" if not is_employed and _to_float(fin.get("employment_income")) <= 0 else None,
            "checkbox_employed": "X" if is_employed else None,
            "checkbox_no_other_income": "X" if not fin.get("other_income") else None,
            "checkbox_spouse_no_other_income": "X" if is_married else None,
            "checkbox_role_respondent": "X",
        }
        return _cb_map.get(key)

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
    
    # Defense explanation text for checkbox forms (e.g. MN HOU202) where the form has
    # specific defense's explanation at a specific overlay position.
    if key.startswith("explanation_"):
        suffix_match = re.search(r'_(\d+)$', key)
        line_idx = None
        if suffix_match:
            try:
                line_idx = int(suffix_match.group(1)) - 1
            except ValueError:
                line_idx = None
        base_key = key[:suffix_match.start()] if suffix_match else key
        _dk = base_key[len("explanation_"):]
        _d = defenses.get(_dk, {})
        if isinstance(_d, dict) and _d.get("checked"):
            raw_text = _d.get("explanation", "").strip()
            if line_idx is not None:
                words = raw_text.split()
                wlines = []
                curr = []
                for wd in words:
                    trial = " ".join(curr + [wd])
                    if pymupdf.get_text_length(trial, fontname="helv", fontsize=8.5) <= 435:
                        curr.append(wd)
                    else:
                        wlines.append(" ".join(curr))
                        curr = [wd]
                if curr:
                    wlines.append(" ".join(curr))
                return wlines[line_idx] if line_idx < len(wlines) else None
            return raw_text
        return None

    # Handle statutory 7-day stay hardship reason lines (MN HOU202 Item 11)
    if key.startswith("hardship_reason_line"):
        suffix_match = re.search(r'(\d+)$', key)
        line_idx = int(suffix_match.group(1)) - 1 if suffix_match else 0
        pref = data.get("preferences", {}) or {}
        raw_text = pref.get("hardship_reason", "").strip()
        if not raw_text and pref.get("needs_more_time"):
            raw_text = "Vacating immediately would cause severe substantial hardship to my household."
        if raw_text:
            words = raw_text.split()
            wlines = []
            curr = []
            for wd in words:
                trial = " ".join(curr + [wd])
                if pymupdf.get_text_length(trial, fontname="helv", fontsize=8.5) <= 435:
                    curr.append(wd)
                else:
                    wlines.append(" ".join(curr))
                    curr = [wd]
            if curr:
                wlines.append(" ".join(curr))
            return wlines[line_idx] if line_idx < len(wlines) else None
        return None

    # Arkansas & fee waiver question detail overlays
    if key == "fw_employment_details":
        fin = data.get("financial_info", {}) or {}
        is_emp = fin.get("is_employed")
        self_emp = bool(fin.get("self_employment_income"))
        emp_name = fin.get("employer_name")
        emp_addr = fin.get("employer_address")
        wages = fin.get("employment_income") or fin.get("self_employment_income")
        if wages is None and is_emp is True:
            wages = fin.get("monthly_net_income") or fin.get("monthly_gross_income")

        # If explicitly not employed or zero employment wages with no employer
        if is_emp is False and not self_emp and not emp_name:
            return None
        if not is_emp and not self_emp and not emp_name and (_to_float(wages) <= 0):
            return None

        if is_emp is True or self_emp or emp_name or (_to_float(wages) > 0):
            parts = []
            if emp_name:
                if self_emp and "self" not in emp_name.lower():
                    parts.append(f"{emp_name} (Self-Employed)")
                else:
                    parts.append(emp_name)
            elif self_emp:
                parts.append("Self-Employed")
            if emp_addr:
                parts.append(emp_addr)
            if _to_float(wages) > 0:
                parts.append(f"({_money(wages, 2)}/mo)")
            return " - ".join(parts) if parts else "Employed"
        return None

    if key == "fw_last_employment_details":
        fin = data.get("financial_info", {}) or {}
        is_emp = fin.get("is_employed")
        self_emp = bool(fin.get("self_employment_income"))
        # If employed or self-employed, Question 1(a) applies and 1(b) must stay blank
        if is_emp is True or self_emp:
            return None
        last_date = fin.get("last_employment_date")
        last_wage = fin.get("last_employment_wage")
        wages = fin.get("employment_income")
        if is_emp is False or (wages is not None and float(wages) == 0) or last_date:
            parts = []
            if last_date:
                parts.append(f"Last employed: {last_date}")
            if last_wage:
                wage_str = _money(last_wage, 2) if str(last_wage).replace('.', '', 1).isdigit() else str(last_wage)
                parts.append(f"Prior wage: {wage_str}/mo")
            return ", ".join(parts) if parts else "Currently unemployed - $0.00 employment income"
        return None

    if key == "fw_income_sources_details":
        fin = data.get("financial_info", {}) or {}
        sources = []
        def _pos(v):
            try:
                return float(v) if v is not None else 0.0
            except (ValueError, TypeError):
                return 0.0

        if _pos(fin.get("unemployment_income")) > 0:
            sources.append(f"Unemployment: {_money(fin['unemployment_income'], 2)}/mo")
        if _pos(fin.get("social_security_income")) > 0:
            sources.append(f"Social Security: {_money(fin['social_security_income'], 2)}/mo")
        if _pos(fin.get("ssi_income")) > 0:
            sources.append(f"SSI: {_money(fin['ssi_income'], 2)}/mo")
        if _pos(fin.get("pension_income")) > 0:
            sources.append(f"Pension: {_money(fin['pension_income'], 2)}/mo")
        if _pos(fin.get("alimony_income")) > 0:
            sources.append(f"Alimony: {_money(fin['alimony_income'], 2)}/mo")
        if _pos(fin.get("child_support_income")) > 0:
            sources.append(f"Child support: {_money(fin['child_support_income'], 2)}/mo")
        if _pos(fin.get("disability_income")) > 0:
            sources.append(f"Disability: {_money(fin['disability_income'], 2)}/mo")
        if _pos(fin.get("veterans_benefits")) > 0:
            sources.append(f"VA Benefits: {_money(fin['veterans_benefits'], 2)}/mo")
        if _pos(fin.get("self_employment_income")) > 0:
            sources.append(f"Self-employment: {_money(fin['self_employment_income'], 2)}/mo")
        if fin.get("receives_snap"):
            sources.append("SNAP benefits")
        if fin.get("receives_medicaid"):
            sources.append("Medicaid")
        if fin.get("receives_tanf"):
            sources.append("TANF")
        if _pos(fin.get("other_income")) > 0:
            desc = fin.get("other_income_description") or "Other"
            sources.append(f"{desc}: {_money(fin['other_income'], 2)}/mo")
        return "; ".join(sources) if sources else "None ($0.00)"

    if key == "fw_accounts_details":
        fin = data.get("financial_info", {}) or {}
        accts = []
        chk = fin.get("checking_balance")
        sav = fin.get("savings_balance")
        cash = fin.get("cash_on_hand")
        bank_total = (_to_float(chk) or 0.0) + (_to_float(sav) or 0.0) if (chk is not None or sav is not None) else None
        if bank_total is not None:
            accts.append(f"Bank account(s): {_money(bank_total, 2)}")
        if cash is not None:
            accts.append(f"Cash on hand: {_money(cash, 2)}")
        return "; ".join(accts) if accts else "None ($0.00)"

    if key == "fw_property_details":
        fin = data.get("financial_info", {}) or {}
        props = []
        veh = fin.get("vehicle_make_model")
        vval = fin.get("vehicle_value")
        if veh:
            props.append(f"Vehicle: {veh}" + (f" ({_money(vval, 0)})" if vval is not None else ""))
        if fin.get("owns_real_estate"):
            reval = fin.get("real_estate_value")
            props.append("Real estate" + (f" ({_money(reval, 0)})" if reval is not None else ""))
        oth = fin.get("other_assets_description")
        if oth:
            oval = fin.get("other_assets_value")
            props.append(f"{oth}" + (f" ({_money(oval, 0)})" if oval is not None else ""))
        return "; ".join(props) if props else "None"

    if key == "fw_dependents_details":
        fin = data.get("financial_info", {}) or {}
        dep_detail = fin.get("dependents_detail")
        if dep_detail:
            return dep_detail
        ch = fin.get("household_children") or 0
        ad = (fin.get("household_adults") or 1) - 1
        tot = fin.get("total_dependents") or (ch + max(0, ad))
        if tot > 0:
            return f"{tot} dependent(s) ({ch} child(ren), {max(0, ad)} adult(s))"
        return "None"

    # Check financial fields directly if present
    fin_val = _get_financial_value(key, data)
    if fin_val is not None:
        return fin_val

    return mapper.get(key)


def _get_financial_value(key: str, data: dict) -> Optional[str]:
    """Get a value from the FinancialInfo section for fee waiver forms.
    
    Returns formatted string for text fields, or "Yes" for boolean checkboxes.
    """
    financial = data.get("financial_info", {}) or data.get("financial", {})
    if not financial:
        return None
    
    # Boolean checkbox fields
    bool_fields = ["receives_public_benefits", "receives_snap", "receives_ssi", "receives_medicaid",
                   "receives_tanf", "receives_blind_aid", "receives_oap", "receives_and",
                   "receives_section8", "receives_public_housing",
                   "receives_county_assistance", "receives_energy_assistance",
                   "receives_veterans_benefits", "receives_child_care_assistance",
                   "income_below_threshold", "unable_to_pay_fees", "owns_real_estate",
                   "has_requested_fee_waiver_before"]
    if key in bool_fields:
        val = financial.get(key, False)
        if key == "receives_public_benefits" and not val:
            val = bool(financial.get("receives_snap") or financial.get("receives_medicaid") or financial.get("receives_ssi") or financial.get("receives_tanf"))
        return "Yes" if val else None
    
    # Numeric fields — format as dollar amounts
    dollar_fields = ["monthly_gross_income", "monthly_net_income", "total_monthly_income", "employment_income",
                     "self_employment_income", "social_security_income", "ssi_income",
                     "unemployment_income", "pension_income", "disability_income",
                     "veterans_benefits", "child_support_income", "alimony_income",
                     "other_income", "rent_or_mortgage", "utilities_expense",
                     "food_expense", "transportation_expense", "medical_expense",
                     "child_care_expense", "debt_payments", "other_expenses",
                     "telephone_expense",
                     "total_monthly_expenses", "total_expenses_table", "cash_on_hand",
                     "checking_balance", "savings_balance", "vehicle_value",
                     "vehicle_loan_owed", "real_estate_value", "real_estate_loan_owed",
                     "other_assets_value", "total_assets", "total_debts", "credit_card_balance"]
    if key in dollar_fields:
        val = financial.get(key)
        # Fallback: employment_income from monthly_gross_income
        if val is None and key == "employment_income":
            val = financial.get("monthly_gross_income")
        if val is None and key == "monthly_net_income":
            val = financial.get("monthly_gross_income")
        if val is None and key == "total_monthly_income":
            val = financial.get("monthly_gross_income")
        # Fallback: total_expenses_table is an alias for total_monthly_expenses
        if val is None and key == "total_expenses_table":
            val = financial.get("total_monthly_expenses")
        # Fallback: total_monthly_expenses calculated from itemized expenses if missing
        if val is None and key in ("total_monthly_expenses", "total_expenses_table"):
            _exp_sum = sum(_to_float(financial.get(k)) for k in (
                "rent_or_mortgage", "utilities_expense", "food_expense",
                "transportation_expense", "medical_expense", "child_care_expense",
                "debt_payments", "other_expenses", "telephone_expense"
            ))
            if _exp_sum > 0:
                val = _exp_sum
        if val is None and key == "total_assets":
            _assets_sum = sum(_to_float(financial.get(k)) for k in (
                "cash_on_hand", "checking_balance", "savings_balance",
                "vehicle_value", "real_estate_value", "other_assets_value"
            ))
            if _assets_sum > 0 or any(financial.get(k) is not None for k in ("cash_on_hand", "checking_balance", "savings_balance")):
                val = _assets_sum
        if val is None and key == "total_debts":
            _debts_sum = sum(_to_float(financial.get(k)) for k in (
                "home_loan_balance", "real_estate_loan_owed", "vehicle_loan_owed",
                "credit_card_balance", "debt_payments", "other_debts"
            ))
            if _debts_sum > 0 or any(financial.get(k) is not None for k in ("debt_payments", "credit_card_balance", "vehicle_loan_owed")):
                val = _debts_sum
        if val is None and key == "credit_card_balance":
            val = financial.get("debt_payments")
        # Fallback: combined bank_balance into checking / savings
        if val is None and key == "checking_balance":
            if financial.get("bank_balance") is not None:
                val = financial.get("bank_balance")
        if val is None and key == "savings_balance":
            if financial.get("bank_balance") is not None:
                val = 0.0
        if val is not None:
            return f"{_money(val, 2)}"
        return None
    
    # Text fields
    text_fields = ["vehicle_make_model", "other_income_description", "other_assets_description",
                   "previous_fee_waiver_case", "last_paycheck_date", "pay_rate", "pay_frequency", "marital_status",
                   "household_members"]
    if key in text_fields:
        val = financial.get(key)
        if val is None and key == "household_members":
            raw_m = financial.get("household_members") or financial.get("dependents_detail")
            if isinstance(raw_m, list):
                items = []
                for item in raw_m:
                    if isinstance(item, dict):
                        n = item.get("name") or "Dependent"
                        rel = item.get("relationship", "")
                        items.append(f"{n} ({rel})" if rel else n)
                    else:
                        items.append(str(item))
                val = ", ".join(items) if items else None
            elif isinstance(raw_m, str) and raw_m.strip():
                val = raw_m.strip()
            elif int(financial.get("household_children") or 0) > 0:
                _num_c = int(financial.get("household_children"))
                val = f"{_num_c} dependent child" if _num_c == 1 else f"{_num_c} dependent children"
        if val is None and key == "marital_status":
            _ad = int(financial.get("household_adults") or 1)
            val = "Single" if _ad <= 1 else "Married"
        if val is None and key == "pay_rate":
            val = financial.get("hourly_rate_or_salary") or financial.get("employment_income") or financial.get("monthly_gross_income")
            if val is not None:
                val = f"{_to_float(val):.2f}"
        if val is None and key == "last_paycheck_date":
            val = financial.get("last_employment_date")
        if val is None and key == "pay_frequency":
            val = financial.get("pay_period") or "Monthly"
        if key == "last_paycheck_date" and val:
            val_str = str(val).strip()
            if re.match(r'^\d{4}-\d{2}-\d{2}$', val_str):
                parts = val_str.split('-')
                val = f"{parts[1]}/{parts[2]}/{parts[0]}"
        return str(val) if val else None
    
    # Household numbers
    if key == "household_size":
        try:
            _total = int(financial.get("household_adults") or 0) + int(financial.get("household_children") or 0)
        except (TypeError, ValueError):
            _total = 0
        if _total <= 0:
            _total = 1
        return str(_total)
    if key in ["household_adults", "household_children", "total_dependents"]:
        val = financial.get(key)
        if key == "total_dependents" and val is None:
            ch = int(financial.get("household_children") or 0)
            ad = max(0, int(financial.get("household_adults") or 1) - 1)
            val = ch + ad
        return str(val) if val is not None else None
    
    # Computed summary fields
    if key == "assets_description":
        parts = []
        vehicle = financial.get("vehicle_make_model")
        vehicle_val = financial.get("vehicle_value")
        if vehicle:
            parts.append(f"Vehicle: {vehicle}" + (f" ({_money(vehicle_val, 0)})" if vehicle_val else ""))
        checking = financial.get("checking_balance")
        savings = financial.get("savings_balance")
        bank_total = (_to_float(checking) or 0.0) + (_to_float(savings) or 0.0) if (checking is not None or savings is not None) else None
        if bank_total:
            parts.append(f"Bank account(s): {_money(bank_total, 2)}")
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

    # Equity/total fields for CT JD-CV-120 and similar forms whose totals are
    # normally computed by Acrobat client-side JavaScript that PyMuPDF never runs.
    if key == "total_monthly_income":
        net_inc = _to_float(financial.get("monthly_net_income") or financial.get("monthly_gross_income"))
        other_inc = _to_float(financial.get("other_income"))
        return f"${net_inc + other_inc:,.2f}"
    if key == "equity_real_estate":
        val = _to_float(financial.get("real_estate_value")) - _to_float(financial.get("real_estate_loan_owed"))
        return f"${max(0.0, val):,.2f}"
    if key == "equity_vehicle":
        val = _to_float(financial.get("vehicle_value")) - _to_float(financial.get("vehicle_loan_owed"))
        return f"${max(0.0, val):,.2f}"
    if key == "equity_other_property":
        val = _to_float(financial.get("other_assets_value"))
        return f"${max(0.0, val):,.2f}"
    if key == "total_assets_equity":
        re_eq = max(0.0, _to_float(financial.get("real_estate_value")) - _to_float(financial.get("real_estate_loan_owed")))
        mv_eq = max(0.0, _to_float(financial.get("vehicle_value")) - _to_float(financial.get("vehicle_loan_owed")))
        opp_eq = max(0.0, _to_float(financial.get("other_assets_value")))
        total = (_to_float(financial.get("cash_on_hand")) + _to_float(financial.get("checking_balance"))
                 + _to_float(financial.get("savings_balance")) + re_eq + mv_eq + opp_eq)
        return f"${total:,.2f}"
    if key == "total_debt_owed":
        if financial.get("debt_owed") is not None:
            return f"${_to_float(financial.get('debt_owed')):,.2f}"
        total = _to_float(financial.get("real_estate_loan_owed")) + _to_float(financial.get("vehicle_loan_owed"))
        return f"${total:,.2f}"

    return None


def _build_financial_summary(financial: dict) -> str:
    """Build a formatted summary of financial data for overlay fee waiver forms."""
    if not financial:
        return ""
    
    lines = []
    
    # Income
    income = financial.get('monthly_gross_income')
    if income is not None:
        lines.append(f"Monthly Gross Income: {_money(income, 2)}")
    emp = financial.get('employment_income')
    if emp is not None:
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
    if rent is not None:
        lines.append(f"Rent/Mortgage: {_money(rent, 2)}")
    total_exp = financial.get('total_monthly_expenses')
    if total_exp is not None:
        lines.append(f"Total Monthly Expenses: {_money(total_exp, 2)}")
    
    # Assets
    cash_val = financial.get('cash_on_hand')
    if cash_val is not None:
        lines.append(f"Cash on Hand: {_money(cash_val, 2)}")
    checking = financial.get('checking_balance')
    if checking is not None:
        lines.append(f"Checking: {_money(checking, 2)}")
    savings = financial.get('savings_balance')
    if savings is not None:
        lines.append(f"Savings: {_money(savings, 2)}")
    vehicle = financial.get('vehicle_make_model')
    if vehicle:
        vehicle_val = financial.get('vehicle_value')
        lines.append(f"Vehicle: {vehicle} ({_money(vehicle_val, 2)})" if vehicle_val is not None else f"Vehicle: {vehicle}")
    
    return '\n'.join(lines)


def _build_defense_lines(defenses: dict, max_lines: int = 5, max_width: float = 460.0, font_size: float = 8.0) -> list[str]:
    """Build individual formatted lines of defenses to sit directly on ruled lines."""
    lines: list[str] = []

    # Check for free-form narrative (e.g. Denver or narrative answers)
    narrative_text = ""
    if isinstance(defenses, dict):
        for n_key in ("narrative", "story", "statement", "free_form", "free_text", "defense_narrative"):
            val = defenses.get(n_key)
            if isinstance(val, dict):
                exp = (val.get("explanation") or val.get("text") or "").strip()
                if exp:
                    narrative_text = exp
                    break
            elif isinstance(val, str) and val.strip():
                narrative_text = val.strip()
                break
        if not narrative_text and defenses.get("explanation") and isinstance(defenses["explanation"], str):
            narrative_text = defenses["explanation"].strip()

    if narrative_text:
        words = narrative_text.split()
        l_words = []
        for wd in words:
            trial = " ".join(l_words + [wd])
            if pymupdf.get_text_length(trial, fontname="helv", fontsize=font_size) <= max_width:
                l_words.append(wd)
            else:
                if l_words:
                    lines.append(" ".join(l_words))
                l_words = [wd]
                if len(lines) >= max_lines:
                    break
        if l_words and len(lines) < max_lines:
            lines.append(" ".join(l_words))

    DEFENSE_LABELS = [
        ("def_repairs", "Failure to repair: "),
        ("def_amount", "Disputed rent: "),
        ("def_bad_notice", "Defective notice: "),
        ("def_attempted_pay", "Attempted payment: "),
        ("def_paid", "Rent paid: "),
        ("def_waived", "Waiver: "),
        ("def_retaliation", "Retaliation: "),
        ("def_fair_housing", "Discrimination: "),
        ("def_accepted_rent", "Accepted rent: "),
        ("def_corrected", "Corrected issue: "),
        ("def_not_owner", "Not proper owner: "),
        ("def_other", "Other: "),
    ]
    item_num = 1
    for k, label in DEFENSE_LABELS:
        if len(lines) >= max_lines:
            break
        d = defenses.get(k, {}) if isinstance(defenses, dict) else {}
        if isinstance(d, dict) and d.get("checked"):
            expl = d.get("explanation", "").strip()
            full_text = f"{item_num}. {label}{expl}" if expl else f"{item_num}. {label.rstrip(': ')}"
            item_num += 1

            w = pymupdf.get_text_length(full_text, fontname="helv", fontsize=font_size)
            if w <= max_width or len(lines) >= max_lines - 1:
                lines.append(full_text)
            else:
                words = full_text.split()
                l1_words = []
                for wd in words:
                    trial = " ".join(l1_words + [wd])
                    if pymupdf.get_text_length(trial, fontname="helv", fontsize=font_size) <= max_width:
                        l1_words.append(wd)
                    else:
                        break
                lines.append(" ".join(l1_words))
                rem = " ".join(words[len(l1_words):])
                if rem and len(lines) < max_lines:
                    lines.append("   " + rem)
            if len(lines) >= max_lines:
                break
    if not lines:
        return ["Defendant denies plaintiff's claims and requests that eviction be denied."]
    return lines[:max_lines]


def _build_defense_narrative(defenses: dict) -> str:
    """Build a formatted paragraph of defense explanations from checked defenses or narrative.
    Used for narrative court forms (AR, NM, TN, Denver CO) that have blank text areas.
    """
    if not defenses:
        return "The defendant requests that the court deny the eviction and allow the defendant to remain in possession of the premises."

    if isinstance(defenses, str):
        return defenses.strip() if defenses.strip() else "The defendant requests that the court deny the eviction and allow the defendant to remain in possession of the premises."

    if not isinstance(defenses, dict):
        return "The defendant requests that the court deny the eviction and allow the defendant to remain in possession of the premises."

    # 1. Check for free-form narrative keys (e.g. Denver County Court answer form)
    narrative_parts = []
    for n_key in ("narrative", "story", "statement", "free_form", "free_text", "defense_narrative"):
        val = defenses.get(n_key)
        if isinstance(val, dict):
            exp = (val.get("explanation") or val.get("text") or "").strip()
            if exp:
                narrative_parts.append(exp)
        elif isinstance(val, str) and val.strip():
            narrative_parts.append(val.strip())

    top_exp = defenses.get("explanation")
    if isinstance(top_exp, str) and top_exp.strip():
        narrative_parts.append(top_exp.strip())

    DEFENSE_LABELS = {
        "def_repairs": ("Failure to maintain premises / necessary repairs",
                        "The landlord failed to make necessary repairs to the property despite written notice."),
        "def_did_repairs": ("Tenant-performed repairs deducted from rent",
                            "I made repairs to the property that the landlord should have made, and I am entitled to deduct these costs from rent."),
        "def_amount": ("Disputed rent amount claimed",
                       "I dispute the amount of rent claimed by the landlord."),
        "def_paid": ("Rent already paid in full",
                     "I have already paid the rent that the landlord claims is owed."),
        "def_attempted_pay": ("Attempted tender of rent refused",
                              "I made a good faith effort to pay rent, but the landlord refused to accept payment."),
        "def_retaliation": ("Retaliation for tenant exercising legal rights",
                            "The landlord is evicting me in retaliation for exercising my legal rights."),
        "def_discrimination": ("Discriminatory eviction violating fair housing laws",
                               "The eviction is discriminatory and violates fair housing laws."),
        "def_bad_notice": ("Defective or improper legal notice",
                           "The landlord did not provide proper legal notice before filing this eviction."),
        "def_landlord_breach": ("Landlord breach of rental agreement",
                                "The landlord breached the rental agreement."),
        "def_not_owner": ("Plaintiff lacks standing / not property owner",
                          "The person or company suing me is not the actual owner or real party in interest."),
        "def_waived": ("Waiver of right to evict",
                       "The landlord waived the right to evict."),
        "def_accepted_rent": ("Acceptance of rent following notice",
                              "The landlord accepted my rent payment after sending the eviction notice, which cancels the eviction."),
        "def_corrected": ("Timely cure of alleged lease violation",
                          "I corrected the alleged lease violation before the applicable deadline."),
        "def_other": ("Additional affirmative defense",
                      "Defendant has additional valid legal defenses to this action."),
        "def_contest": ("Lack of jurisdiction",
                        "This court does not have proper jurisdiction over this case."),
        "def_dismiss": ("Defective pleadings / motion to dismiss",
                        "The complaint fails to state a claim upon which relief can be granted."),
    }

    checked = []
    # Any custom defense keys not in DEFENSE_LABELS or narrative_keys
    for k, v in defenses.items():
        if k in DEFENSE_LABELS:
            continue
        if k in ("narrative", "story", "statement", "free_form", "free_text", "defense_narrative", "explanation"):
            continue
        if isinstance(v, dict) and (v.get("checked") or v.get("explanation")):
            exp = (v.get("explanation") or "").strip()
            if exp:
                checked.append(exp)

    for key, (heading, default_text) in DEFENSE_LABELS.items():
        d = defenses.get(key, {})
        if isinstance(d, dict) and d.get("checked"):
            explanation = (d.get("explanation") or "").strip().rstrip(".")
            if explanation:
                checked.append(f"{heading}: {explanation}.")
            else:
                checked.append(f"{heading}: {default_text}")

    # Combine narrative texts and checked defenses
    all_sections = []
    if narrative_parts:
        all_sections.extend(narrative_parts)

    if checked:
        if not narrative_parts:
            for i, def_text in enumerate(checked, 1):
                all_sections.append(f"{i}. {def_text}")
        else:
            all_sections.extend(checked)

    if not all_sections:
        return "The defendant requests that the court deny the eviction and allow the defendant to remain in possession of the premises."

    return "\n\n".join(all_sections)
