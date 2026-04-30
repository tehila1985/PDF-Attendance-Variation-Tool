from __future__ import annotations

import re

from core.entities import AttendanceRow, ReportType, parse_date
from parsers.base_parser import BaseParser
from parsers.common import DATE_PATTERN, DAY_PATTERN, PERCENT_PATTERN, TIME_PATTERN, extract_employee_name, extract_month, normalize_hhmm

_HEADER_KEYWORDS: frozenset[str] = frozenset(
    ("\u05e9\u05e2\u05ea \u05db\u05e0\u05d9\u05e1\u05d4", "\u05e9\u05e2\u05ea \u05d9\u05e6\u05d9\u05d0\u05d4", "\u05ea\u05d0\u05e8\u05d9\u05da", "\u05d9\u05d5\u05dd", "date", "entry", "exit")
)
_NUMERIC_TOKEN_PATTERN = re.compile(r"\b\d+(?:[.,]\d+)?%?\b")
_DECIMAL_VALUE_PATTERN = re.compile(r"\b\d{1,2}[.,]\d{1,2}\b")


class TypeAReportParser(BaseParser):
    """Type A parser \u2013 hook implementations for the Template Method skeleton.

    Type A reports contain entry/exit times and total hours per day.
    No location, break, or percentage columns are expected.
    """

    def _get_report_type(self) -> ReportType:
        return ReportType.TYPE_A

    def _is_header_line(self, line: str) -> bool:
        return any(kw in line for kw in _HEADER_KEYWORDS)

    def _parse_row(self, line: str) -> AttendanceRow | None:
        date_match = DATE_PATTERN.search(line)
        if not date_match:
            return None

        if any(keyword in line for keyword in ("מקום", "הפסקה")) or PERCENT_PATTERN.search(line):
            return None

        times = [normalize_hhmm(t) for t in TIME_PATTERN.findall(line)]
        if len(times) < 2:
            return None
        if len(times) > 3:
            return None

        extra_numeric = self._remaining_numeric_tokens(line)
        if len(extra_numeric) > 1:
            return None
        if extra_numeric and not _DECIMAL_VALUE_PATTERN.fullmatch(extra_numeric[0]):
            return None

        day_match = DAY_PATTERN.search(line)
        total = times[2] if len(times) >= 3 else None

        row = AttendanceRow(
            date=parse_date(date_match.group(1)),
            day=day_match.group(1) if day_match else None,
            start_time=times[0],
            end_time=times[1],
            total_hours=total,
            raw_line=line,
        )
        if not row.total_hours:
            row.recompute_total_hours()
        return row

    def _parse_summary(self, full_text: str) -> dict[str, str | None]:
        return {
            "employee_name": extract_employee_name(full_text),
            "month": extract_month(full_text),
        }

    @staticmethod
    def _remaining_numeric_tokens(line: str) -> list[str]:
        scrubbed = DATE_PATTERN.sub(" ", line)
        scrubbed = TIME_PATTERN.sub(" ", scrubbed)
        return _NUMERIC_TOKEN_PATTERN.findall(scrubbed)
