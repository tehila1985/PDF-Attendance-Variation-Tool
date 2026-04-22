from abc import ABC, abstractmethod
from app.entities import AttendanceReport

class BaseReportParser(ABC):
    @abstractmethod
    def parse(self, file_path: str) -> AttendanceReport:
        """
        מקבל נתיב לקובץ PDF ומחזיר אובייקט נתונים מובנה.
        כל Parser (TypeA/TypeB) יממש את זה אחרת.
        """
        pass