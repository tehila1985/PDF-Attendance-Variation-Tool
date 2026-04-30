from __future__ import annotations

from pathlib import Path

from services.ocr_service import TesseractPyMuPDFOCRService


def test_resolve_tesseract_cmd_uses_explicit_path() -> None:
    path = r"C:\tools\tesseract.exe"

    assert TesseractPyMuPDFOCRService._resolve_tesseract_cmd(path) == path


def test_resolve_tesseract_cmd_falls_back_to_common_windows_location(monkeypatch) -> None:
    monkeypatch.setattr("services.ocr_service.shutil.which", lambda _: None)
    monkeypatch.setattr(Path, "exists", lambda self: str(self) == "C:\\Program Files\\Tesseract-OCR\\tesseract.exe")

    resolved = TesseractPyMuPDFOCRService._resolve_tesseract_cmd(None)

    assert resolved == "C:\\Program Files\\Tesseract-OCR\\tesseract.exe"