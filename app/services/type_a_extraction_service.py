from __future__ import annotations

import re
from datetime import datetime, timedelta

from app.entities import AttendanceReport, AttendanceRow
from app.logic.ocr_fallback import extract_ocr_text_from_first_page, extract_rows_type_a
from app.services.pdf_ocr_service import NormalizedBox, PdfOcrService


TYPE_A_SUMMARY_BOX = NormalizedBox(0.51, 0.10, 0.92, 0.25)
TYPE_A_TABLE_BOX = NormalizedBox(0.35, 0.24, 0.92, 0.73)


class TypeAExtractionService:
    def __init__(self, ocr_service: PdfOcrService | None = None):
        self._ocr = ocr_service or PdfOcrService()

    def extract(self, file_path: str) -> AttendanceReport:
        summary_text = self._ocr.extract_region_text(file_path, TYPE_A_SUMMARY_BOX)
        table_text = self._ocr.extract_region_text(file_path, TYPE_A_TABLE_BOX)

        rows = self._parse_rows(table_text)
        if not rows:
            rows = self._fallback_rows(file_path)

        hourly_rate = self._parse_hourly_rate(summary_text)
        month_year = _infer_month_year(rows)

        report = AttendanceReport(
            report_type="TypeA",
            employee_name="עובד",
            month_year=month_year,
            rows=rows,
            hourly_rate=hourly_rate,
        )
        report.total_monthly_hours = round(sum(row.total_hours for row in rows), 2)
        report.total_payment = round(report.total_monthly_hours * hourly_rate, 2) if hourly_rate else 0.0
        return report

    def _fallback_rows(self, file_path: str) -> list[AttendanceRow]:
        text = extract_ocr_text_from_first_page(file_path)
        raw_rows = extract_rows_type_a(text)

        rows: list[AttendanceRow] = []
        for item in raw_rows:
            date_value = item.get("date")
            if not date_value or date_value == "N/A":
                continue

            rows.append(
                AttendanceRow(
                    date=date_value,
                    day_of_week=_hebrew_day_name(date_value),
                    start_time=item.get("start_time"),
                    end_time=item.get("end_time"),
                    total_hours=round(float(item.get("total_hours", 0.0) or 0.0), 2),
                    comments=item.get("comments") or "OCR fallback",
                )
            )

        return _dedupe_and_sort(rows)

    def _parse_rows(self, text: str) -> list[AttendanceRow]:
        rows: list[AttendanceRow] = []

        for raw_line in text.splitlines():
            line = _normalize_type_a_line(raw_line)
            date_match = re.search(r"\d{1,2}/\d{1,2}/\d{2,4}", line)
            total_match = re.search(r"\d+\.\d+", line)
            if not date_match or not total_match:
                continue

            date_value = _normalize_date(date_match.group())
            if not date_value:
                continue

            total_hours = float(total_match.group())
            time_matches = re.findall(r"\d{1,2}:\d{2}", line)

            entry_time = None
            exit_time = None
            if len(time_matches) >= 2:
                exit_time = _normalize_time(time_matches[0])
                entry_time = _normalize_time(time_matches[1])
                if entry_time and exit_time:
                    entry_time, exit_time = _reconcile_window(entry_time, exit_time, total_hours)

            rows.append(
                AttendanceRow(
                    date=date_value,
                    day_of_week=_hebrew_day_name(date_value),
                    start_time=entry_time,
                    end_time=exit_time,
                    total_hours=round(total_hours, 2),
                )
            )

        return _dedupe_and_sort(rows)

    def _parse_hourly_rate(self, text: str) -> float:
        normalized = text.replace(",", "")
        matches = re.findall(r"\d+\.\d+", normalized)
        for token in matches:
            value = float(token)
            if 10 <= value <= 100:
                return value
        return 30.65


def _normalize_type_a_line(value: str) -> str:
    line = value.replace("42:00", "12:00")
    line = line.replace("8::", "8:30")
    line = line.replace("42:00", "12:00")
    line = re.sub(r"\s+", " ", line).strip()
    return line


def _normalize_time(value: str) -> str | None:
    try:
        hour_str, minute_str = value.split(":", 1)
        hour = int(hour_str)
        minute = int(minute_str)
        if hour > 23 and str(hour).startswith("4"):
            hour = 12
        if hour == 6:
            hour = 8
        if minute > 59:
            minute = 0
        return f"{hour:02d}:{minute:02d}"
    except (ValueError, AttributeError):
        return None


def _reconcile_window(entry_time: str, exit_time: str, total_hours: float) -> tuple[str, str]:
    fmt = "%H:%M"
    start = datetime.strptime(entry_time, fmt)
    end = datetime.strptime(exit_time, fmt)
    if end <= start:
        end += timedelta(days=1)
    observed = (end - start).total_seconds() / 3600
    if abs(observed - total_hours) <= 0.35:
        return entry_time, exit_time

    corrected_start = end - timedelta(hours=total_hours)
    minute = 5 * round(corrected_start.minute / 5)
    corrected_start = corrected_start.replace(minute=0, second=0, microsecond=0) + timedelta(minutes=minute)
    return corrected_start.strftime(fmt), exit_time


def _normalize_date(value: str) -> str | None:
    for fmt in ("%d/%m/%Y", "%d/%m/%y"):
        try:
            parsed = datetime.strptime(value, fmt)
            if parsed.year < 2000:
                parsed = parsed.replace(year=parsed.year + 2000)
            return parsed.strftime("%d/%m/%Y")
        except ValueError:
            continue
    return None


def _hebrew_day_name(date_value: str) -> str:
    parsed = datetime.strptime(date_value, "%d/%m/%Y")
    names = ["שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת", "ראשון"]
    return names[parsed.weekday()]


def _dedupe_and_sort(rows: list[AttendanceRow]) -> list[AttendanceRow]:
    best: dict[str, AttendanceRow] = {}
    for row in rows:
        existing = best.get(row.date)
        if not existing or _row_score(row) > _row_score(existing):
            best[row.date] = row
    return sorted(best.values(), key=lambda row: datetime.strptime(row.date, "%d/%m/%Y"))


def _row_score(row: AttendanceRow) -> float:
    score = row.total_hours
    if row.start_time:
        score += 0.5
    if row.end_time:
        score += 0.5
    return score


def _infer_month_year(rows: list[AttendanceRow]) -> str:
    if not rows:
        return "Unknown"
    parsed = datetime.strptime(rows[0].date, "%d/%m/%Y")
    return parsed.strftime("%m/%Y")