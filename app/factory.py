import pdfplumber
from app.parsers.type_a_parser import TypeAParser
from app.parsers.type_b_parser import TypeBParser
from app.generators.type_a_generator import TypeAResponseGenerator
from app.generators.type_b_generator import TypeBResponseGenerator
from app.renderers.type_a_renderer import TypeARenderer
from app.renderers.type_b_renderer import TypeBRenderer

class ReportFactory:
    @staticmethod
    def get_tools(file_path: str):
        # 1. זיהוי סוג הדו"ח לפי מילות מפתח בטקסט
        with pdfplumber.open(file_path) as pdf:
            first_page_text = pdf.pages[0].extract_text() or ""
            first_page_text = first_page_text.strip()

        normalized_path = file_path.lower()
        normalized_text = first_page_text.replace("\n", " ")
            
        # בדיקה אם זה סוג א' (לפי מילת מפתח שמצאנו בקבצים שלך)
        if "מחיר לשעה" in normalized_text or "n_r" in normalized_path:
            return TypeAParser(), TypeAResponseGenerator(), TypeARenderer()
        
        # בדיקה אם זה סוג ב' (לפי מילות מפתח של אחוזים)
        if "% 125" in normalized_text or "a_r" in normalized_path:
            return TypeBParser(), TypeBResponseGenerator(), TypeBRenderer()
            
        raise ValueError("סוג הד\"ח לא זוהה")