from __future__ import annotations

import os
import sys
import uuid
import logging
import tempfile
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_file

# ---------------------------------------------------------------------------
# Make the project root importable when running  `python web/app.py`
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.entities import ReportType
from generators.html_renderer import HtmlRenderer
from generators.pdf_generator import PdfRenderer
from interfaces.renderer import BaseRenderer
from main import run_pipeline

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = Flask(__name__, template_folder="templates", static_folder="static")
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024  # 20 MB upload limit

UPLOAD_DIR = Path(tempfile.gettempdir()) / "attendance_uploads"
OUTPUT_DIR = Path(tempfile.gettempdir()) / "attendance_outputs"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXT = {".pdf"}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)


def _safe_filename(name: str) -> str:
    """Return a filename using only the base name, no path traversal."""
    return Path(name).name


def _allowed(filename: str) -> bool:
    return Path(filename).suffix.lower() in ALLOWED_EXT


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/process", methods=["POST"])
def process():
    """
    Accepts:
      - file      : PDF upload (multipart/form-data)
      - seed      : optional string (default "42")
      - ocr_lang  : optional string (default "heb+eng")
      - format    : "pdf" | "html" (default "pdf")
      - tesseract : optional path to tesseract exe
    Returns:
      - JSON { ok, filename, download_url } on success
      - JSON { ok, error } on failure
    """
    if "file" not in request.files:
        return jsonify(ok=False, error="No file uploaded"), 400

    upload = request.files["file"]
    if not upload.filename or not _allowed(upload.filename):
        return jsonify(ok=False, error="Only PDF files are accepted"), 400

    seed = request.form.get("seed", "42")
    ocr_lang = request.form.get("ocr_lang", "heb+eng")
    output_format = request.form.get("format", "pdf").lower()
    tesseract_cmd = request.form.get("tesseract") or None

    if output_format not in ("pdf", "html"):
        return jsonify(ok=False, error="format must be 'pdf' or 'html'"), 400

    # Save upload to temp
    safe_name = _safe_filename(upload.filename)
    job_id = uuid.uuid4().hex
    input_path = UPLOAD_DIR / f"{job_id}_{safe_name}"
    upload.save(str(input_path))

    ext = "html" if output_format == "html" else "pdf"
    stem = Path(safe_name).stem
    output_path = OUTPUT_DIR / f"{job_id}_{stem}_varied.{ext}"

    try:
        renderer: BaseRenderer = HtmlRenderer() if output_format == "html" else PdfRenderer()
        _run_pipeline(
            input_pdf=str(input_path),
            output_path=str(output_path),
            seed=seed,
            ocr_lang=ocr_lang,
            tesseract_cmd=tesseract_cmd,
            renderer=renderer,
        )
    except Exception as exc:
        logging.exception("Pipeline error: %s", exc)
        return jsonify(ok=False, error=str(exc)), 500
    finally:
        try:
            input_path.unlink()
        except OSError:
            pass

    download_name = f"{stem}_varied.{ext}"
    return jsonify(
        ok=True,
        filename=download_name,
        download_url=f"/api/download/{output_path.name}",
    )


@app.route("/api/download/<filename>")
def download(filename: str):
    """Serve a processed file for download, then delete it."""
    safe = _safe_filename(filename)
    file_path = OUTPUT_DIR / safe

    if not file_path.exists() or not file_path.is_file():
        return jsonify(ok=False, error="File not found or already downloaded"), 404

    # Guard against path traversal: must resolve inside OUTPUT_DIR
    try:
        file_path.resolve().relative_to(OUTPUT_DIR.resolve())
    except ValueError:
        return jsonify(ok=False, error="Forbidden"), 403

    mime = "text/html" if safe.endswith(".html") else "application/pdf"

    def _remove_after():
        try:
            file_path.unlink()
        except OSError:
            pass

    response = send_file(str(file_path), mimetype=mime, as_attachment=True, download_name=safe)
    response.call_on_close(_remove_after)
    return response


# ---------------------------------------------------------------------------
# Internal pipeline (mirrors main.py logic)
# ---------------------------------------------------------------------------

def _run_pipeline(
    input_pdf: str,
    output_path: str,
    seed: str,
    ocr_lang: str,
    tesseract_cmd: str | None,
    renderer: BaseRenderer,
) -> None:
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    run_pipeline(
        input_pdf=input_pdf,
        output_path=output_path,
        seed=seed,
        ocr_lang=ocr_lang,
        tesseract_cmd=tesseract_cmd,
        renderer=renderer,
    )


# ---------------------------------------------------------------------------
# Dev server entry-point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
