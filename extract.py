import cv2
import pytesseract
import json
import os
import sys
import re

# Set your Tesseract path
pytesseract.pytesseract.tesseract_cmd = r"D:\dada\tesseract.exe"

# ---------------------------------------------------------------------------
# LOW-LEVEL HELPERS
# ---------------------------------------------------------------------------

def _get_ocr_words(img):
    """
    Run Tesseract and return a list of word dicts:
      { text, left, top, width, height, right, bottom, conf }
    Only returns words with confidence >= 20 and non-empty text.
    """
    data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT, config="--psm 3")
    words = []
    for i in range(len(data["text"])):
        txt = data["text"][i].strip()
        conf = int(data["conf"][i])
        if txt and conf >= 20:
            l = data["left"][i]
            t = data["top"][i]
            w = data["width"][i]
            h = data["height"][i]
            words.append({
                "text":   txt,
                "left":   l,
                "top":    t,
                "width":  w,
                "height": h,
                "right":  l + w,
                "bottom": t + h,
                "conf":   conf,
            })
    return words


def _find_anchors(words, anchor_query, case_insensitive=True):
    """
    Return all word dicts whose text contains anchor_query.
    """
    q = anchor_query.lower() if case_insensitive else anchor_query
    matches = []
    for w in words:
        t = w["text"].lower() if case_insensitive else w["text"]
        if q in t:
            matches.append(w)
    return matches


def _words_on_same_row(words, anchor, y_tolerance=12):
    """Words whose vertical centre is within y_tolerance px of the anchor's centre."""
    cy = (anchor["top"] + anchor["bottom"]) / 2
    return [w for w in words if abs((w["top"] + w["bottom"]) / 2 - cy) <= y_tolerance]


def _words_below(words, anchor, max_dy=80, x_min=None, x_max=None):
    """
    Words that start below the anchor's bottom edge, within max_dy pixels,
    and optionally within a horizontal range.
    """
    result = []
    for w in words:
        if w["top"] >= anchor["bottom"] and (w["top"] - anchor["bottom"]) <= max_dy:
            if x_min is not None and w["right"] < x_min:
                continue
            if x_max is not None and w["left"] > x_max:
                continue
            result.append(w)
    return result


def _words_right_of(words, anchor, max_dx=500, y_tolerance=12):
    """Words to the right of the anchor on the same row."""
    return [
        w for w in words
        if w["left"] > anchor["right"]
        and (w["left"] - anchor["right"]) <= max_dx
        and abs((w["top"] + w["bottom"]) / 2 - (anchor["top"] + anchor["bottom"]) / 2) <= y_tolerance
    ]


def _text_of(word_list, sep=" "):
    return sep.join(w["text"] for w in sorted(word_list, key=lambda w: w["left"]))


# ---------------------------------------------------------------------------
# FIELD EXTRACTORS  (each takes the full word list)
# ---------------------------------------------------------------------------

def _extract_case_number(words):
    """
    Look for the breadcrumb line: 'Case Details (CAPF/PVT/R1/2025/...)'.
    The case number is the text inside the parentheses.
    """
    # Strategy 1: find an anchor word 'Details' and look to the right on same row
    for anchor_text in ["Details", "details"]:
        anchors = _find_anchors(words, anchor_text)
        for anc in anchors:
            row = _words_on_same_row(words, anc, y_tolerance=15)
            row_text = _text_of(row)
            # Look for something like (CAPF/.../.../.../....)
            m = re.search(r'\(([A-Z0-9/\-]+)\)', row_text)
            if m:
                return m.group(1)
            # Sometimes brackets are split across words — join and retry
            raw = re.sub(r'\s+', '', row_text)
            m2 = re.search(r'\(([A-Z0-9/\-]+)\)', raw)
            if m2:
                return m2.group(1)

    # Strategy 2: scan all words for something that looks like CAPF/PVT/R1/...
    for w in words:
        m = re.search(r'((?:CAPF|CGHS|ESIC|NDRF|NAMASTE)/[A-Z0-9/\-]{5,})', w["text"])
        if m:
            return m.group(1)

    return ""


def _extract_scheme(case_number, words):
    """
    Derive scheme from case number prefix.  Fall back to scanning all words.
    """
    valid_schemes = ["CAPF", "CGHS", "ESIC", "NDRF", "NAMASTE"]
    for s in valid_schemes:
        if case_number.upper().startswith(s):
            return s

    # Fallback: scan every word
    for w in words:
        for s in valid_schemes:
            if s in w["text"].upper():
                return s

    return "CAPF"  # default


