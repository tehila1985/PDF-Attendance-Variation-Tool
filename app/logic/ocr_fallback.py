import re
from datetime import datetime, timedelta
from typing import Any

import pypdfium2 as pdfium
import pytesseract


DEFAULT_TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


def extract_ocr_text_from_first_page(file_path: str) -> str:
    pytesseract.pytesseract.tesseract_cmd = DEFAULT_TESSERACT_PATH

    pdf = pdfium.PdfDocument(file_path)
    page = pdf[0]
    image = page.render(scale=3).to_pil()

    text = pytesseract.image_to_string(image, lang="eng+heb", config="--psm 6")
    return _normalize_ocr_text(text)


def extract_rows_from_ocr_text(text: str) -> list[dict[str, Any]]:
    date_pattern = r"\b(?:[0-2]?\d|3[01])/(?:0?\d|1[0-2])(?:/\d{2,4})?\b"
    time_pattern = r"\b(?:[01]?\d|2[0-3]):[0-5]\d\b"

    rows: list[dict[str, Any]] = []
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    for line in lines:
        dates = re.findall(date_pattern, line)
        times = re.findall(time_pattern, line)

        if dates and len(times) >= 2:
            start_time = times[0]
            end_time = times[1]
            total_hours = _hours_between(start_time, end_time)

            # OCR on RTL tables often returns a duration cell as a time-like token.
            # If duration is clearly unrealistic as a work shift, keep only a parsed duration.
            if total_hours > 16:
                total_hours = _duration_to_hours(end_time)
                start_time = None
                end_time = None

            row = {
                "date": dates[-1],
                "day_of_week": "",
                "start_time": start_time,
                "end_time": end_time,
                "total_hours": total_hours,
                "comments": line,
            }
            rows.append(row)

    if rows:
        return rows

    dates = re.findall(date_pattern, text)
    times = re.findall(time_pattern, text)
    pair_count = min(len(dates), len(times) // 2)

    for i in range(pair_count):
        start_time = times[i * 2]
        end_time = times[i * 2 + 1]
        rows.append(
            {
                "date": dates[i],
                "day_of_week": "",
                "start_time": start_time,
                "end_time": end_time,
                "total_hours": _hours_between(start_time, end_time),
                "comments": "OCR fallback row",
            }
        )

    if rows:
        return rows

    if text.strip():
        rows.append(
            {
                "date": "N/A",
                "day_of_week": "",
                "start_time": None,
                "end_time": None,
                "total_hours": 0.0,
                "comments": "OCR extracted text but no structured rows found",
            }
        )

    return rows


def extract_rows_type_a(text: str) -> list[dict[str, Any]]:
    rows = []
    date_pattern = r"\b(?:[0-2]?\d|3[01])/(?:0?\d|1[0-2])(?:/\d{2,4})?\b"
    time_pattern = r"\b(?:[01]?\d|2[0-3]):[0-5]\d\b"

    for line in [line.strip() for line in text.splitlines() if line.strip()]:
        dates = re.findall(date_pattern, line)
        times = re.findall(time_pattern, line)

        if not dates:
            continue

        total_from_duration = _extract_duration_from_line(line, target=8.5)

        start_time = times[0] if len(times) >= 1 else None
        end_time = times[1] if len(times) >= 2 else None

        if _is_break_or_noise_time(start_time):
            start_time = None
            end_time = None

        if _is_break_or_noise_time(start_time):
            start_time = None
            end_time = None

        if start_time and end_time:
            total_hours = _hours_between(start_time, end_time)
            if total_hours > 12:
                total_hours = total_from_duration if total_from_duration is not None else _duration_to_hours(end_time)
                start_time = None
                end_time = None
        else:
            total_hours = total_from_duration if total_from_duration is not None else 0.0

        if total_hours <= 0 and total_from_duration is not None:
            total_hours = total_from_duration

        normalized_date = _normalize_date(dates[-1])
        if not normalized_date:
            continue

        rows.append(
            {
                "date": normalized_date,
                "day_of_week": _day_name_from_date(normalized_date),
                "start_time": start_time,
                "end_time": end_time,
                "total_hours": round(min(max(total_hours, 0.0), 14.0), 2),
                "comments": line,
            }
        )

    return _finalize_rows(rows)


def extract_rows_type_b(text: str) -> list[dict[str, Any]]:
    rows = []
    date_pattern = r"\b(?:[0-2]?\d|3[01])/(?:0?\d|1[0-2])/(?:\d{2,4})\b"
    time_pattern = r"\b(?:[01]?\d|2[0-3]):[0-5]\d\b"
    decimal_pattern = r"\b\d{1,2}\.\d{1,2}\b"

    for line in [line.strip() for line in text.splitlines() if line.strip()]:
        dates = re.findall(date_pattern, line)
        if not dates:
            continue

        times = re.findall(time_pattern, line)
        decimals = [float(v) for v in re.findall(decimal_pattern, line)]
        meaningful_decimals = [v for v in decimals if 0.0 < v <= 14.0]

        start_time = times[0] if len(times) >= 1 else None
        end_time = times[1] if len(times) >= 2 else None

        total_hours = 0.0
        if meaningful_decimals:
            total_hours = max(meaningful_decimals)
        elif start_time and end_time and start_time != end_time:
            total_hours = max(_hours_between(start_time, end_time) - 0.5, 0.0)
        else:
            total_hours = _default_workday_hours(dates[-1])

        if start_time == end_time:
            start_time = None
            end_time = None

        normalized_date = _normalize_date(dates[-1])
        if not normalized_date:
            continue

        rows.append(
            {
                "date": normalized_date,
                "day_of_week": _day_name_from_date(normalized_date),
                "start_time": start_time,
                "end_time": end_time,
                "total_hours": round(min(max(total_hours, 0.0), 14.0), 2),
                "comments": line,
            }
        )

    return _finalize_rows(rows)


def _hours_between(start_time: str, end_time: str) -> float:
    try:
        fmt = "%H:%M"
        start = datetime.strptime(start_time, fmt)
        end = datetime.strptime(end_time, fmt)
        if end < start:
            end = end + timedelta(days=1)
        delta = end - start

        return round(delta.total_seconds() / 3600, 2)
    except ValueError:
        return 0.0


def _duration_to_hours(value: str) -> float:
    try:
        hours, minutes = value.split(":")
        return round(int(hours) + int(minutes) / 60, 2)
    except (ValueError, AttributeError):
        return 0.0


def _extract_duration_from_line(line: str, target: float = 8.5) -> float | None:
    candidate_times = re.findall(r"\b(?:0?\d|1[0-4]):[0-5]\d\b", line)
    if not candidate_times:
        return None

    durations = [_duration_to_hours(item) for item in candidate_times]
    durations = [value for value in durations if 0.0 < value <= 14.0]
    if not durations:
        return None

    return min(durations, key=lambda value: abs(value - target))


def _default_workday_hours(date_value: str) -> float:
    try:
        parsed_date = _parse_date(date_value)
        if not parsed_date:
            return 8.5
    except (ValueError, IndexError):
        return 8.5

    if parsed_date.weekday() in (4, 5):
        return 0.0

    return 8.5


def _normalize_ocr_text(text: str) -> str:
    lines = []
    for raw_line in text.splitlines():
        line = raw_line.replace("|", " ")
        line = re.sub(r"(\d)[oO](\d)", r"\1 0 \2", line)
        line = re.sub(r"(?<=\d)[lI](?=\d)", "1", line)
        line = re.sub(r"\s+", " ", line).strip()
        if line:
            lines.append(line)
    return "\n".join(lines)


def _normalize_date(value: str) -> str | None:
    value = value.replace("-", "/").replace(".", "/")
    parsed = _parse_date(value)
    if not parsed:
        return None
    return parsed.strftime("%d/%m/%Y")


def _parse_date(value: str) -> datetime | None:
    value = value.strip()
    for fmt in ("%d/%m/%Y", "%d/%m/%y"):
        try:
            parsed = datetime.strptime(value, fmt)
            if parsed.year < 2000:
                parsed = parsed.replace(year=parsed.year + 2000)
            return parsed
        except ValueError:
            continue
    return None


def _day_name_from_date(value: str) -> str:
    parsed = _parse_date(value)
    if not parsed:
        return ""

    names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    return names[parsed.weekday()]


def _finalize_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    best_by_date: dict[str, dict[str, Any]] = {}

    for row in rows:
        key = row["date"]
        existing = best_by_date.get(key)
        if not existing:
            best_by_date[key] = row
            continue

        score_existing = _row_quality_score(existing)
        score_new = _row_quality_score(row)
        if score_new > score_existing:
            best_by_date[key] = row

    finalized = list(best_by_date.values())
    finalized.sort(key=lambda item: _parse_date(item["date"]) or datetime.max)
    return finalized


def _row_quality_score(row: dict[str, Any]) -> float:
    score = row.get("total_hours", 0.0)
    if row.get("start_time"):
        score += 0.5
    if row.get("end_time"):
        score += 0.5
    return score


def _is_break_or_noise_time(value: str | None) -> bool:
    if not value:
        return False
    if value in ("00:30", "0:30"):
        return True
    try:
        hour = int(value.split(":")[0])
        return hour < 5
    except (ValueError, IndexError):
        return False