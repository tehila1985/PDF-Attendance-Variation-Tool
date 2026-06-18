from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.entities import AttendanceReport, AttendanceRow, ReportType
from interfaces.renderer import BaseRenderer


class JsonRenderer(BaseRenderer):
    """Render an attendance report as structured JSON output."""

    def render(self, report: AttendanceReport, source_path: str, output_path: str) -> None:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        document = {
            "source_pdf": Path(source_path).name,
            "report_type": report.report_type.value,
            "employee_name": report.employee_name,
            "month": report.month,
            "monthly_total_hours": report.monthly_total_hours,
            "rows": [self._serialize_row(row) for row in report.rows],
            "metadata": {**report.metadata},
        }

        try:
            output.write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError as exc:
            raise RuntimeError(f"JSON generation failed for '{output}': {exc}") from exc

    @staticmethod
    def _serialize_row(row: AttendanceRow) -> dict[str, Any]:
        return {
            "date": row.date.isoformat() if row.date else None,
            "day": row.day,
            "start_time": row.start_time,
            "end_time": row.end_time,
            "break_duration": row.break_duration,
            "break_minutes": row.break_minutes,
            "total_hours": row.total_hours,
            "location": row.location,
            "percentage_bracket": row.percentage_bracket,
            "overtime_125_hours": row.overtime_125_hours,
            "overtime_150_hours": row.overtime_150_hours,
            "raw_line": row.raw_line,
            "metadata": dict(row.metadata),
        }
