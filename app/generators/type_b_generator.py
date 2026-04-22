from datetime import datetime, timedelta

from app.interfaces.generator_interface import BaseResponseGenerator
from app.entities import AttendanceReport
from app.logic.rules import TimeOffsetRule, CalculateTypeBOvertimeRule

class TypeBResponseGenerator(BaseResponseGenerator):
    def calculate_variation(self, data: AttendanceReport) -> AttendanceReport:
        # סט חוקים לסוג ב'
        rules = [
            TimeOffsetRule(),
            CalculateTypeBOvertimeRule() # חישוב אחוזים והפסקות
        ]
        
        for row in data.rows:
            if row.total_hours <= 0:
                row.start_time = None
                row.end_time = None
                row.overtime_shabbat = 0.0
                row.overtime_125 = 0.0
                row.overtime_150 = 0.0
                continue

            if not row.start_time or not row.end_time or _is_unreliable_time_window(row.start_time, row.end_time):
                start_time, end_time = _build_time_window(row.date, row.total_hours)
                row.start_time = start_time
                row.end_time = end_time

            for rule in rules:
                row = rule.apply(row)
        
        # עדכון סיכומים חודשיים (לפי מה שמופיע בדו"ח המקורי) [cite: 10, 34]
        data.total_monthly_hours = sum(r.total_hours for r in data.rows)
        
        return data


def _build_time_window(date_value: str, total_hours: float) -> tuple[str, str]:
    base = datetime.strptime("08:00", "%H:%M")
    checksum = sum(ord(ch) for ch in date_value)
    shift = (checksum % 7) * 5
    start = base + timedelta(minutes=shift)
    # Type B uses a standard 30-minute break in the rendered report.
    end = start + timedelta(hours=total_hours + 0.5)
    return start.strftime("%H:%M"), end.strftime("%H:%M")


def _is_unreliable_time_window(start_time: str, end_time: str) -> bool:
    try:
        start = datetime.strptime(start_time, "%H:%M")
        end = datetime.strptime(end_time, "%H:%M")
    except ValueError:
        return True

    # OCR can mis-read break/time tokens and produce midnight-like shifts.
    if start.hour < 5 or end.hour < 5:
        return True

    return end <= start