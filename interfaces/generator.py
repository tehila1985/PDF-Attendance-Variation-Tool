from __future__ import annotations

from abc import ABC, abstractmethod

from core.entities import AttendanceReport


class PDFGenerator(ABC):
    """Contract for generating an output PDF report from parsed entities."""

    @abstractmethod
    def generate(self, original_pdf_path: str, output_pdf_path: str, report: AttendanceReport) -> None:
        """Generate a PDF using source layout metadata and modified values."""
        raise NotImplementedError
