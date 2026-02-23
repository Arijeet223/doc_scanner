# TMS Form Auto-Fill Tool

Automatically extracts claim data from a TMS screenshot and fills the corresponding Microsoft Form using Selenium.

---

## How It Works

1. **`setup_template.py`** — Run once to define which regions of your screenshot contain each field. Saves coordinates to `template.json`.
2. **`extract.py`** — Reads `input.png` and uses Tesseract OCR to pull field values from the regions defined in `template.json`.
3. **`fill_form.py`** — Opens the Microsoft Form in Chrome and fills every field using the extracted data.
4. **`main.py`** — Entry point. Runs extract → fill in sequence.

---

## Setup

### Prerequisites

- Python 3.8+
- Google Chrome
- [ChromeDriver](https://chromedriver.chromium.org/) (matching your Chrome version, on PATH)
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

### Step 1 — Set up the template (first time only)

Save your TMS screenshot as `input.png` in the project folder, then run:

```bash
python setup_template.py
```

A window opens for each field. Click and drag to draw a bounding box around the text for that field, then press **Space** or **Enter** to confirm. Repeat for all fields. Coordinates are saved to `template.json`.

**Fields captured:**
| Field | Description |
|---|---|
| `case_number` | Claim/case ID |
| `claimed_amount` | Total amount claimed |
| `approved_amount` | Amount approved |
| `scheme` | Scheme name (CAPF, CGHS, ESIC, NDRF, NAMASTE) |
| `action_taken` | Decision text (Approved / Query / Reject) |
| `remarks` | Remarks / reason text |

### Step 2 — Run the automation

```bash
python main.py
```

The script will:
- Extract all fields from `input.png` via OCR
- Print the extracted values to the terminal
- Open Chrome and fill the form automatically
- Keep the browser open for you to **review and submit manually**

Press **Ctrl+C** in the terminal when you are done.

---

## Field Mapping & Logic

| Form Field | Source |
|---|---|
| Name of Processor | Static: `Aakash Basak` |
| Type of TMS | Static: `2.O` |
| Claim Sub Type | Static: `Cashless` |
| Claim Type | Static: `OPD` |
| Role | Static: `CPD` |
| Case Type | Static: `New` |
| Case Number | OCR from image |
| Claimed Amount | OCR from image |
| Approved Amount | OCR from image |
| Scheme | OCR → matched to valid list |
| Action Taken | Derived (see below) |
| Deficiencies (Q12) | Always `Other`; text box filled with action label |
| Reasons (Q14) | OCR remarks text |
| Other Remarks | Static: `NA` |

### Action Taken logic

The `action_taken` value is derived from the extracted action text and the amounts:

- Contains **"query"** → `Query`
- Contains **"reject"** → `Reject` (approved amount set to `0`)
- Contains **"approv"** and claimed > approved > 0 → `Approved With Deduction`
- Contains **"approv"** otherwise → `Approved`
- No keyword match → falls back to amount comparison

---

## Project Files

```
project/
├── main.py              # Entry point
├── extract.py           # OCR extraction logic
├── fill_form.py         # Selenium form-filling logic
├── setup_template.py    # Interactive bounding box setup
├── template.json        # Saved field region coordinates
├── input.png            # Your TMS screenshot (not committed)
├── output.json          # Last extracted data (auto-generated)
├── requirements.txt     # Python dependencies
├── debug_tms.py         # Debug helper: dumps HTML near a form question
└── debug_form.py        # Debug helper: general form inspection
```

---

## Troubleshooting

| Issue | Fix |
|---|---|
| `Error: Could not find 'input.png'` | Save your screenshot as `input.png` in the project folder |
| `Error: Could not find 'template.json'` | Run `setup_template.py` first |
| OCR reads wrong text | Re-run `setup_template.py` and draw tighter bounding boxes |
| Dropdown / radio button not clicked | Run `debug_tms.py` or `debug_form.py` to inspect the live form HTML |
| ChromeDriver error | Ensure ChromeDriver version matches your installed Chrome version |
