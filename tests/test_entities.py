from core.entities import AttendanceRow, hhmm_to_minutes, minutes_to_hhmm, parse_date, parse_time


def test_time_and_date_parsing_helpers() -> None:
    assert parse_time("08:45") is not None
    assert parse_time("08.45") is not None
    assert parse_time("bad") is None

    assert parse_date("30/04/2026") is not None
    assert parse_date("30.04.26") is not None
    assert parse_date("not-a-date") is None


def test_minutes_converters() -> None:
    assert hhmm_to_minutes("01:30") == 90
    assert hhmm_to_minutes("99:99") is None
    assert minutes_to_hhmm(90) == "01:30"


def test_attendance_row_recompute_total_hours() -> None:
    row = AttendanceRow(
        date=None,
        day=None,
        start_time="08:00",
        end_time="17:30",
        total_hours=None,
    )

    row.recompute_total_hours()
    assert row.total_hours == "09:30"