def _extract_claimed_amount(words):
    """
    Find the 'Claimed Amount' label in the top summary bar (top ~300 px of the
    document, right side) and read the value below it.

    Strategy:
      1. Locate the 'Claimed' word that is in the top header strip (y < 300)
         and on the right side of the page (x > 1000).
      2. Grab the largest valid decimal number from the words below that anchor
         within ~80 px, and also from the same row to the right.
    """
    img_top_threshold = 300  # only look in the top banner/header

    # Filter to the Claimed label in the top header
    header_claimed = [
        w for w in _find_anchors(words, "Claimed")
        if w["top"] < img_top_threshold and w["left"] > 1000
    ]

    for anc in header_claimed:
        candidates = (
            _words_below(words, anc, max_dy=80,
                         x_min=anc["left"] - 50, x_max=anc["right"] + 300)
            + _words_right_of(words, anc, max_dx=300)
        )
        nums = []
        for w in candidates:
            clean = re.sub(r'[^\d.,]', '', w["text"])
            if re.match(r'^\d[\d,]*(\.(\d+))?$', clean) and len(clean) >= 3:
                nums.append(float(clean.replace(',', '')))
        if nums:
            return str(max(nums))  # take the largest (avoids stray lone digits)

    # Fallback: scan all words for a currency value on a 'Claimed Amount' row.
    # Look for a pattern: word 'Claimed' anywhere near a ₹ value.
    for anc in _find_anchors(words, "Claimed"):
        row = _words_on_same_row(words, anc, y_tolerance=15)
        for w in sorted(row, key=lambda x: -x["left"]):
            clean = re.sub(r'[^\d.,]', '', w["text"])
            if re.match(r'^\d[\d,]*(\.(\d+))?$', clean) and len(clean) >= 3:
                return clean.replace(',', '')
    return ""


def _extract_approved_amount(words):
    """
    Find 'Claim amount approved (After technical evaluation)' in the adjudication
    summary block and read the rupee value at the right end of that row.

    Strategy:
      1. Use the highly unique word 'technical' (or 'evaluation') as the anchor —
         this phrase only appears in this one label on the page.
      2. Grab the rightmost valid decimal number on that row.
      3. Fallback: find a row containing both 'approved' and 'technical'.
    """
    def _best_num_on_row(row):
        """Return the rightmost decimal number string from a list of word dicts."""
        nums = []
        for w in sorted(row, key=lambda x: x["left"], reverse=True):
            clean = re.sub(r'[^\d.,]', '', w["text"])
            if re.match(r'^\d[\d,]*(\.(\d+))?$', clean) and len(clean) >= 3:
                nums.append(clean.replace(',', ''))
        return nums[0] if nums else None

    # Primary anchor: 'technical'
    for anc in _find_anchors(words, "technical"):
        row = _words_on_same_row(words, anc, y_tolerance=18)
        row_text = _text_of(row).lower()
        if "approved" in row_text or "claim" in row_text:
            val = _best_num_on_row(row)
            if val:
                return val

    # Secondary anchor: 'evaluation'
    for anc in _find_anchors(words, "evaluation"):
        row = _words_on_same_row(words, anc, y_tolerance=18)
        row_text = _text_of(row).lower()
        if "approved" in row_text or "claim" in row_text:
            val = _best_num_on_row(row)
            if val:
                return val

    # Tertiary: any 'approved' anchor whose row also contains 'bill' or 'amount'
    # but exclude very low y (bottom Action area) and very high y (header area)
    for anc in _find_anchors(words, "approved"):
        if anc["top"] < 400 or anc["top"] > 2100:
            continue
        row = _words_on_same_row(words, anc, y_tolerance=15)
        row_text = _text_of(row).lower()
        if "claim" in row_text and "amount" in row_text:
            val = _best_num_on_row(row)
            if val:
                return val

    return ""


def _extract_action(words):
    """
    Find the standalone 'Action' label near the bottom of the page (above the
    approval dropdown) and return the selected value below it.

    Strategy:
      1. Find all 'Action' words (handles OCR artifacts like 'Action*', 'Action'')
         that are in the lower third of the document (y > 1800).
      2. The label row typically contains only 'Action' ± an asterisk/symbol.
      3. Grab the word(s) directly below within 120 px — that's the dropdown value
         (e.g. 'Approve', 'Query', 'Reject').
    """
    # Estimate lower-third threshold from the doc's word extent
    if words:
        max_y = max(w["top"] for w in words)
        lower_threshold = max_y * 0.6
    else:
        lower_threshold = 1500

    action_anchors = []
    for w in words:
        # Match 'Action', 'Action*', "Action'", etc. — strip non-alpha chars
        base = re.sub(r'[^A-Za-z]', '', w["text"])
        if base.lower() == "action" and w["top"] > lower_threshold:
            action_anchors.append(w)

    for anc in sorted(action_anchors, key=lambda x: x["top"]):
        row = _words_on_same_row(words, anc, y_tolerance=12)
        row_text = re.sub(r'[^A-Za-z ]', '', _text_of(row)).strip()
        # Confirm it's the standalone label (not 'Actionable details' header)
        if len(row_text.split()) <= 2 and "actionable" not in row_text.lower():
            below = _words_below(words, anc, max_dy=120,
                                  x_min=anc["left"] - 100, x_max=anc["left"] + 600)
            if below:
                below_text = _text_of(sorted(below, key=lambda w: (w["top"], w["left"])))
                return below_text
    return ""


