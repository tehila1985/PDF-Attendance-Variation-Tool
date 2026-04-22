from app.interfaces.parser_interface import BaseReportParser
from app.entities import AttendanceReport
from app.services.type_a_extraction_service import TypeAExtractionService

class TypeAParser(BaseReportParser):
    def __init__(self):
        self._service = TypeAExtractionService()

    def parse(self, file_path: str) -> AttendanceReport:
        return self._service.extract(file_path)