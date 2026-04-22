from abc import ABC, abstractmethod
from app.entities import AttendanceReport


class BaseResponseGenerator(ABC):
    @abstractmethod
    def calculate_variation(self, data: AttendanceReport) -> AttendanceReport:
        pass