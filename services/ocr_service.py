from __future__ import annotations

import io
import shutil
from pathlib import Path
from typing import Any

from core.entities import OCRPage, OCRResult
from interfaces.ocr import OCRService

try:
    import fitz  # type: ignore
except Exception:  # pragma: no cover
    fitz = None

try:
    import pytesseract  # type: ignore
except Exception:  # pragma: no cover
    pytesseract = None

try:
    from PIL import Image  # type: ignore
except Exception:  # pragma: no cover
    Image = None

try:
    from PIL import ImageOps  # type: ignore
except Exception:  # pragma: no cover
    ImageOps = None

import io


class TesseractPyMuPDFOCRService(OCRService):
    """OCR service backed by PyMuPDF and Tesseract."""

    _OCR_DATA_CONFIG = "--psm 6"
    _OCR_STRING_CONFIG = "--psm 6"

    def __init__(self, ocr_lang: str = "heb+eng", tesseract_cmd: str | None = None) -> None:
        self.ocr_lang = ocr_lang
        self.tesseract_cmd = self._resolve_tesseract_cmd(tesseract_cmd)
        if self.tesseract_cmd and pytesseract is not None:
            pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd

    def extract(self, pdf_path: str) -> OCRResult:
        """Extract text with layout metadata from the given PDF path."""
        if fitz is None:
            raise RuntimeError("PyMuPDF is not installed. Install package 'pymupdf'.")

        input_path = Path(pdf_path)
        if not input_path.exists():
            raise FileNotFoundError(f"PDF file does not exist: {input_path}")

        pages: list[OCRPage] = []
        try:
            with fitz.open(input_path) as doc:
                for page in doc:
                    text = self._extract_rows_from_blocks(page)
                    if len(text) < 30:
                        text = self._fallback_ocr(page)
                    if not text.strip() and self._page_needs_ocr(page):
                        raise RuntimeError(
                            "Scanned PDF page has no extractable text and OCR is unavailable. "
                            "Install Tesseract or pass --tesseract-cmd."
                        )

                    blocks: list[dict[str, Any]] = []
                    for block in page.get_text("blocks"):
                        x0, y0, x1, y1, block_text = block[:5]
                        blocks.append(
                            {
                                "x0": x0,
                                "y0": y0,
                                "x1": x1,
                                "y1": y1,
                                "text": str(block_text).strip(),
                            }
                        )

                    pages.append(
                        OCRPage(
                            page_number=page.number + 1,
                            text=text,
                            width=float(page.rect.width),
                            height=float(page.rect.height),
                            blocks=blocks,
                        )
                    )

        except Exception as exc:
            raise RuntimeError(f"Failed OCR extraction for '{input_path}': {exc}") from exc

        full_text = "\n".join(page.text for page in pages)
        return OCRResult(
            full_text=full_text,
            pages=pages,
            metadata={
                "source_pdf": str(input_path),
                "page_count": len(pages),
            },
        )

    def _extract_rows_from_blocks(self, page: Any) -> str:
        """Reconstruct page text in visual row order using block positions.

        PyMuPDF's default ``get_text("text")`` returns blocks in PDF-stream
        order, which for multi-column / tabular PDFs means each column is
        emitted separately.  This method groups text blocks that share roughly
        the same Y coordinate (table row) and sorts them right-to-left (Hebrew
        reading order) within each row, producing one line per table row.
        """
        raw_blocks = page.get_text("blocks")  # (x0,y0,x1,y1,text,blk_no,type)

        # Keep only text blocks (type == 0) that are non-empty
        items: list[tuple[float, float, str]] = []  # (y0, x0, text)
        for blk in raw_blocks:
            if int(blk[6]) == 0:
                for sub_line in blk[4].split("\n"):
                    stripped = sub_line.strip()
                    if stripped:
                        items.append((blk[1], blk[0], stripped))

        if not items:
            return page.get_text("text").strip()

        # Group items sharing a similar Y into rows (tolerance = 8 px)
        tolerance = 8.0
        groups: list[tuple[float, list[tuple[float, str]]]] = []  # (avg_y, [(x0, text)])

        for y, x, text in sorted(items, key=lambda b: b[0]):
            for idx, (avg_y, cells) in enumerate(groups):
                if abs(avg_y - y) <= tolerance:
                    cells.append((x, text))
                    # Update running average Y
                    groups[idx] = ((avg_y * (len(cells) - 1) + y) / len(cells), cells)
                    break
            else:
                groups.append((y, [(x, text)]))

        # Sort rows top→bottom; within each row sort right→left (Hebrew RTL)
        lines: list[str] = []
        for _, cells in sorted(groups, key=lambda g: g[0]):
            cells.sort(key=lambda c: c[0], reverse=True)
            lines.append("  ".join(cell for _, cell in cells))

        return "\n".join(lines)

    def _fallback_ocr(self, page: Any) -> str:
        """Run image-based OCR with spatial row reconstruction via Tesseract.

        Uses ``image_to_data`` instead of ``image_to_string`` so that each
        word's bounding box is available.  Words are grouped by Y coordinate
        (with a pixel tolerance) and sorted right-to-left within each group,
        reproducing the visual row order of Hebrew/bidirectional tables.
        """
        if pytesseract is None or Image is None:
            return page.get_text("text").strip()

        try:
            pix = page.get_pixmap(matrix=fitz.Matrix(3, 3), alpha=False)
            image = Image.open(io.BytesIO(pix.tobytes("png")))
            image = self._preprocess_ocr_image(image)

            data = pytesseract.image_to_data(
                image,
                lang=self.ocr_lang,
                config=self._OCR_DATA_CONFIG,
                output_type=pytesseract.Output.DICT,
            )

            # Build (top, left, text) list filtering low-confidence results
            word_items: list[tuple[int, int, str]] = []
            for i in range(len(data["text"])):
                word = data["text"][i].strip()
                conf = int(data["conf"][i])
                if word and conf >= 0:
                    word_items.append((data["top"][i], data["left"][i], word))

            if not word_items:
                # Nothing survived confidence filter – plain string fallback
                return pytesseract.image_to_string(
                    image,
                    lang=self.ocr_lang,
                    config=self._OCR_STRING_CONFIG,
                ).strip()

            # Group words into rows by Y coordinate after 3x rasterization.
            tolerance = 28
            groups: list[tuple[float, list[tuple[int, str]]]] = []  # (avg_top, [(left, word)])

            for top, left, word in sorted(word_items, key=lambda w: w[0]):
                for idx, (avg_top, cells) in enumerate(groups):
                    if abs(avg_top - top) <= tolerance:
                        cells.append((left, word))
                        groups[idx] = ((avg_top * (len(cells) - 1) + top) / len(cells), cells)
                        break
                else:
                    groups.append((float(top), [(left, word)]))

            # Emit rows top→bottom, cells right→left (Hebrew RTL)
            lines: list[str] = []
            for _, cells in sorted(groups, key=lambda g: g[0]):
                cells.sort(key=lambda c: c[0], reverse=True)
                lines.append("  ".join(word for _, word in cells))

            return "\n".join(lines)

        except Exception:
            # Keep pipeline functional even when tesseract binary is missing.
            return page.get_text("text").strip()

    @staticmethod
    def _preprocess_ocr_image(image: Any) -> Any:
        if ImageOps is None:
            return image
        return ImageOps.autocontrast(ImageOps.grayscale(image))

    @staticmethod
    def _resolve_tesseract_cmd(explicit_cmd: str | None) -> str | None:
        if explicit_cmd:
            return explicit_cmd

        discovered = shutil.which("tesseract")
        if discovered:
            return discovered

        windows_candidates = (
            Path("C:/Program Files/Tesseract-OCR/tesseract.exe"),
            Path("C:/Program Files (x86)/Tesseract-OCR/tesseract.exe"),
        )
        for candidate in windows_candidates:
            if candidate.exists():
                return str(candidate)
        return None

    @staticmethod
    def _page_needs_ocr(page: Any) -> bool:
        return bool(page.get_images(full=True)) and not page.get_text("text").strip()
