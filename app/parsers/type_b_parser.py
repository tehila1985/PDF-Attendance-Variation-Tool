from app.interfaces.parser_interface import BaseReportParser
from app.entities import AttendanceReport
from app.services.type_b_extraction_service import TypeBExtractionService

class TypeBParser(BaseReportParser):
    def __init__(self):
        self._service = TypeBExtractionService()

    def parse(self, file_path: str) -> AttendanceReport:
        return self._service.extract(file_path)