from datetime import datetime, timedelta
from app.entities import AttendanceRow

class TimeOffsetRule:
    """מזיז זמני כניסה/יציאה בצורה דטרמיניסטית לפי תכולת השורה."""
    def apply(self, row: AttendanceRow) -> AttendanceRow:
        if row.start_time and row.end_time:
            fmt = "%H:%M"
            try:
                offset = _deterministic_offset_minutes(row)
                start = datetime.strptime(row.start_time, fmt)
                end = datetime.strptime(row.end_time, fmt)

                start = start + timedelta(minutes=offset)
                end = end + timedelta(minutes=offset)

                if end <= start:
                    end = start + timedelta(hours=8, minutes=30)

                row.start_time = start.strftime(fmt)
                row.end_time = end.strftime(fmt)
            except ValueError:
                return row
        return row

class CalculateTypeAHoursRule:
    """מחשב מחדש את סך השעות ואת התשלום לפי מחיר שעתי"""
    def __init__(self, hourly_rate: float):
        self.hourly_rate = hourly_rate

    def apply(self, row: AttendanceRow) -> AttendanceRow:
        if row.start_time and row.end_time:
            fmt = "%H:%M"
            try:
                start = datetime.strptime(row.start_time, fmt)
                end = datetime.strptime(row.end_time, fmt)

                if end <= start:
                    end = end + timedelta(days=1)

                delta = end - start
                hours = delta.total_seconds() / 3600
                row.total_hours = _normalize_workday_hours(hours)
            except ValueError:
                row.total_hours = _normalize_workday_hours(row.total_hours)
        else:
            row.total_hours = _normalize_workday_hours(row.total_hours)
        return row


class CalculateTypeBOvertimeRule:
    """חישוב שעות נוס לפי כללים ספציפיים לסוג ב'"""

    def apply(self, row: AttendanceRow) -> AttendanceRow:
        net_hours = 0.0

        if row.start_time and row.end_time:
            fmt = "%H:%M"
            try:
                start = datetime.strptime(row.start_time, fmt)
                end = datetime.strptime(row.end_time, fmt)

                if end <= start:
                    end = end + timedelta(days=1)

                delta = end - start
                total_gross = delta.total_seconds() / 3600
                net_hours = max(0.0, total_gross - 0.5)
            except ValueError:
                net_hours = row.total_hours
        else:
            net_hours = row.total_hours

        net_hours = _normalize_workday_hours(net_hours)
        row.total_hours = net_hours

        weekday_name = (row.day_of_week or "").strip()
        if weekday_name == "שבת":
            row.overtime_shabbat = row.total_hours
            row.overtime_125 = 0.0
            row.overtime_150 = 0.0
            return row

        row.overtime_shabbat = 0.0

        # לוגיקה דטרמיניסטית קבועה לחלוקת 125% ו-150%
        if net_hours <= 8.5:
            row.overtime_125 = 0.0
            row.overtime_150 = 0.0
        elif net_hours <= 10.5:
            row.overtime_125 = round(net_hours - 8.5, 2)
            row.overtime_150 = 0.0
        else:
            row.overtime_125 = 2.0
            row.overtime_150 = round(net_hours - 10.5, 2)

        return row


def _deterministic_offset_minutes(row: AttendanceRow) -> int:
    seed_value = f"{row.date}|{row.start_time}|{row.end_time}|{row.comments}"
    checksum = sum(ord(ch) for ch in seed_value)
    return (checksum % 11) - 5


def _normalize_workday_hours(hours: float) -> float:
    # תחום עבודה סביר ליום בודד
    clamped = min(max(float(hours), 0.0), 14.0)
    return round(clamped, 2)