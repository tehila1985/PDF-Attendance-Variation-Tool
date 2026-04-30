from __future__ import annotations

import re
from dataclasses import dataclass

from core.entities import OCRResult, ReportType
from parsers.common import DATE_PATTERN, TIME_PATTERN

_TYPE_A_HEADER_PATTERN = re.compile(r"שעת\s+כניסה\s*[:\-]?\s*שעת\s+יציאה", re.IGNORECASE)
_TYPE_B_PERCENT_PATTERN = re.compile(r"(?:%\s*100|100\s*%|%\s*125|125\s*%|%\s*150|150\s*%)")
_NUMERIC_TOKEN_PATTERN = re.compile(r"\b\d+(?:[.,]\d+)?%?\b")
_DECIMAL_VALUE_PATTERN = re.compile(r"\b\d{1,2}[.,]\d{1,2}\b")


@dataclass(slots=True)
class KeywordLayoutClassifier:
    """Header- and row-structure based report classifier."""

    # TYPE_A unique markers: these keywords only appear in TYPE_A headers
    type_a_keywords: tuple[str, ...] = ("שעת כניסה", "שעת יציאה", "סה\"כ שעות", "סהכ שעות")
    # TYPE_B unique markers: location + break columns are exclusive to TYPE_B
    type_b_keywords: tuple[str, ...] = ("מקום", "הפסקה")
    # Secondary TYPE_B indicators (weaker signal – ½ point each)
    type_b_secondary: tuple[str, ...] = ("100%", "125%", "150%")

    def classify(self, ocr_result: OCRResult) -> ReportType:
        lines = self._get_candidate_lines(ocr_result.full_text)
        header_line = self._extract_header_line(lines)
        header_type = self._classify_header_line(header_line) if header_line else ReportType.UNKNOWN
        if header_type != ReportType.UNKNOWN:
            return header_type

        row_type = self._classify_by_row_structure(lines)
        if row_type != ReportType.UNKNOWN:
            return row_type

        text = ocr_result.full_text
        a_score = self._score(text, self.type_a_keywords)
        b_score = self._score(text, self.type_b_keywords)
        # Secondary indicators contribute 0.5 each so they can break a tie
        # but can't override a strong primary-keyword signal.
        b_score += 0.5 * self._score(text, self.type_b_secondary)

        if a_score == 0 and b_score == 0:
            return ReportType.UNKNOWN
        return ReportType.TYPE_A if a_score >= b_score else ReportType.TYPE_B

    def infer_layout_metadata(self, report_type: ReportType, ocr_result: OCRResult) -> dict[str, object]:
        """Infer column order/headers for rendering the resulting PDF."""
        if report_type == ReportType.TYPE_A:
            return {
                "columns": ["date", "day", "start_time", "end_time", "total_hours"],
                "headers": ["תאריך", "יום", "שעת כניסה", "שעת יציאה", "סה\"כ שעות"],
                "source_page_count": len(ocr_result.pages),
            }

        if report_type == ReportType.TYPE_B:
            return {
                "columns": [
                    "date",
                    "day",
                    "location",
                    "start_time",
                    "end_time",
                    "break_duration",
                    "total_hours",
                    "percentage_bracket",
                ],
                "headers": ["תאריך", "יום", "מקום", "כניסה", "יציאה", "הפסקה", "סה\"כ", "%"],
                "source_page_count": len(ocr_result.pages),
            }

        return {
            "columns": ["date", "day", "start_time", "end_time", "total_hours"],
            "headers": ["Date", "Day", "Start", "End", "Total"],
            "source_page_count": len(ocr_result.pages),
        }

    @staticmethod
    def _score(text: str, keywords: tuple[str, ...]) -> int:
        lowered = text.lower()
        return sum(1 for keyword in keywords if keyword.lower() in lowered)

    @staticmethod
    def _get_candidate_lines(text: str) -> list[str]:
        return [line.strip() for line in text.splitlines() if line.strip()]

    def _extract_header_line(self, lines: list[str]) -> str | None:
        best_line: str | None = None
        best_score = 0

        for line in lines:
            if DATE_PATTERN.search(line):
                continue

            score = 0
            if "שעת כניסה" in line:
                score += 2
            if "שעת יציאה" in line:
                score += 2
            if "מקום" in line:
                score += 2
            score += len(_TYPE_B_PERCENT_PATTERN.findall(line))

            if score > best_score:
                best_score = score
                best_line = line

        return best_line if best_score >= 3 else None

    @staticmethod
    def _classify_header_line(line: str) -> ReportType:
        if _TYPE_A_HEADER_PATTERN.search(line):
            return ReportType.TYPE_A
        if "מקום" in line and len(_TYPE_B_PERCENT_PATTERN.findall(line)) >= 2:
            return ReportType.TYPE_B
        return ReportType.UNKNOWN

    def _classify_by_row_structure(self, lines: list[str]) -> ReportType:
        type_a_matches = 0
        type_b_matches = 0

        for line in lines:
            if not DATE_PATTERN.search(line):
                continue

            is_type_a = self._looks_like_type_a_row(line)
            is_type_b = self._looks_like_type_b_row(line)

            if is_type_a and not is_type_b:
                type_a_matches += 1
            elif is_type_b and not is_type_a:
                type_b_matches += 1

        if type_a_matches == 0 and type_b_matches == 0:
            return ReportType.UNKNOWN
        return ReportType.TYPE_A if type_a_matches >= type_b_matches else ReportType.TYPE_B

    @staticmethod
    def _looks_like_type_a_row(line: str) -> bool:
        if any(keyword in line for keyword in ("מקום", "הפסקה")):
            return False
        if _TYPE_B_PERCENT_PATTERN.search(line):
            return False

        times = TIME_PATTERN.findall(line)
        extra_numeric = KeywordLayoutClassifier._remaining_numeric_tokens(line)
        has_decimal_total = any(_DECIMAL_VALUE_PATTERN.fullmatch(token) for token in extra_numeric)

        if len(times) == 3 and not extra_numeric:
            return True
        if len(times) == 2 and len(extra_numeric) <= 1:
            return not extra_numeric or has_decimal_total
        return False

    @staticmethod
    def _looks_like_type_b_row(line: str) -> bool:
        times = TIME_PATTERN.findall(line)
        extra_numeric = KeywordLayoutClassifier._remaining_numeric_tokens(line)
        type_b_keywords_present = any(keyword in line for keyword in ("מקום", "הפסקה"))
        percent_columns_present = bool(_TYPE_B_PERCENT_PATTERN.search(line))

        if len(times) >= 3 and (type_b_keywords_present or percent_columns_present):
            return True
        if len(times) >= 3 and len(extra_numeric) >= 1:
            return True
        return False

    @staticmethod
    def _remaining_numeric_tokens(line: str) -> list[str]:
        scrubbed = DATE_PATTERN.sub(" ", line)
        scrubbed = TIME_PATTERN.sub(" ", scrubbed)
        return _NUMERIC_TOKEN_PATTERN.findall(scrubbed)
