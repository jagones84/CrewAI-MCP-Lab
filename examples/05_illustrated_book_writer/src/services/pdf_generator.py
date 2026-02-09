import os
import re

try:
    from fpdf import FPDF
except ImportError:
    FPDF = None
    print("WARNING: fpdf2 not installed.")

def clean_text(text: str) -> str:
    """Cleans text artifacts from LLM output."""
    if not text: return ""
    text = re.sub(r'(?i)\*\*Final Answer\*\*:', '', text)
    text = re.sub(r'(?i)Final Answer:', '', text)
    text = re.sub(r'(?i)\*\*Final Scene Text.*?\*\*:', '', text)
    replacements = {
        '—': '-', '–': '-', '“': '"', '”': '"', '‘': "'", '’': "'", '…': '...'
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text.strip()

class PDFBook(FPDF):
    def __init__(self, book_title="Automated Illustrated Novel", 
                 bg_color=(10, 5, 5), 
                 text_color=(220, 220, 220), 
                 line_spacing=5,
                 font_body="times",
                 font_header="times"):
        super().__init__()
        self.set_margins(25, 25, 25)
        self.set_auto_page_break(auto=True, margin=25)
        self.book_title = book_title
        self.custom_bg_color = bg_color
        self.custom_text_color = text_color
        self.line_spacing = line_spacing
        self.font_body = font_body
        self.font_header = font_header
        self.font_header = font_header

    def _safe_color(self, color, default=(200,200,200)):
        if color is None: return default
        try:
            return [max(0, min(255, int(c))) if c is not None else default[i] for i, c in enumerate(color[:3])]
        except:
            return default

    def header(self):
        # Draw Background
        try:
            if self.custom_bg_color and len(self.custom_bg_color) >= 3:
                # Ensure all components are numeric and in range 0-255
                clean_color = self._safe_color(self.custom_bg_color, default=(0,0,0))
                self.set_fill_color(*clean_color)
                self.rect(0, 0, self.w, self.h, "F")
        except Exception as e:
            print(f"❌ PDF BG ERROR: {e} (bg_color={self.custom_bg_color})")
            
        try:
            self.set_font(self.font_header, 'I', 8)
            t_color = self._safe_color(self.custom_text_color, default=(200,200,200))
            self.set_text_color(*t_color)
            self.cell(0, 10, self.book_title, align='R')
            self.ln(15)
        except Exception as e:
            print(f"❌ PDF HEADER ERROR: {e}")

    def character_profiles(self, character_data: dict, character_context: str):
        """Generates a section for character profiles with images."""
        self.add_page()
        self.chapter_title("Dramatis Personae")
        
        # If we have structured data in char_manager, use it
        if character_data:
            for name, data in character_data.items():
                self.set_font(self.font_header, 'B', 16)
                self.set_text_color(*self._safe_color(self.custom_text_color))
                self.cell(0, 10, name, ln=True)
                
                # Portrait
                if data.get('portrait_path') and os.path.exists(data['portrait_path']):
                    try:
                        # Limit image height to 1/3 page
                        self.image(data['portrait_path'], h=80) 
                        self.ln(5)
                    except Exception as e:
                        print(f"PDF PORTRAIT ERROR: {e}")

                # Background
                self.set_font(self.font_body, '', 12)
                bg_text = clean_text(data.get('background', ''))
                bg_text = bg_text.encode('latin-1', 'replace').decode('latin-1')
                self.multi_cell(0, self.line_spacing, bg_text)
                self.ln(10)
        else:
            # Fallback to raw text
            self.set_font(self.font_body, '', 12)
            txt = clean_text(character_context).encode('latin-1', 'replace').decode('latin-1')
            self.multi_cell(0, self.line_spacing, txt)

    def chapter_title(self, title):
        title = title.encode('latin-1', 'replace').decode('latin-1')
        self.set_font(self.font_header, 'B', 24)
        self.set_text_color(*self._safe_color(self.custom_text_color))
        self.cell(0, 20, title, align='C', ln=True)
        self.ln(10)

    def chapter_body(self, scenes_data):
        self.set_font(self.font_body, '', 12)
        self.set_text_color(*self._safe_color(self.custom_text_color))
        
        for scene in scenes_data:
            # 1. Write Text
            text = scene.get('text', '')
            text = clean_text(text)
            text = text.encode('latin-1', 'replace').decode('latin-1')
            self.multi_cell(0, self.line_spacing, text.strip(), align='J')
            self.ln(5)
            
            # 2. Insert Image
            img_path = scene.get('image')
            if img_path and os.path.exists(img_path):
                try:
                    self.ln(5)
                    eff_width = self.w - self.l_margin - self.r_margin
                    
                    if self.get_y() > 200: 
                        self.add_page()
                        
                    self.image(img_path, w=eff_width)
                    self.ln(10)
                except Exception as e:
                    print(f"PDF IMAGE ERROR: {e}")
        
        self.ln(10)
