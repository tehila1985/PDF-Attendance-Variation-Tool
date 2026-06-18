from __future__ import annotations

import json
from pathlib import Path

from core.entities import AttendanceReport, AttendanceRow, ReportType
from generators.json_renderer import JsonRenderer


def test_json_renderer_writes_valid_output() -> None:
    rows = (
        AttendanceRow(
            date=None,
            day="ראשון",
            start_time="08:00",
            end_time="17:00",
            total_hours="09:00",
            location="HQ",
            percentage_bracket=None,
            break_duration="00:30",
            break_minutes=30,
            overtime_125_hours="00:30",
            overtime_150_hours="00:00",
            raw_line="01/01/2026 ראשון 08:00 17:00 09:00",
            metadata={"row_id": 1},
        ),
    )
    report = AttendanceReport(
        report_type=ReportType.TYPE_B,
        employee_name="ישראל ישראלי",
        month="2026-01",
        rows=rows,
        monthly_total_hours="09:00",
        metadata={"layout_metadata": {"columns": ["date", "day"]}},
    )

    output_path = Path("real_reports_output") / "test_output.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    JsonRenderer().render(report=report, source_path="source.pdf", output_path=str(output_path))

    assert output_path.exists()
    content = json.loads(output_path.read_text(encoding="utf-8"))
    assert content["source_pdf"] == "source.pdf"
    assert content["report_type"] == "type_b"
    assert content["employee_name"] == "ישראל ישראלי"
    assert content["rows"][0]["day"] == "ראשון"
    assert content["rows"][0]["metadata"]["row_id"] == 1
