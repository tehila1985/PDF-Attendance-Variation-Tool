from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pypdfium2 as pdfium
import pytesseract


DEFAULT_TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


@dataclass(frozen=True)
class NormalizedBox:
    left: float
    top: float
    right: float
    bottom: float


class PdfOcrService:
    def __init__(self, tesseract_cmd: str = DEFAULT_TESSERACT_PATH, scale: float = 2.5):
        self._tesseract_cmd = tesseract_cmd
        self._scale = scale

    def extract_region_text(self, file_path: str, box: NormalizedBox, psm: int = 6, lang: str = "heb+eng") -> str:
        image = self.render_first_page(file_path)
        width, height = image.size
        crop_box = (
            int(width * box.left),
            int(height * box.top),
            int(width * box.right),
            int(height * box.bottom),
        )
        crop = image.crop(crop_box)
        pytesseract.pytesseract.tesseract_cmd = self._tesseract_cmd
        return pytesseract.image_to_string(crop, lang=lang, config=f"--psm {psm}")

    def render_first_page(self, file_path: str):
        pdf = pdfium.PdfDocument(str(Path(file_path)))
        page = pdf[0]
        return page.render(scale=self._scale).to_pil()