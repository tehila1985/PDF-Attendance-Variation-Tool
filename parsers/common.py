from __future__ import annotations

import re

from core.entities import parse_date

DATE_PATTERN = re.compile(r"(\d{1,2}[./]\d{1,2}(?:[./]\d{2,4})?)")
# Colon-only: avoids matching decimal-hours values like '7.50' that appear
# in percentage columns of attendance reports.
TIME_PATTERN = re.compile(r"((?:[01]?\d|2[0-3]):[0-5]\d)")
PERCENT_PATTERN = re.compile(r"(100%|125%|150%)")
DAY_PATTERN = re.compile(r"(ראשון|שני|שלישי|רביעי|חמישי|שישי|שבת|Sun|Mon|Tue|Wed|Thu|Fri|Sat)")


def normalize_hhmm(value: str | None) -> str | None:
    if not value:
        return None
    return value.replace(".", ":")


def extract_employee_name(full_text: str) -> str | None:
    patterns = [
        r"שם\s*עובד\s*[:\-]?\s*(.+)",
        r"עובד\s*[:\-]?\s*(.+)",
        r"Employee\s*[:\-]?\s*(.+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, full_text, re.IGNORECASE)
        if match:
            value = match.group(1).strip().split("\n")[0].strip()
            return value if value else None
    return None


def extract_month(full_text: str) -> str | None:
    patterns = [
        r"חודש\s*[:\-]?\s*([^\n]+)",
        r"חודש\s*דוח\s*[:\-]?\s*([^\n]+)",
        r"Month\s*[:\-]?\s*([^\n]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, full_text, re.IGNORECASE)
        if match:
            value = match.group(1).strip()
            return value if value else None

    date_match = DATE_PATTERN.search(full_text)
    if date_match:
        parsed = parse_date(date_match.group(1))
        if parsed:
            return parsed.strftime("%Y-%m")

    return None
