# TMS Form Auto-Fill Tool

Automatically extracts claim data from a TMS screenshot and fills the corresponding Microsoft Form using Selenium.

Works on **any screenshot of the NHA TMS portal** — documents can vary in length (more rows, expanded sections, extra content) and extraction will still work correctly.

---

## How It Works

1. **`extract.py`** — Reads `input.png` and uses Tesseract OCR to locate fields by searching for nearby text **labels** (e.g. `"Claimed Amount"`, `"Action"`, `"Remarks"`) rather than fixed pixel positions. This makes it robust to documents of any height.
2. **`fill_form.py`** — Opens the Microsoft Form in Chrome and fills every field using the extracted data.
3. **`main.py`** — Entry point. Runs extract → fill in sequence.
4. **`setup_template.py`** *(optional, legacy)* — Only needed if anchor detection fails on an unusual layout. Lets you manually draw bounding boxes to override extraction for specific fields.

---

## Setup

### Prerequisites

- Python 3.8+
- Google Chrome
- [ChromeDriver](https://chromedriver.chromium.org/) matching your Chrome version, on PATH
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) installed locally

### Install Python dependencies

```bash
pip install -r requirements.txt
```

### Configure Tesseract path

In `extract.py`, update this line to point to your Tesseract executable:

```python
pytesseract.pytesseract.tesseract_cmd = r"D:\dada\tesseract.exe"
```

---

## Usage

Save your TMS screenshot as **`input.png`** in the project folder, then run:

```bash
python main.py
```

The script will:
- Run OCR on `input.png` and print all extracted values
- Open Chrome and fill the form automatically
- Keep the browser open for you to **review and submit manually**

Press **Ctrl+C** in the terminal when you are done.

---

## Anchor-Based Extraction

Fields are located by finding a distinctive text label in the OCR output and reading the value near it. This means extraction is **position-independent** — it doesn't matter where on the page a field appears vertically.

| Field | How it's found |
|---|---|
| `case_number` | Searches for `"Case Details"` breadcrumb, reads text in parentheses on that line |
| `scheme` | Parsed from the case number prefix (e.g. `CAPF/PVT/...` → `CAPF`) |
| `claimed_amount` | Finds `"Claimed Amount"` label, reads nearest number below/right |
| `approved_amount` | Finds `"Claim amount approved"` label, reads number to its right |
| `action_taken` | Finds standalone `"Action"` label, reads value below it |
| `remarks` | Finds `"Remarks"` label, collects all text below until `SUBMIT` |

### Action Taken logic

| Condition | Result |
|---|---|
| Action text contains `"query"` | `Query` |
| Action text contains `"reject"` | `Reject` (approved amount set to `0`) |
| Action text contains `"approv"` and claimed > approved > 0 | `Approved With Deduction` |
| Action text contains `"approv"` otherwise | `Approved` |
| No keyword match — claimed > approved > 0 | `Approved With Deduction` |
| No keyword match — otherwise | `Approved` |

---

## Static Field Values

These are always written as-is regardless of the document:

| Form Field | Value |
|---|---|
| Name of Processor | `Aakash Basak` |
| Type of TMS | `2.O` |
| Claim Sub Type | `Cashless` |
| Claim Type | `OPD` |
| Role | `CPD` |
| Case Type | `New` |
| Deficiencies (Q12) | Always `Other`; text = `NA` for Approved, else the action label |
| Other Remarks | `NA` |

---

## Project Files

```
project/
├── main.py              # Entry point
├── extract.py           # Anchor-based OCR extraction
├── fill_form.py         # Selenium form-filling logic
├── setup_template.py    # Legacy: manual bounding-box override (not normally needed)
├── template.json        # Legacy: saved coordinates (not used at runtime)
├── input.png            # Your TMS screenshot (not committed)
├── output.json          # Last extracted data (auto-generated)
├── requirements.txt     # Python dependencies
├── debug_tms.py         # Debug: dumps HTML near a form question
└── debug_form.py        # Debug: general form inspection
```

---

## Troubleshooting

| Issue | Fix |
|---|---|
| `Error: Could not find 'input.png'` | Save your screenshot as `input.png` in the project folder |
| A field extracts incorrectly | Run `setup_template.py` to manually draw a bounding box for that field, then use `extract_field()` as a fallback in `extract.py` |
| OCR is very slow | Ensure Tesseract is installed correctly and the image is not extremely high-resolution |
| Dropdown / radio button not clicked | Run `debug_tms.py` or `debug_form.py` to inspect the live form HTML |
| ChromeDriver error | Ensure ChromeDriver version matches your installed Chrome version |
