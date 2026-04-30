from __future__ import annotations

import re

from core.entities import AttendanceRow, ReportType, hhmm_to_minutes, parse_date
from parsers.base_parser import BaseParser
from parsers.common import (
    DATE_PATTERN,
    DAY_PATTERN,
    PERCENT_PATTERN,
    TIME_PATTERN,
    extract_employee_name,
    extract_month,
    normalize_hhmm,
)

_LOCATION_PATTERN = re.compile(r"מקום\s*[:\-]?\s*([^\n]+)")
_BREAK_PATTERN = re.compile(r"הפסקה\s*[:\-]?\s*((?:[01]?\d|2[0-3])[:.][0-5]\d)")
_OVERTIME_125_PATTERN = re.compile(r"125%\s*[:\-]?\s*((?:[01]?\d|2[0-3]):[0-5]\d)")
_OVERTIME_150_PATTERN = re.compile(r"150%\s*[:\-]?\s*((?:[01]?\d|2[0-3]):[0-5]\d)")
_HEADER_KEYWORDS: frozenset[str] = frozenset(("מקום", "הפסקה", "תאריך", "יום"))


class TypeBReportParser(BaseParser):
    """Type B parser – hook implementations for the Template Method skeleton.

    Type B reports add location, break duration, and percentage-bracket columns
    (100 %, 125 %, 150 %) on top of the standard entry/exit fields.
    """

    def _get_report_type(self) -> ReportType:
        return ReportType.TYPE_B

    def _is_header_line(self, line: str) -> bool:
        return any(kw in line for kw in _HEADER_KEYWORDS) and not DATE_PATTERN.search(line)

    def _parse_row(self, line: str) -> AttendanceRow | None:
        date_match = DATE_PATTERN.search(line)
        if not date_match:
            return None

        day_match = DAY_PATTERN.search(line)
        percent_match = PERCENT_PATTERN.search(line)
        break_match = _BREAK_PATTERN.search(line)
        location_match = _LOCATION_PATTERN.search(line)
        ot125_match = _OVERTIME_125_PATTERN.search(line)
        ot150_match = _OVERTIME_150_PATTERN.search(line)

        location: str | None = None
        if location_match:
            location = location_match.group(1).strip()
        elif "מקום" in line:
            location = line.split("מקום", maxsplit=1)[-1].strip()[:25]

        break_duration = normalize_hhmm(break_match.group(1)) if break_match else None
        break_minutes: int | None = hhmm_to_minutes(break_duration) if break_duration else None

        times = [normalize_hhmm(t) for t in TIME_PATTERN.findall(line)]
        if break_duration and break_duration in times:
            times.remove(break_duration)

        # Heuristic: when no keyword-based break was found, the third time
        # value in a TYPE-B row is almost always the break duration (≤ 90 min).
        # Decimal-hours columns (7.50, 0.00) are excluded by TIME_PATTERN.
        if break_duration is None and len(times) >= 3:
            candidate_mins = hhmm_to_minutes(times[2])
            if candidate_mins is not None and 0 < candidate_mins <= 90:
                break_duration = times[2]
                break_minutes = candidate_mins
                times = [times[0], times[1]] + times[3:]

        if len(times) < 2:
            return None

        row = AttendanceRow(
            date=parse_date(date_match.group(1)),
            day=day_match.group(1) if day_match else None,
            location=location,
            start_time=times[0],
            end_time=times[1],
            break_duration=break_duration,
            break_minutes=break_minutes,
            total_hours=None,  # always recompute from start/end/break
            percentage_bracket=percent_match.group(1) if percent_match else None,
            overtime_125_hours=ot125_match.group(1) if ot125_match else None,
            overtime_150_hours=ot150_match.group(1) if ot150_match else None,
            raw_line=line,
        )
        row.recompute_total_hours()
        return row

    def _parse_summary(self, full_text: str) -> dict[str, str | None]:
        return {
            "employee_name": extract_employee_name(full_text),
            "month": extract_month(full_text),
        }
