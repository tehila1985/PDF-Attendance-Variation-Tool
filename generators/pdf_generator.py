from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from core.entities import AttendanceReport, AttendanceRow, ReportType
from interfaces.generator import PDFGenerator
from interfaces.renderer import BaseRenderer

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.enums import TA_RIGHT
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
except Exception:  # pragma: no cover
    colors = None
    A4 = None
    TA_RIGHT = None
    ParagraphStyle = None
    getSampleStyleSheet = None
    pdfmetrics = None
    TTFont = None
    Paragraph = None
    SimpleDocTemplate = None
    Spacer = None
    Table = None
    TableStyle = None

_DEFAULT_FONT_NAME = "Helvetica"
_DEFAULT_BOLD_FONT_NAME = "Helvetica-Bold"
_UNICODE_FONT_NAME = "ArialUnicodeFallback"
_UNICODE_BOLD_FONT_NAME = "ArialUnicodeFallback-Bold"
_HEBREW_PATTERN = re.compile(r"[\u0590-\u05FF]")


class ReportLabPDFGenerator(PDFGenerator, BaseRenderer):
    """Generate a clean attendance PDF while preserving source column structure.

    Implements both the legacy ``PDFGenerator`` interface and the new
    ``BaseRenderer`` interface so it can be used in either pipeline.
    """

    def generate(self, original_pdf_path: str, output_pdf_path: str, report: AttendanceReport) -> None:
        if SimpleDocTemplate is None:
            raise RuntimeError("reportlab is not installed. Install package 'reportlab'.")

        font_name, bold_font_name = self._resolve_fonts()

        output = Path(output_pdf_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        layout_metadata = report.metadata.get("layout_metadata", {})
        columns = self._columns(layout_metadata, report.report_type)
        headers = [self._display_text(header) for header in self._headers(layout_metadata, columns)]

        rows = [headers]
        for row in report.rows:
            rows.append([self._display_text(self._extract_value(row, column)) for column in columns])

        rows.append(["" for _ in columns])
        rows.append(self._monthly_total_row(columns, self._display_text(report.monthly_total_hours or "00:00")))

        doc = SimpleDocTemplate(str(output), pagesize=A4)
        styles = getSampleStyleSheet()
        title_style = self._build_paragraph_style(styles["Title"], bold_font_name)
        body_style = self._build_paragraph_style(styles["Normal"], font_name)
        story: list[Any] = [
            Paragraph("Attendance Report Variation", title_style),
            Spacer(1, 10),
            Paragraph(f"Source PDF: {Path(original_pdf_path).name}", body_style),
            Paragraph(f"Employee: {self._display_text(report.employee_name or 'N/A')}", body_style),
            Paragraph(f"Month: {report.month or 'N/A'}", body_style),
            Spacer(1, 14),
        ]

        table = Table(rows, repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("FONTNAME", (0, 0), (-1, 0), bold_font_name),
                    ("FONTNAME", (0, 1), (-1, -1), font_name),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                ]
            )
        )
        story.append(table)

        try:
            doc.build(story)
        except Exception as exc:
            raise RuntimeError(f"PDF generation failed for '{output}': {exc}") from exc

    @staticmethod
    def _columns(layout_metadata: dict[str, Any], report_type: ReportType) -> list[str]:
        columns = layout_metadata.get("columns")
        if isinstance(columns, list) and columns:
            return [str(col) for col in columns]

        if report_type == ReportType.TYPE_B:
            return ["date", "day", "location", "start_time", "end_time", "break_duration", "total_hours", "percentage_bracket"]
        return ["date", "day", "start_time", "end_time", "total_hours"]

    @staticmethod
    def _headers(layout_metadata: dict[str, Any], columns: list[str]) -> list[str]:
        headers = layout_metadata.get("headers")
        if isinstance(headers, list) and len(headers) == len(columns):
            return [str(h) for h in headers]
        return [col.replace("_", " ").title() for col in columns]

    @staticmethod
    def _extract_value(row: AttendanceRow, column: str) -> str:
        if column == "date":
            return row.date.isoformat() if row.date else ""
        value = getattr(row, column, None)
        return "" if value is None else str(value)

    @staticmethod
    def _monthly_total_row(columns: list[str], monthly_total: str) -> list[str]:
        row = ["" for _ in columns]
        if "total_hours" in columns:
            row[columns.index("total_hours")] = monthly_total
        if columns:
            row[0] = "Monthly Total"
        return row

    @staticmethod
    def _display_text(value: str) -> str:
        if not value or not _HEBREW_PATTERN.search(value):
            return value
        return value[::-1]

    @staticmethod
    def _resolve_fonts() -> tuple[str, str]:
        if pdfmetrics is None or TTFont is None:
            return _DEFAULT_FONT_NAME, _DEFAULT_BOLD_FONT_NAME

        regular_path = Path("C:/Windows/Fonts/arial.ttf")
        bold_path = Path("C:/Windows/Fonts/arialbd.ttf")

        if regular_path.exists() and _UNICODE_FONT_NAME not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(_UNICODE_FONT_NAME, str(regular_path)))
        if bold_path.exists() and _UNICODE_BOLD_FONT_NAME not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(_UNICODE_BOLD_FONT_NAME, str(bold_path)))

        has_regular = _UNICODE_FONT_NAME in pdfmetrics.getRegisteredFontNames()
        has_bold = _UNICODE_BOLD_FONT_NAME in pdfmetrics.getRegisteredFontNames()
        if has_regular and has_bold:
            return _UNICODE_FONT_NAME, _UNICODE_BOLD_FONT_NAME
        return _DEFAULT_FONT_NAME, _DEFAULT_BOLD_FONT_NAME

    @staticmethod
    def _build_paragraph_style(base_style: Any, font_name: str) -> Any:
        if ParagraphStyle is None or TA_RIGHT is None:
            return base_style
        return ParagraphStyle(
            name=f"{base_style.name}-{font_name}",
            parent=base_style,
            fontName=font_name,
            alignment=TA_RIGHT,
        )

    # ---- BaseRenderer interface ----
    def render(self, report: AttendanceReport, source_path: str, output_path: str) -> None:
        """BaseRenderer entry-point: delegates to generate()."""
        self.generate(
            original_pdf_path=source_path,
            output_pdf_path=output_path,
            report=report,
        )


# Convenient alias used by the new pipeline.
PdfRenderer = ReportLabPDFGenerator
