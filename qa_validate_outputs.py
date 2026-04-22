from __future__ import annotations

from datetime import datetime
from pathlib import Path

from app.factory import ReportFactory


INPUT_DIR = Path("input_files")


def main() -> int:
    has_errors = False

    for pdf_path in sorted(INPUT_DIR.glob("*.pdf")):
        parser, generator, _renderer = ReportFactory.get_tools(str(pdf_path))
        report = generator.calculate_variation(parser.parse(str(pdf_path)))
        errors = validate_report(report)

        if errors:
            has_errors = True
            print(f"[FAIL] {pdf_path.name}")
            for error in errors:
                print(f"  - {error}")
        else:
            print(f"[PASS] {pdf_path.name}")

    return 1 if has_errors else 0


def validate_report(report) -> list[str]:
    errors: list[str] = []
    total_hours = 0.0

    if not report.rows:
        errors.append("No attendance rows extracted")

    if not report.month_year or report.month_year == "Unknown":
        errors.append("Month was not identified")

    for row in report.rows:
        parsed_date = _parse_date(row.date)
        if not parsed_date:
            errors.append(f"Invalid date: {row.date}")
            continue

        if row.total_hours < 0 or row.total_hours > 14:
            errors.append(f"Unrealistic daily hours on {row.date}: {row.total_hours}")

        if row.total_hours == 0:
            if row.start_time or row.end_time:
                errors.append(f"Zero-hour row should not have times on {row.date}")
        else:
            if not row.start_time or not row.end_time:
                errors.append(f"Missing time window on worked day {row.date}")
            elif not _is_valid_time_window(row.start_time, row.end_time):
                errors.append(f"Invalid time order on {row.date}: {row.start_time} -> {row.end_time}")

        if report.report_type == "TypeB":
            expected_125, expected_150 = _expected_overtime(row.total_hours)
            if round(row.overtime_125, 2) != expected_125 or round(row.overtime_150, 2) != expected_150:
                errors.append(
                    f"Overtime mismatch on {row.date}: got ({row.overtime_125}, {row.overtime_150}) expected ({expected_125}, {expected_150})"
                )

        total_hours += row.total_hours

    if round(total_hours, 2) != round(report.total_monthly_hours, 2):
        errors.append(
            f"Monthly total mismatch: rows={round(total_hours, 2)} report={round(report.total_monthly_hours, 2)}"
        )

    return errors


def _parse_date(value: str) -> datetime | None:
    for fmt in ("%d/%m/%Y", "%d/%m/%y"):
        try:
            parsed = datetime.strptime(value, fmt)
            if parsed.year < 2000:
                parsed = parsed.replace(year=parsed.year + 2000)
            return parsed
        except ValueError:
            continue
    return None


def _is_valid_time_window(start_time: str, end_time: str) -> bool:
    fmt = "%H:%M"
    try:
        start = datetime.strptime(start_time, fmt)
        end = datetime.strptime(end_time, fmt)
    except ValueError:
        return False
    return end > start


def _expected_overtime(total_hours: float) -> tuple[float, float]:
    if total_hours <= 8.5:
        return 0.0, 0.0
    if total_hours <= 10.5:
        return round(total_hours - 8.5, 2), 0.0
    return 2.0, round(total_hours - 10.5, 2)


if __name__ == "__main__":
    raise SystemExit(main())