from pydantic import BaseModel, Field
from typing import List, Dict, Optional

class BookState(BaseModel):
    title: str = "Untitled"
    genre: str = "Fiction"
    theme: str = "None"
    target_chapters: int = 5
    scenes_per_chapter: int = 4
    images_per_chapter: int = 1
    master_plot: str = ""
    outline: List[Dict] = []
    book_content: List[Dict] = []
    last_summary: str = "Start."
    rag_path: str = ""
    mode: str = "create"
    action: str = "generate_book"
    modification_prompt: str = ""
    character_context: str = ""
    regen_chapters: List[int] = []
    regen_images: bool = False
    workflow_name: str = "image_perfectDeliberate_text_to_image_API.json"
    
    # PDF Styles
    pdf_bg_color: tuple = (10, 5, 5)
    pdf_text_color: tuple = (220, 220, 220)
    pdf_line_spacing: int = 5
    pdf_font_body: str = "times"
    pdf_font_header: str = "times"
    
    # Writing Styles
    target_word_count: int = 700
    language: str = "English"

    # --- ROBUSTNESS & STATE MACHINE EXTENSIONS ---
    chapter_registry: Dict[str, str] = {} # e.g. {"Chapter 1": "completed", "Chapter 2": "pending"}
    asset_manifest: Dict[str, bool] = {} # e.g. {"char_eliot": True}
    recursive_summaries: Dict[int, str] = {} # level 0 (global), 1 (arc), 2 (prev chapter)
