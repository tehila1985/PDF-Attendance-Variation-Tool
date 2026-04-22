from datetime import datetime, timedelta

from app.interfaces.generator_interface import BaseResponseGenerator
from app.entities import AttendanceReport
from app.logic.rules import TimeOffsetRule, CalculateTypeAHoursRule

class TypeAResponseGenerator(BaseResponseGenerator):
    def calculate_variation(self, data: AttendanceReport) -> AttendanceReport:
        # הגדרת סט החוקים הספציפי לסוג א'
        rules = [
            TimeOffsetRule(),
            CalculateTypeAHoursRule(hourly_rate=data.hourly_rate or 30.65)
        ]
        
        # הרצת החוקים על כל שורה בדו"ח
        for row in data.rows:
            if row.total_hours <= 0:
                row.start_time = None
                row.end_time = None
                continue

            if not row.start_time or not row.end_time:
                start_time, end_time = _build_time_window(row.date, row.total_hours)
                row.start_time = start_time
                row.end_time = end_time

            for rule in rules:
                row = rule.apply(row)
        
        # עדכון סיכומים כלליים של הדו"ח
        data.total_monthly_hours = sum(r.total_hours for r in data.rows)
        hourly_rate = data.hourly_rate or 30.65
        data.total_payment = round(data.total_monthly_hours * hourly_rate, 2)
        
        return data


def _build_time_window(date_value: str, total_hours: float) -> tuple[str, str]:
    base = datetime.strptime("08:30", "%H:%M")
    checksum = sum(ord(ch) for ch in date_value)
    shift = (checksum % 7) * 5
    start = base + timedelta(minutes=shift)
    end = start + timedelta(hours=total_hours)
    return start.strftime("%H:%M"), end.strftime("%H:%M")