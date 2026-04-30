from core.entities import OCRPage, OCRResult, ReportType
from services.classifier import KeywordLayoutClassifier


def test_classify_type_a_by_keywords() -> None:
    classifier = KeywordLayoutClassifier()
    ocr = OCRResult(
        full_text='שעת כניסה 08:00 שעת יציאה 17:00 סה"כ שעות 09:00',
        pages=[OCRPage(page_number=1, text="")],
    )

    assert classifier.classify(ocr) == ReportType.TYPE_A


def test_classify_type_b_by_keywords_and_block_signal() -> None:
    classifier = KeywordLayoutClassifier()
    ocr = OCRResult(
        full_text="מקום תל אביב הפסקה 00:30",
        pages=[OCRPage(page_number=1, text="", blocks=[{"text": "125%"}])],
    )

    assert classifier.classify(ocr) == ReportType.TYPE_B


def test_classify_unknown_when_no_signal() -> None:
    classifier = KeywordLayoutClassifier()
    ocr = OCRResult(full_text="random text", pages=[OCRPage(page_number=1, text="")])

    assert classifier.classify(ocr) == ReportType.UNKNOWN


def test_classify_type_a_by_header_line_structure() -> None:
    classifier = KeywordLayoutClassifier()
    text = "\n".join(
        [
            "דוח נוכחות חודשי",
            "תאריך יום שעת כניסה שעת יציאה סה\"כ שעות",
            "01/04/2026 ראשון 08:00 17:00 9.00",
        ]
    )
    ocr = OCRResult(full_text=text, pages=[OCRPage(page_number=1, text=text)])

    assert classifier.classify(ocr) == ReportType.TYPE_A


def test_classify_type_b_by_header_line_structure() -> None:
    classifier = KeywordLayoutClassifier()
    text = "\n".join(
        [
            "סיכום שעות",
            "תאריך יום מקום כניסה יציאה הפסקה % 100 % 125 % 150",
            "03/04/2026 שלישי מקום: תל אביב 08:00 17:00 00:30 7.50 1.00 0.00",
        ]
    )
    ocr = OCRResult(full_text=text, pages=[OCRPage(page_number=1, text=text)])

    assert classifier.classify(ocr) == ReportType.TYPE_B


def test_classify_type_b_by_row_structure_without_header() -> None:
    classifier = KeywordLayoutClassifier()
    text = "04/04/2026 רביעי 08:00 17:00 00:30 7.50 1.00 0.00 125%"
    ocr = OCRResult(full_text=text, pages=[OCRPage(page_number=1, text=text)])

    assert classifier.classify(ocr) == ReportType.TYPE_B


def test_infer_layout_metadata_type_b() -> None:
    classifier = KeywordLayoutClassifier()
    ocr = OCRResult(full_text="", pages=[OCRPage(page_number=1, text="")])

    metadata = classifier.infer_layout_metadata(ReportType.TYPE_B, ocr)

    assert metadata["source_page_count"] == 1
    assert "location" in metadata["columns"]
    assert "percentage_bracket" in metadata["columns"]


