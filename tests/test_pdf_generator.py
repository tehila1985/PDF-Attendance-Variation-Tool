from generators.pdf_generator import ReportLabPDFGenerator


def test_display_text_reverses_hebrew_for_pdf_rendering() -> None:
    assert ReportLabPDFGenerator._display_text("ישראל ישראלי") == "ילארשי לארשי"


def test_display_text_keeps_latin_text_unchanged() -> None:
    assert ReportLabPDFGenerator._display_text("Monthly Total") == "Monthly Total"