def _extract_remarks(words):
    """
    Find the standalone 'Remarks' label near the bottom (not the column header
    in the Actionable details table) and collect all text below it until SUBMIT.

    Strategy:
      1. Find 'Remarks' words in the lower portion of the document.
      2. Confirm it is the standalone label (row has ≤ 2 words).
      3. Collect every word below the anchor until 'SUBMIT' or 'CANCEL' is seen,
         then join them grouped by row to reconstruct the paragraph.
    """
    if words:
        max_y = max(w["top"] for w in words)
        lower_threshold = max_y * 0.6
    else:
        lower_threshold = 1500

    remarks_anchors = [
        w for w in words
        if re.sub(r'[^A-Za-z]', '', w["text"]).lower() == "remarks"
        and w["top"] > lower_threshold
    ]

    for anc in sorted(remarks_anchors, key=lambda x: x["top"]):
        row = _words_on_same_row(words, anc, y_tolerance=10)
        row_text = re.sub(r'[^A-Za-z ]', '', _text_of(row)).strip()
        if len(row_text.split()) <= 2:
            # Collect words below the Remarks label heading
            below = []
            for w in sorted(words, key=lambda x: (x["top"], x["left"])):
                if w["top"] <= anc["bottom"]:
                    continue
                if w["text"].upper() in ("SUBMIT", "CANCEL", "CHARACTER", "LIMIT:"):
                    break
                # Skip sidebar noise: 1-2 char tokens that aren't real words
                txt = w["text"].strip()
                if len(txt) <= 2 and not txt.isalpha():
                    continue
                below.append(w)
            if below:
                # Group by row and join to preserve line breaks naturally
                lines_grouped = {}
                for w in below:
                    row_key = round(w["top"] / 20) * 20  # bucket by ~20px
                    lines_grouped.setdefault(row_key, []).append(w)
                text_lines = []
                for row_key in sorted(lines_grouped):
                    text_lines.append(
                        " ".join(w["text"] for w in
                                 sorted(lines_grouped[row_key], key=lambda x: x["left"]))
                    )
                return " ".join(text_lines)
    return ""


# ---------------------------------------------------------------------------
# PUBLIC API
# ---------------------------------------------------------------------------

def clean_num(value):
    """Remove all non-numeric characters for amounts."""
    cleaned = ''.join(c for c in value if c.isdigit() or c == '.')
    return cleaned.strip()


def extract_all_fields(image_path="input.png"):
    if not os.path.exists(image_path):
        print(f"Error: Could not find '{image_path}'.")
        sys.exit(1)

    img = cv2.imread(image_path)
    if img is None:
        print(f"Error: Could not read '{image_path}'. Ensure it is a valid image.")
        sys.exit(1)

    print("Running OCR (this may take a few seconds)...")
    words = _get_ocr_words(img)

    result = {}

    # === 1. Static values ===
    result["processor_name"]  = "Aakash Basak"
    result["tms_type"]        = "2.O"
    result["claim_sub_type"]  = "Cashless"
    result["claim_type"]      = "OPD"
    result["role"]            = "CPD"
    result["case_type"]       = "New"
    result["no_of_pages"]     = ""

    # === 2. Anchor-based dynamic extraction ===
    case_number = _extract_case_number(words)
    # Clean up stray punctuation
    for char in ['|', '(', ')', ' ']:
        case_number = case_number.replace(char, '')
    result["case_number"] = case_number

    result["scheme"] = _extract_scheme(case_number, words)

    claimed_str  = clean_num(_extract_claimed_amount(words))
    approved_str = clean_num(_extract_approved_amount(words))
    result["claimed_amount"]  = claimed_str
    result["approved_amount"] = approved_str

    raw_action  = _extract_action(words)
    raw_remarks = _extract_remarks(words)
    result["remarks"] = raw_remarks
    result["reason"]  = raw_remarks

    # === 3. Derived logic: action_taken + deficiencies_text ===
    try:
        c_amt = float(claimed_str) if claimed_str else 0.0
    except ValueError:
        c_amt = 0.0

    try:
        a_amt = float(approved_str) if approved_str else 0.0
    except ValueError:
        a_amt = 0.0

    action_lower = raw_action.lower()

    if "query" in action_lower:
        action_taken_value = "Query"
    elif "reject" in action_lower:
        action_taken_value = "Reject"
        result["approved_amount"] = "0"
    elif "approved" in action_lower or "approve" in action_lower:
        if c_amt > a_amt and a_amt > 0:
            action_taken_value = "Approved With Deduction"
        else:
            action_taken_value = "Approved"
    else:
        # Fallback: use amount comparison
        if c_amt > a_amt and a_amt > 0:
            action_taken_value = "Approved With Deduction"
        else:
            action_taken_value = "Approved"

    result["action_taken"] = action_taken_value

    # Section 12 — always "Other"
    result["deficiencies"]      = "Other"
    result["deficiencies_text"] = "NA" if action_taken_value == "Approved" else action_taken_value

    return result


if __name__ == "__main__":
    data = extract_all_fields("input.png")
    print("\nExtracted fields:")
    for k, v in data.items():
        print(f"  {k}: {v!r}")
