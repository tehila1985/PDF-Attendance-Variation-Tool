from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from enum import Enum
from typing import Any


class ReportType(str, Enum):
    """Supported attendance report formats."""

    TYPE_A = "type_a"
    TYPE_B = "type_b"
    UNKNOWN = "unknown"


@dataclass(slots=True)
class AttendanceRow:
    """A single attendance row extracted from the source report."""

    date: date | None
    day: str | None
    start_time: str | None
    end_time: str | None
    total_hours: str | None
    location: str | None = None
    percentage_bracket: str | None = None
    break_duration: str | None = None
    # --- Type B enriched fields ---
    break_minutes: int | None = None
    overtime_125_hours: str | None = None
    overtime_150_hours: str | None = None
    # --------------------------------
    raw_line: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def start_as_time(self) -> time | None:
        return parse_time(self.start_time)

    def end_as_time(self) -> time | None:
        return parse_time(self.end_time)

    def recompute_total_hours(self) -> None:
        """Recalculate row duration as HH:MM based on start/end times, minus any break."""
        start_t = self.start_as_time()
        end_t = self.end_as_time()
        if not start_t or not end_t:
            return

        start_dt = datetime.combine(datetime.today(), start_t)
        end_dt = datetime.combine(datetime.today(), end_t)
        if end_dt <= start_dt:
            end_dt += timedelta(days=1)

        duration = end_dt - start_dt
        total_minutes = int(duration.total_seconds() // 60)
        if self.break_minutes:
            total_minutes = max(0, total_minutes - self.break_minutes)
        self.total_hours = minutes_to_hhmm(total_minutes)


@dataclass(slots=True)
class AttendanceReport:
    """Aggregate report object containing all parsed rows and metadata."""

    report_type: ReportType
    employee_name: str | None
    month: str | None
    rows: list[AttendanceRow]
    monthly_total_hours: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def recompute_monthly_total(self) -> None:
        """Recompute total monthly hours from row totals."""
        total_minutes = 0
        for row in self.rows:
            minutes = hhmm_to_minutes(row.total_hours)
            if minutes is not None:
                total_minutes += minutes

        self.monthly_total_hours = minutes_to_hhmm(total_minutes)


@dataclass(slots=True)
class OCRPage:
    """OCR output for a single page."""

    page_number: int
    text: str
    width: float | None = None
    height: float | None = None
    blocks: list[dict[str, Any]] = field(default_factory=list)


@dataclass(slots=True)
class OCRResult:
    """Normalized OCR result for downstream processing."""

    full_text: str
    pages: list[OCRPage]
    metadata: dict[str, Any] = field(default_factory=dict)


def parse_time(value: str | None) -> time | None:
    """Parse time values in HH:MM format."""
    if not value:
        return None

    stripped = value.strip()
    for fmt in ("%H:%M", "%H.%M"):
        try:
            return datetime.strptime(stripped, fmt).time()
        except ValueError:
            continue
    return None


def parse_date(value: str | None) -> date | None:
    """Parse date values in common local formats."""
    if not value:
        return None

    stripped = value.strip()
    for fmt in ("%d/%m/%Y", "%d.%m.%Y", "%d/%m/%y", "%d.%m.%y"):
        try:
            parsed = datetime.strptime(stripped, fmt).date()
            if parsed.year < 100:
                return parsed.replace(year=2000 + parsed.year)
            return parsed
        except ValueError:
            continue
    return None


def hhmm_to_minutes(value: str | None) -> int | None:
    """Convert HH:MM to total minutes."""
    if not value:
        return None

    parts = value.strip().split(":")
    if len(parts) != 2:
        return None

    try:
        hours = int(parts[0])
        minutes = int(parts[1])
        if minutes < 0 or minutes >= 60 or hours < 0:
            return None
        return hours * 60 + minutes
    except ValueError:
        return None


def minutes_to_hhmm(total_minutes: int) -> str:
    """Convert minutes to HH:MM format."""
    hours, minutes = divmod(max(total_minutes, 0), 60)
    return f"{hours:02d}:{minutes:02d}"


def timedelta_to_hhmm(value: timedelta) -> str:
    """Convert timedelta to HH:MM representation."""
    total_minutes = int(value.total_seconds() // 60)
    return minutes_to_hhmm(total_minutes)
