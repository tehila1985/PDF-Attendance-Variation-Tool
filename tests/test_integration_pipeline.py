from __future__ import annotations

from pathlib import Path

from services.ocr_service import TesseractPyMuPDFOCRService
from services.container import AppContainer


def test_integration_pipeline_processes_sample_pdf() -> None:
    # Choose one sample PDF with text extraction and OCR fallback support.
    sample_pdf = Path("real_reports_input") / "a_r_25.pdf"
    assert sample_pdf.exists(), "Integration sample PDF is missing"

    ocr_service = TesseractPyMuPDFOCRService(ocr_lang="heb+eng")
    ocr_result = ocr_service.extract(str(sample_pdf))
    assert ocr_result.full_text.strip(), "OCR output should contain text"

    container = AppContainer.create(ocr_lang="heb+eng")
    report_type = container.classifier.classify(ocr_result)
    assert report_type != None

    parser = container.parser_factory.get_parser(report_type)
    report = parser.parse(ocr_result)
    assert report.rows, "Parsed report should contain attendance rows"
    assert report.monthly_total_hours is not None

    varied_report = container.transformation_service.apply(report, seed=123)
    assert varied_report.rows
    assert varied_report.monthly_total_hours

    renderer = container.build_renderer("html")
    output_path = Path("real_reports_output") / "integration_output.html"
    renderer.render(report=varied_report, source_path=str(sample_pdf), output_path=str(output_path))
    assert output_path.exists()

    content = output_path.read_text(encoding="utf-8")
    assert "Attendance Report Variation" in content
