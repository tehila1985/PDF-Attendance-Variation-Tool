from datetime import date, datetime

from core.entities import AttendanceReport, AttendanceRow, ReportType, hhmm_to_minutes
from services.variation_engine import DeterministicVariationService


def _build_report() -> AttendanceReport:
    rows = [
        AttendanceRow(
            date=date(2026, 4, 1),
            day="ראשון",
            start_time="08:00",
            end_time="17:00",
            total_hours="09:00",
            location="HQ",
        ),
        AttendanceRow(
            date=date(2026, 4, 2),
            day="שני",
            start_time="08:30",
            end_time="16:30",
            total_hours="08:00",
            location="Branch",
        ),
    ]
    report = AttendanceReport(
        report_type=ReportType.TYPE_B,
        employee_name="User",
        month="2026-04",
        rows=rows,
    )
    return report.with_monthly_total()


def test_deterministic_seed_produces_same_output() -> None:
    service = DeterministicVariationService()
    report = _build_report()

    varied_1 = service.apply(report, seed=123)
    varied_2 = service.apply(report, seed=123)

    times_1 = [(r.start_time, r.end_time, r.total_hours) for r in varied_1.rows]
    times_2 = [(r.start_time, r.end_time, r.total_hours) for r in varied_2.rows]

    assert times_1 == times_2
    assert varied_1.monthly_total_hours == varied_2.monthly_total_hours


def test_variation_preserves_time_invariant_and_recomputes_totals() -> None:
    service = DeterministicVariationService()
    report = _build_report()

    varied = service.apply(report, seed="abc-seed")

    monthly_minutes = 0
    for row in varied.rows:
        start = datetime.strptime(row.start_time or "00:00", "%H:%M")
        end = datetime.strptime(row.end_time or "00:00", "%H:%M")
        if end <= start:
            end = end.replace(day=end.day + 1)

        assert end > start

        duration_minutes = int((end - start).total_seconds() // 60)
        assert hhmm_to_minutes(row.total_hours) == duration_minutes
        monthly_minutes += duration_minutes

    assert hhmm_to_minutes(varied.monthly_total_hours) == monthly_minutes


def test_different_seeds_change_at_least_one_row() -> None:
    service = DeterministicVariationService()
    report = _build_report()

    varied_1 = service.apply(report, seed=111)
    varied_2 = service.apply(report, seed=222)

    snapshot_1 = [(r.start_time, r.end_time) for r in varied_1.rows]
    snapshot_2 = [(r.start_time, r.end_time) for r in varied_2.rows]

    assert snapshot_1 != snapshot_2


def test_row_seed_depends_on_row_identity() -> None:
    service = DeterministicVariationService()
    report_a = _build_report()
    report_b = AttendanceReport(
        report_type=report_a.report_type,
        employee_name=report_a.employee_name,
        month=report_a.month,
        rows=(
            AttendanceRow(
                date=report_a.rows[0].date,
                day=report_a.rows[0].day,
                start_time=report_a.rows[0].start_time,
                end_time=report_a.rows[0].end_time,
                total_hours=report_a.rows[0].total_hours,
                location=report_a.rows[0].location,
            ),
            report_a.rows[1],
        ),
    ).with_monthly_total()

    # Change only the first row date to verify seed depends on row identity.
    report_c = AttendanceReport(
        report_type=report_a.report_type,
        employee_name=report_a.employee_name,
        month=report_a.month,
        rows=(
            AttendanceRow(
                date=report_a.rows[0].date.replace(day=2) if report_a.rows[0].date else None,
                day=report_a.rows[0].day,
                start_time=report_a.rows[0].start_time,
                end_time=report_a.rows[0].end_time,
                total_hours=report_a.rows[0].total_hours,
                location=report_a.rows[0].location,
            ),
            report_a.rows[1],
        ),
    ).with_monthly_total()

    varied_a = service.apply(report_a, seed=123)
    varied_c = service.apply(report_c, seed=123)

    assert varied_a.rows[0] != varied_c.rows[0]
    assert varied_a.rows[1] == varied_c.rows[1]
