import os

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.interfaces.renderer_interface import BaseRenderer
from app.services.hebrew_text_service import rtl


class TypeARenderer(BaseRenderer):
    def render(self, report, output_path):
        doc = SimpleDocTemplate(output_path, pagesize=A4, rightMargin=24, leftMargin=24, topMargin=24, bottomMargin=24)
        styles = getSampleStyleSheet()
        font_name = _ensure_hebrew_font()

        styles["Title"].fontName = font_name
        styles["Normal"].fontName = font_name

        title = Paragraph(rtl(f"דוח נוכחות סוג א - {report.employee_name}"), styles["Title"])
        subtitle = Paragraph(rtl(f"חודש: {report.month_year}"), styles["Normal"])

        data = [[rtl("תאריך"), rtl("יום בשבוע"), rtl("שעת כניסה"), rtl("שעת יציאה"), rtl('סה"כ שעות')]]
        for row in report.rows:
            data.append([
                row.date,
                rtl(row.day_of_week),
                row.start_time or "-",
                row.end_time or "-",
                f"{row.total_hours:.2f}",
            ])

        data.append(["", "", "", rtl('סה"כ שעות'), f"{report.total_monthly_hours:.2f}"])
        data.append(["", "", "", rtl('סה"כ לתשלום'), f"{report.total_payment:.2f}"])

        table = Table(data, colWidths=[90, 80, 80, 80, 80], repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), font_name),
                    ("FONTNAME", (0, 1), (-1, -1), font_name),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#6b7280")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -3), [colors.white, colors.HexColor("#f3f4f6")]),
                    ("BACKGROUND", (0, -2), (-1, -1), colors.HexColor("#e5e7eb")),
                    ("FONTNAME", (0, -2), (-1, -1), font_name),
                ]
            )
        )

        doc.build([title, Spacer(1, 8), subtitle, Spacer(1, 12), table])


def _ensure_hebrew_font() -> str:
    font_name = "Helvetica"
    font_path = r"C:\Windows\Fonts\arial.ttf"

    if os.path.exists(font_path):
        try:
            pdfmetrics.registerFont(TTFont("ArialHebrew", font_path))
            font_name = "ArialHebrew"
        except Exception:
            font_name = "Helvetica"

    return font_name