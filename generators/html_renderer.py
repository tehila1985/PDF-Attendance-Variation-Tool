from __future__ import annotations

import html
from pathlib import Path
from typing import Any

from core.entities import AttendanceReport, AttendanceRow, ReportType
from interfaces.renderer import BaseRenderer

_CSS = """
body { font-family: Arial, sans-serif; direction: rtl; padding: 24px; }
h1 { font-size: 1.4rem; margin-bottom: 4px; }
.meta { color: #555; margin-bottom: 16px; font-size: 0.9rem; }
table { border-collapse: collapse; width: 100%; font-size: 0.88rem; }
th { background: #e8e8e8; font-weight: bold; padding: 8px 10px; border: 1px solid #ccc; }
td { padding: 6px 10px; border: 1px solid #ddd; white-space: nowrap; }
tr:nth-child(even) { background: #f9f9f9; }
tr.total-row { background: #e0f0e0; font-weight: bold; }
"""


class HtmlRenderer(BaseRenderer):
    """Render an attendance report to a self-contained HTML file.

    Implements the ``BaseRenderer`` Strategy interface so it can be swapped
    with ``PdfRenderer`` transparently by the caller.
    """

    def render(self, report: AttendanceReport, source_path: str, output_path: str) -> None:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        layout_metadata: dict[str, Any] = report.metadata.get("layout_metadata", {})
        columns = self._columns(layout_metadata, report.report_type)
        headers = self._headers(layout_metadata, columns)

        body_rows: list[str] = []
        for row in report.rows:
            cells = "".join(
                f"<td>{html.escape(self._extract_value(row, col))}</td>"
                for col in columns
            )
            body_rows.append(f"<tr>{cells}</tr>")

        total_cells = "".join(
            f"<td>{html.escape(report.monthly_total_hours or '00:00') if col == 'total_hours' else ('סה&quot;כ חודשי' if col == columns[0] else '')}</td>"
            for col in columns
        )
        body_rows.append(f'<tr class="total-row">{total_cells}</tr>')

        header_html = "".join(f"<th>{html.escape(h)}</th>" for h in headers)
        table_html = (
            f"<table><thead><tr>{header_html}</tr></thead>"
            f"<tbody>{''.join(body_rows)}</tbody></table>"
        )

        document = f"""<!DOCTYPE html>
<html lang="he">
<head>
<meta charset="utf-8"/>
<title>Attendance Variation – {html.escape(Path(source_path).name)}</title>
<style>{_CSS}</style>
</head>
<body>
<h1>Attendance Report Variation</h1>
<div class="meta">
  <span>Source: {html.escape(Path(source_path).name)}</span> &nbsp;|&nbsp;
  <span>Employee: {html.escape(report.employee_name or 'N/A')}</span> &nbsp;|&nbsp;
  <span>Month: {html.escape(report.month or 'N/A')}</span>
</div>
{table_html}
</body>
</html>"""

        try:
            output.write_text(document, encoding="utf-8")
        except OSError as exc:
            raise RuntimeError(f"HTML generation failed for '{output}': {exc}") from exc

    # ---- Helpers (mirrors PdfRenderer private statics) -------------------

    @staticmethod
    def _columns(layout_metadata: dict[str, Any], report_type: ReportType) -> list[str]:
        columns = layout_metadata.get("columns")
        if isinstance(columns, list) and columns:
            return [str(col) for col in columns]
        if report_type == ReportType.TYPE_B:
            return [
                "date", "day", "location", "start_time", "end_time",
                "break_duration", "total_hours", "percentage_bracket",
            ]
        return ["date", "day", "start_time", "end_time", "total_hours"]

    @staticmethod
    def _headers(layout_metadata: dict[str, Any], columns: list[str]) -> list[str]:
        headers = layout_metadata.get("headers")
        if isinstance(headers, list) and len(headers) == len(columns):
            return [str(h) for h in headers]
        return [col.replace("_", " ").title() for col in columns]

    @staticmethod
    def _extract_value(row: AttendanceRow, column: str) -> str:
        if column == "date":
            return row.date.isoformat() if row.date else ""
        value = getattr(row, column, None)
        return "" if value is None else str(value)
