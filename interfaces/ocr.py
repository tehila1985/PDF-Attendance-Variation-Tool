from __future__ import annotations

from abc import ABC, abstractmethod

from core.entities import OCRResult


class OCRService(ABC):
    """Contract for OCR extraction from attendance PDFs."""

    @abstractmethod
    def extract(self, pdf_path: str) -> OCRResult:
        """Extract normalized text and layout metadata from a PDF file."""
        raise NotImplementedError
