from __future__ import annotations

from dataclasses import dataclass

from app.factory import ReportFactory


@dataclass
class ProcessedReportResult:
    input_path: str
    output_path: str
    report_data: object


class ReportProcessingService:
    def process(self, input_path: str, output_path: str) -> ProcessedReportResult:
        parser, generator, renderer = ReportFactory.get_tools(input_path)
        report_data = parser.parse(input_path)
        modified_report = generator.calculate_variation(report_data)
        renderer.render(modified_report, output_path)
        return ProcessedReportResult(input_path=input_path, output_path=output_path, report_data=modified_report)