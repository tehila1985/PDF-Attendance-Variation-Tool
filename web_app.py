from __future__ import annotations

import secrets
import time
from pathlib import Path

from flask import Flask, abort, render_template, request, send_file, url_for
from werkzeug.utils import secure_filename

from main import process_file


MAX_UPLOAD_SIZE = 16 * 1024 * 1024
RUNTIME_ROOT = Path("attendance_processing") / "web_runtime"
UPLOAD_DIR = RUNTIME_ROOT / "uploads"
OUTPUT_DIR = RUNTIME_ROOT / "outputs"
EXPIRATION_SECONDS = 60 * 60 * 8

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_SIZE


def _ensure_runtime_dirs() -> None:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _cleanup_expired_files() -> None:
    threshold = time.time() - EXPIRATION_SECONDS
    for directory in (UPLOAD_DIR, OUTPUT_DIR):
        for file_path in directory.glob("*.pdf"):
            try:
                if file_path.stat().st_mtime < threshold:
                    file_path.unlink()
            except OSError:
                continue


def _build_summary(report) -> dict[str, str | int | float | None]:
    total_payment = getattr(report, "total_payment", None)
    return {
        "report_type": report.report_type,
        "employee_name": report.employee_name,
        "month_year": report.month_year,
        "row_count": len(report.rows),
        "total_monthly_hours": round(report.total_monthly_hours, 2),
        "total_payment": round(total_payment, 2) if isinstance(total_payment, (int, float)) else None,
    }


def _is_allowed_pdf(filename: str) -> bool:
    return Path(filename).suffix.lower() == ".pdf"


@app.route("/", methods=["GET", "POST"])
def index():
    _ensure_runtime_dirs()
    _cleanup_expired_files()

    if request.method == "POST":
        uploaded_file = request.files.get("report_file")
        if uploaded_file is None or not uploaded_file.filename:
            return render_template("index.html", error="בחר קובץ PDF להעלאה.")

        original_name = secure_filename(uploaded_file.filename)
        if not original_name or not _is_allowed_pdf(original_name):
            return render_template("index.html", error="מותר להעלות רק קבצי PDF.")

        token = secrets.token_hex(6)
        upload_name = f"{Path(original_name).stem}_{token}.pdf"
        upload_path = UPLOAD_DIR / upload_name
        uploaded_file.save(upload_path)

        try:
            result = process_file(upload_path, OUTPUT_DIR)
        except Exception as exc:
            try:
                upload_path.unlink(missing_ok=True)
            except OSError:
                pass
            return render_template("index.html", error=f"העיבוד נכשל: {exc}")

        return render_template(
            "index.html",
            success="הקובץ עובד ונוצר PDF חדש להורדה.",
            summary=_build_summary(result.report_data),
            download_url=url_for("download_file", filename=Path(result.output_path).name),
            original_name=uploaded_file.filename,
        )

    return render_template("index.html")


@app.get("/download/<path:filename>")
def download_file(filename: str):
    _ensure_runtime_dirs()
    safe_name = secure_filename(filename)
    file_path = OUTPUT_DIR / safe_name
    if not file_path.exists():
        abort(404)
    return send_file(file_path, as_attachment=True, download_name=file_path.name, mimetype="application/pdf")


if __name__ == "__main__":
    _ensure_runtime_dirs()
    app.run(debug=True)