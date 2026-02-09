import os

class WorldBible:
    def __init__(self, assets_dir):
        self.assets_dir = assets_dir
        self.glossary_path = os.path.join(assets_dir, "glossary.md")
        self.rules_path = os.path.join(assets_dir, "universe_rules.md")
        self._ensure_files_exist()

    def _ensure_files_exist(self):
        os.makedirs(self.assets_dir, exist_ok=True)
        
        if not os.path.exists(self.glossary_path):
            with open(self.glossary_path, "w", encoding="utf-8") as f:
                f.write("# Stylistic Glossary\n\n- Use active voice.\n- Avoid clichés.\n")
                
        if not os.path.exists(self.rules_path):
            with open(self.rules_path, "w", encoding="utf-8") as f:
                f.write("# Universe Rules\n\n- Gravity works comfortably.\n- No FTL travel.\n")

    def get_context(self):
        context = []
        
        if os.path.exists(self.glossary_path):
            with open(self.glossary_path, "r", encoding="utf-8") as f:
                context.append(f"STYLISIC GUIDELINES:\n{f.read()}")
                
        if os.path.exists(self.rules_path):
            with open(self.rules_path, "r", encoding="utf-8") as f:
                context.append(f"UNIVERSE RULES:\n{f.read()}")
                
        return "\n\n".join(context)
