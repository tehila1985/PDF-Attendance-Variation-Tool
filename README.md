# Attendance Report Variation System

Python system for processing Hebrew attendance PDFs with deterministic variation.
Reads a scanned or digital attendance report, classifies it, parses it into structured rows, shifts all times by a deterministic seed-based offset, and outputs a new PDF or HTML.

## Pipeline

```
PDF input → OCR → Classify → Parse → Transform → Render → PDF / HTML / JSON output
```

## Supported Report Types

### Type A
Columns: `תאריך | יום | שעת כניסה | שעת יציאה | סה"כ שעות`

### Type B
Columns: `תאריך | יום | מקום | כניסה | יציאה | הפסקה | סה"כ | % 100 / 125 / 150`

## Directory Structure

```
core/
  entities.py               – Domain models: AttendanceRow, AttendanceReport, OCRResult
interfaces/                 – ABCs: OCRService, ReportParser, BaseTransformationStrategy, BaseRenderer
services/
  ocr_service.py            – PyMuPDF + Tesseract; auto-discovers tesseract.exe on Windows
  classifier.py             – Classifies TYPE_A / TYPE_B by header line → row structure → keywords
  strategies.py             – TypeATransformationStrategy, TypeBTransformationStrategy
  transformation_service.py – Applies strategies row-by-row with per-row seeded RNG
  decorators.py             – ValidatingStrategyDecorator: audits every transformed row
  variation_engine.py       – Backward-compatible alias (DeterministicVariationService)
parsers/
  base_parser.py            – Template Method skeleton shared by both parsers
  type_a_parser.py          – Parses TYPE_A rows; rejects rows with TYPE_B markers
  type_b_parser.py          – Parses TYPE_B rows; extracts location, break, overtime %
  common.py                 – Shared regex patterns and helpers
  factory.py                – Returns the correct parser for a given ReportType
generators/
  pdf_generator.py          – ReportLab PDF output; registers Arial TTF for Hebrew rendering
  html_renderer.py          – Self-contained HTML output with RTL CSS
web/
  app.py                    – Flask web interface for the same pipeline
main.py                     – CLI entry point
```

## Install

### 1. Python environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

For development and tests:

```powershell
pip install -r requirements-dev.txt
```

### 2. Tesseract OCR

Required only for scanned (image-based) PDFs. Digital PDFs with embedded text work without it.

**Windows:** Download from [github.com/UB-Mannheim/tesseract/wiki](https://github.com/UB-Mannheim/tesseract/wiki) and install.  
The system auto-discovers `tesseract.exe` in `C:\Program Files\Tesseract-OCR\` even if it is not on PATH.  
Install the **Hebrew** language pack (`heb.traineddata`) during setup.

**Manual override:**

```powershell
python main.py "input.pdf" "output.pdf" --tesseract-cmd "C:\Program Files\Tesseract-OCR\tesseract.exe"
```

## Usage

```powershell
# Install the package locally
python -m pip install -e .

# PDF output (default)
python main.py "input_report.pdf" "output_varied.pdf" --seed 42

# HTML output
python main.py "input_report.pdf" "output_varied.html" --output-format html

# JSON output
python main.py "input_report.pdf" "output_varied.json" --output-format json

# Custom output directory (filename auto-generated)
python main.py "input_report.pdf" -o "real_reports_output" --seed 42

# All options
python main.py "input_report.pdf" "output.pdf" --seed 42 --ocr-lang "heb+eng" --tesseract-cmd "..." --log-level DEBUG
```

## Variation Rules

For each row, independently per seed:

- Start time shifted by a random value in `[-10, +10]` minutes
- End time shifted by a random value in `[-10, +10]` minutes
- Invariant enforced: `end_time > start_time` always
- `total_hours` recalculated from the new start/end (minus break for Type B)
- Type B overtime columns (`125%`, `150%`) shifted by `[-5, +5]` minutes
- Monthly total recomputed from all modified rows

The seed is combined with a per-row hash of `(index, date, start, end, total, location, %)` so the same input + same seed always produces the same output.

## Classification Logic

The classifier tries three strategies in order:

1. **Header line** — finds the table header row and checks for `שעת כניסה שעת יציאה` (TYPE_A) or `מקום` + percentage columns (TYPE_B)
2. **Row structure** — counts data rows matching each type's expected column pattern
3. **Keyword scoring** — raw keyword count fallback

If classification still fails, `main.py` falls back to filename heuristics (`a_r` → TYPE_A, `n_r` → TYPE_B), then tries both parsers and picks the one that extracts more rows.

## Error Handling

| Situation | Behaviour |
|---|---|
| Scanned PDF, no Tesseract | `RuntimeError` with clear install instructions |
| Unknown report type | Falls back through filename → parser-success heuristics, raises if all fail |
| Row fails validation after transform | Original row kept, warning logged (graceful degradation) |
| Both parsers fail | Empty report generated with warning |

## Testing

```powershell
python -m pytest -q
```

21 tests covering: classifier (header / row-structure / keyword), OCR service auto-discovery, parsers (TYPE_A rejection of TYPE_B rows, TYPE_B location/break/percentage extraction), PDF generator Hebrew rendering helper, variation engine (determinism, constraints, seed reproducibility), core entity helpers.
