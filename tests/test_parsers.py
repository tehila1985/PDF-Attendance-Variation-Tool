from core.entities import OCRPage, OCRResult, ReportType
from parsers.factory import ParserFactory
from parsers.type_a_parser import TypeAReportParser
from parsers.type_b_parser import TypeBReportParser


def test_parser_factory_returns_type_a_parser() -> None:
    factory = ParserFactory()
    parser = factory.create(ReportType.TYPE_A)
    assert isinstance(parser, TypeAReportParser)


def test_type_a_parser_extracts_rows_and_monthly_total() -> None:
    text = "\n".join(
        [
            "שם עובד: ישראל ישראלי",
            "חודש: 2026-04",
            "01/04/2026 ראשון 08:00 17:00 09:00",
            "02/04/2026 שני 08:30 17:00",
        ]
    )
    ocr = OCRResult(full_text=text, pages=[OCRPage(page_number=1, text=text)], metadata={"layout_metadata": {}})

    report = TypeAReportParser().parse(ocr)

    assert report.employee_name == "ישראל ישראלי"
    assert len(report.rows) == 2
    assert report.rows[0].start_time == "08:00"
    assert report.rows[1].total_hours == "08:30"
    assert report.monthly_total_hours == "17:30"


def test_type_b_parser_extracts_location_break_and_percentage() -> None:
    text = "\n".join(
        [
            "שם עובד: דנה כהן",
            "חודש: 2026-04",
            "03/04/2026 שלישי מקום: תל אביב הפסקה: 00:30 08:00 16:00 08:00 125%",
        ]
    )
    ocr = OCRResult(full_text=text, pages=[OCRPage(page_number=1, text=text)], metadata={"layout_metadata": {}})

    report = TypeBReportParser().parse(ocr)

    assert report.employee_name == "דנה כהן"
    assert len(report.rows) == 1
    row = report.rows[0]
    assert row.location == "תל אביב הפסקה: 00:30 08:00 16:00 08:00 125%"
    assert row.break_duration == "00:30"
    assert row.percentage_bracket == "125%"
    # 16:00 - 08:00 = 8h minus 30 min break = 07:30
    assert row.total_hours == "07:30"


def test_type_a_parser_rejects_type_b_like_row() -> None:
    parser = TypeAReportParser()

    row = parser._parse_row("03/04/2026 שלישי מקום: תל אביב 08:00 16:00 00:30 7.50 125%")

    assert row is None
