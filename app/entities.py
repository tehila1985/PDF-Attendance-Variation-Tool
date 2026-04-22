from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class AttendanceRow:
    """
    מחלקה המייצגת שורה בודדת בדו"ח הנוכחות.
    היא מכילה את כל השדות האפשריים משני סוגי הדוחות (A ו-B).
    """
    date: str
    day_of_week: str
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    total_hours: float = 0.0
    comments: str = ""
    # שדות ייחודיים לדוחות עם אחוזים (סוג B)
    overtime_shabbat: float = 0.0
    overtime_125: float = 0.0
    overtime_150: float = 0.0

@dataclass
class AttendanceReport:
    """
    מחלקה המייצגת דו"ח נוכחות חודשי מלא.
    זהו ה-"Entity" המרכזי שעובר בין ה-Parser ל-Generator.
    """
    report_type: str  # "TypeA" או "TypeB"
    employee_name: str
    month_year: str
    # רשימה של אובייקטי AttendanceRow
    rows: List[AttendanceRow] = field(default_factory=list)
    hourly_rate: float = 0.0
    
    # סיכומים חודשיים
    total_monthly_hours: float = 0.0
    total_payment: float = 0.0  # רלוונטי בעיקר לסוג A שבו יש מחיר לשעה