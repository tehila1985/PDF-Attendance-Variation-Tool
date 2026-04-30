from __future__ import annotations

from abc import abstractmethod

from core.entities import AttendanceReport, AttendanceRow, OCRResult, ReportType
from interfaces.parser import ReportParser


class BaseParser(ReportParser):
    """Template Method base class for attendance report parsers.

    The ``parse()`` method defines the fixed skeleton of the parsing algorithm.
    Subclasses customise behaviour by overriding the four *hook* methods only;
    they must NOT override ``parse()`` itself.

    Hook methods
    ------------
    _get_report_type()  – return the ReportType produced by this parser.
    _is_header_line()   – return True if *line* is a table header to skip.
    _parse_row()        – try to produce an AttendanceRow from *line*; return
                          None when the line does not contain row data.
    _parse_summary()    – extract report-level metadata (employee name, month).
    """

    def parse(self, ocr_result: OCRResult) -> AttendanceReport:
        """Skeleton algorithm – do not override in subclasses."""
        rows: list[AttendanceRow] = []

        for line in ocr_result.full_text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if self._is_header_line(stripped):
                continue
            row = self._parse_row(stripped)
            if row is not None:
                rows.append(row)

        if not rows:
            raise ValueError(f"No attendance rows parsed by {self.__class__.__name__}.")

        summary = self._parse_summary(ocr_result.full_text)
        report = AttendanceReport(
            report_type=self._get_report_type(),
            employee_name=summary.get("employee_name"),
            month=summary.get("month"),
            rows=rows,
            metadata={"layout_metadata": ocr_result.metadata.get("layout_metadata", {})},
        )
        report.recompute_monthly_total()
        return report

    @abstractmethod
    def _get_report_type(self) -> ReportType:
        """Return the ReportType this parser produces."""
        raise NotImplementedError

    @abstractmethod
    def _is_header_line(self, line: str) -> bool:
        """Return True if *line* is a table header that should be skipped."""
        raise NotImplementedError

    @abstractmethod
    def _parse_row(self, line: str) -> AttendanceRow | None:
        """Attempt to parse a single data row; return None on no-match."""
        raise NotImplementedError

    @abstractmethod
    def _parse_summary(self, full_text: str) -> dict[str, str | None]:
        """Extract report-level metadata from the full OCR text."""
        raise NotImplementedError
