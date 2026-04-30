from __future__ import annotations

from abc import ABC, abstractmethod

from core.entities import AttendanceReport, OCRResult


class ReportParser(ABC):
    """Contract for converting OCR output to structured domain entities."""

    @abstractmethod
    def parse(self, ocr_result: OCRResult) -> AttendanceReport:
        """Parse OCR output into an attendance report model."""
        raise NotImplementedError
