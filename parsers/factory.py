from __future__ import annotations

from core.entities import ReportType
from interfaces.parser import ReportParser
from parsers.type_a_parser import TypeAReportParser
from parsers.type_b_parser import TypeBReportParser


class ParserFactory:
    """Factory for selecting parser strategy by report type."""

    def create(self, report_type: ReportType) -> ReportParser:
        if report_type == ReportType.TYPE_A:
            return TypeAReportParser()
        if report_type == ReportType.TYPE_B:
            return TypeBReportParser()
        raise ValueError(f"Unsupported report type for parser factory: {report_type}")
