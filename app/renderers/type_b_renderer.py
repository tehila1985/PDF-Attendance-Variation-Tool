import os

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.interfaces.renderer_interface import BaseRenderer
from app.services.hebrew_text_service import rtl


class TypeBRenderer(BaseRenderer):
    def render(self, report, output_path):
        doc = SimpleDocTemplate(
            output_path,
            pagesize=landscape(A4),
            rightMargin=24,
            leftMargin=24,
            topMargin=24,
            bottomMargin=24,
        )
        styles = getSampleStyleSheet()
        font_name = _ensure_hebrew_font()

        styles["Title"].fontName = font_name
        styles["Normal"].fontName = font_name

        title = Paragraph(rtl(f"דוח נוכחות סוג ב - {report.employee_name}"), styles["Title"])
        subtitle = Paragraph(rtl(f"חודש: {report.month_year}"), styles["Normal"])

        data = [[rtl("תאריך"), rtl("יום"), rtl("מקום"), rtl("כניסה"), rtl("יציאה"), rtl("הפסקה"), "100%", "125%", "150%", rtl("שבת 150%")]]
        for row in report.rows:
            data.append([
                row.date,
                rtl(row.day_of_week),
                rtl("גליליון"),
                row.start_time or "-",
                row.end_time or "-",
                "00:30",
                f"{row.total_hours:.2f}",
                f"{row.overtime_125:.2f}",
                f"{row.overtime_150:.2f}",
                f"{row.overtime_shabbat:.2f}",
            ])

        total_125 = sum(row.overtime_125 for row in report.rows)
        total_150 = sum(row.overtime_150 for row in report.rows)
        total_shabbat = sum(row.overtime_shabbat for row in report.rows)
        data.append(["", "", "", "", "", rtl('סה"כ'), f"{report.total_monthly_hours:.2f}", f"{total_125:.2f}", f"{total_150:.2f}", f"{total_shabbat:.2f}"])

        table = Table(data, colWidths=[80, 70, 85, 65, 65, 55, 60, 60, 60, 70], repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), font_name),
                    ("FONTNAME", (0, 1), (-1, -1), font_name),
                    ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#6b7280")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#eef2ff")]),
                    ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#dbeafe")),
                    ("FONTNAME", (0, -1), (-1, -1), font_name),
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