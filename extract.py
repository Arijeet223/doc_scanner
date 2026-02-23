import cv2
import pytesseract
import json
import os
import sys

# Set your Tesseract path
pytesseract.pytesseract.tesseract_cmd = r"D:\dada\tesseract.exe"

def clean_num(value):
    # Remove all non-numeric characters for amounts
    cleaned = ''.join(c for c in value if c.isdigit() or c == '.')
    return cleaned.strip()

def extract_field(img, box):
    x1, y1, x2, y2 = box["x1"], box["y1"], box["x2"], box["y2"]
    crop = img[y1:y2, x1:x2]
    # psm 6 assumes a single uniform block of text
    text = pytesseract.image_to_string(crop, config="--psm 6")
    return text.strip()

def extract_all_fields(image_path="input.png"):
    if not os.path.exists(image_path):
        print(f"Error: Could not find '{image_path}'.")
        sys.exit(1)
        
    if not os.path.exists("template.json"):
        print("Error: Could not find 'template.json'. Please run 'python setup_template.py' first.")
        sys.exit(1)

    img = cv2.imread(image_path)

    with open("template.json", "r") as f:
        template = json.load(f)

    result = {}

    # === 1. User Defined Static Values ===
    result["processor_name"] = "Aakash Basak"
    result["tms_type"] = "2.O"          # Capital letter O, matches form option
    result["claim_sub_type"] = "Cashless"
    result["claim_type"] = "OPD"
    result["role"] = "CPD"
    result["case_type"] = "New"
    result["no_of_pages"] = ""          # User specified empty

    # === 2. Dynamically Extracted Values from Image ===
    raw_case_num = extract_field(img, template.get("case_number", {"x1":0,"y1":0,"x2":1,"y2":1}))
    # Remove pipes and parentheses
    for char in ['|', '(', ')', ' ']:
        raw_case_num = raw_case_num.replace(char, '')
    result["case_number"] = raw_case_num
    
    claimed_str = clean_num(extract_field(img, template.get("claimed_amount", {"x1":0,"y1":0,"x2":1,"y2":1})))
    approved_str = clean_num(extract_field(img, template.get("approved_amount", {"x1":0,"y1":0,"x2":1,"y2":1})))
    
    result["claimed_amount"] = claimed_str
    result["approved_amount"] = approved_str
    
    # Extract Scheme 
    raw_scheme = extract_field(img, template.get("scheme", {"x1":0,"y1":0,"x2":1,"y2":1}))
    # Scheme matching logic (CAPF, CGHS, ESIC, NDRF, NAMASTE)
    valid_schemes = ["CAPF", "CGHS", "ESIC", "NDRF", "NAMASTE"]
    matched_scheme = "CAPF" # default fallback
    for s in valid_schemes:
        if s.lower() in raw_scheme.lower():
            matched_scheme = s
            break
    result["scheme"] = matched_scheme
    
    # Extract Action Taken text
    raw_action = extract_field(img, template.get("action_taken", {"x1":0,"y1":0,"x2":1,"y2":1}))
    
    # Extract Remarks
    raw_remarks = extract_field(img, template.get("remarks", {"x1":0,"y1":0,"x2":1,"y2":1}))
    result["remarks"] = raw_remarks
    result["reason"] = raw_remarks  # Section 14 always uses the remarks from the image
    
    # === 3. Derived Logic: Action Taken + Section 12 deficiencies_text ===
    # Convert amounts to floats for comparison
    try:
        c_amt = float(claimed_str) if claimed_str else 0.0
    except ValueError:
        c_amt = 0.0
        
    try:
        a_amt = float(approved_str) if approved_str else 0.0
    except ValueError:
        a_amt = 0.0

    action_lower = raw_action.lower()

    # Determine action_taken from the photo text first
    if "query" in action_lower:
        action_taken_value = "Query"
    elif "reject" in action_lower:
        action_taken_value = "Reject"
        result["approved_amount"] = "0"  # Reject = 0 approved
    elif "approved" in action_lower or "approve" in action_lower:
        # Deduction check: claimed > approved and approved > 0
        if c_amt > a_amt and a_amt > 0:
            action_taken_value = "Approved With Deduction"
        else:
            action_taken_value = "Approved"
    else:
        # Fallback: use amount comparison alone
        if c_amt > a_amt and a_amt > 0:
            action_taken_value = "Approved With Deduction"
        else:
            action_taken_value = "Approved"

    result["action_taken"] = action_taken_value

    # Section 12 — always "Other"
    # Text box: "NA" when simply Approved, otherwise write the action label
    result["deficiencies"] = "Other"
    result["deficiencies_text"] = "NA" if action_taken_value == "Approved" else action_taken_value

    return result

if __name__ == "__main__":
    # Internal test only if run directly
    pass
