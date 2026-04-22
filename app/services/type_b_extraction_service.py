from __future__ import annotations

import re
from datetime import datetime

from app.entities import AttendanceReport, AttendanceRow
from app.logic.ocr_fallback import extract_ocr_text_from_first_page, extract_rows_type_b
from app.services.pdf_ocr_service import NormalizedBox, PdfOcrService


TYPE_B_LEFT_BOX = NormalizedBox(0.13, 0.10, 0.53, 0.48)
TYPE_B_RIGHT_BOX = NormalizedBox(0.47, 0.10, 0.89, 0.48)


class TypeBExtractionService:
    def __init__(self, ocr_service: PdfOcrService | None = None):
        self._ocr = ocr_service or PdfOcrService()

    def extract(self, file_path: str) -> AttendanceReport:
        left_text = self._ocr.extract_region_text(file_path, TYPE_B_LEFT_BOX)
        right_text = self._ocr.extract_region_text(file_path, TYPE_B_RIGHT_BOX)

        rows = self._parse_rows(left_text, right_text)
        if not rows:
            rows = self._fallback_rows(file_path)

        report = AttendanceReport(
            report_type="TypeB",
            employee_name="עובד",
            month_year=_infer_month_year(rows),
            rows=rows,
        )
        report.total_monthly_hours = round(sum(row.total_hours for row in rows), 2)
        return report

    def _fallback_rows(self, file_path: str) -> list[AttendanceRow]:
        text = extract_ocr_text_from_first_page(file_path)
        raw_rows = extract_rows_type_b(text)

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
                    overtime_shabbat=round(float(item.get("overtime_shabbat", 0.0) or 0.0), 2),
                    overtime_125=round(float(item.get("overtime_125", 0.0) or 0.0), 2),
                    overtime_150=round(float(item.get("overtime_150", 0.0) or 0.0), 2),
                )
            )

        return sorted(rows, key=lambda row: datetime.strptime(row.date, "%d/%m/%Y"))

    def _parse_rows(self, left_text: str, right_text: str) -> list[AttendanceRow]:
        left_lines = [line for line in (_normalize_line(item) for item in left_text.splitlines()) if _is_data_line_left(line)]
        right_lines = [line for line in (_normalize_line(item) for item in right_text.splitlines()) if _is_data_line_right(line)]

        rows: list[AttendanceRow] = []
        for left_line, right_line in zip(left_lines, right_lines):
            numeric_tokens = [_parse_decimal_token(token) for token in re.findall(r"\d+(?:[\.,]\d+)?", left_line)]
            numeric_tokens = [token for token in numeric_tokens if token is not None]
            time_tokens = re.findall(r"\d{1,2}:\d{2}", right_line)
            date_match = re.search(r"\d{1,2}/\d{1,2}/\d{4}", right_line)

            if len(numeric_tokens) < 5 or len(time_tokens) < 3 or not date_match:
                continue

            date_value = date_match.group()
            shabbat_150 = numeric_tokens[0]
            overtime_150 = numeric_tokens[1]
            overtime_125 = numeric_tokens[2]
            regular_100 = numeric_tokens[3]
            total_hours = numeric_tokens[4]
            break_time = time_tokens[0]
            exit_time = time_tokens[1]
            entry_time = time_tokens[2]

            row = AttendanceRow(
                date=date_value,
                day_of_week=_hebrew_day_name(date_value),
                start_time=entry_time,
                end_time=exit_time,
                total_hours=round(total_hours, 2),
                comments=f"break={break_time}; regular={regular_100:.2f}",
                overtime_shabbat=round(shabbat_150, 2),
                overtime_125=round(overtime_125, 2),
                overtime_150=round(overtime_150, 2),
            )
            rows.append(row)

        return sorted(rows, key=lambda row: datetime.strptime(row.date, "%d/%m/%Y"))


def _normalize_line(value: str) -> str:
    line = value.replace("�", " ")
    line = re.sub(r"\s+", " ", line).strip()
    return line


def _is_data_line_left(line: str) -> bool:
    return line.count("00:30") == 1 and bool(re.search(r"\d", line))


def _is_data_line_right(line: str) -> bool:
    return bool(re.search(r"\d{1,2}/\d{1,2}/\d{4}", line)) and len(re.findall(r"\d{1,2}:\d{2}", line)) >= 3


def _parse_decimal_token(token: str) -> float | None:
    normalized = token.replace(",", ".")
    if normalized.isdigit() and len(normalized) == 3:
        normalized = f"{normalized[0]}.{normalized[1:]}"
    try:
        return float(normalized)
    except ValueError:
        return None


def _hebrew_day_name(date_value: str) -> str:
    parsed = datetime.strptime(date_value, "%d/%m/%Y")
    names = ["שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת", "ראשון"]
    return names[parsed.weekday()]


def _infer_month_year(rows: list[AttendanceRow]) -> str:
    if not rows:
        return "Unknown"
    parsed = datetime.strptime(rows[0].date, "%d/%m/%Y")
    return parsed.strftime("%m/%Y")