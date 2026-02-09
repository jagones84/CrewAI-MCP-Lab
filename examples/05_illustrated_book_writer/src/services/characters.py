from pathlib import Path
from typing import List, Dict, Optional
import os

class CharacterManager:
    """Loads and manages character data from character folders."""
    def __init__(self, characters_path: str):
        self.characters_path = Path(characters_path)
        self.characters = {}
        self.portraits_enabled = False
        self.portrait_workflow = ""
        self.portrait_tools = []
        
    def setup_portrait_generation(self, enabled: bool, workflow: str, tools: List):
        """Configure portrait generation settings."""
        self.portraits_enabled = enabled
        self.portrait_workflow = workflow
        self.portrait_tools = tools

    def _extract_appearance(self, background_text: str) -> str:
        """Extract the Appearance section from the background text."""
        try:
            lines = background_text.split('\n')
            appearance = []
            capturing = False
            for line in lines:
                if line.lower().startswith("appearance:"):
                    appearance.append(line.split(":", 1)[1].strip())
                    capturing = True
                elif capturing and (line.lower().startswith("personality:") or line.lower().startswith("role:") or line.lower().startswith("backstory:")):
                    break
                elif capturing:
                    appearance.append(line.strip())
            
            result = " ".join(appearance).strip()
            return result if result else background_text[:300] # Fallback
        except Exception:
            return background_text[:300]

    def _detect_gender(self, text: str) -> str:
        """Detect gender tags based on pronouns and keywords."""
        text = text.lower()
        male_score = text.count(" he ") + text.count(" him ") + text.count(" his ") + text.count(" man ") + text.count(" male ") + text.count(" boy ")
        female_score = text.count(" she ") + text.count(" her ") + text.count(" hers ") + text.count(" woman ") + text.count(" female ") + text.count(" girl ")
        
        if male_score > female_score:
            return "(1boy:1.6), (male:1.5), (masculine features:1.2)"
        elif female_score > male_score:
            return "(1girl:1.6), (female:1.5), (feminine features:1.2)"
        return "(1person:1.4)" # Neutral fallback

    def generate_portraits(self):
        """Generate missing portraits for all loaded characters."""
        if not self.portraits_enabled or not self.portrait_tools:
            print("⏩ Portrait generation disabled or tools missing.")
            return

        print("🎨 Checking Character Portraits...")
        img_tool = next((t for t in self.portrait_tools if "generate_image" in t.name), None)
        if not img_tool:
             print("❌ ComfyUI Image Tool not found!")
             return

        for name, data in self.characters.items():
            char_folder = self.characters_path / name
            portrait_path = char_folder / "portrait.png"
            
            if portrait_path.exists() and portrait_path.stat().st_size > 1024:
                print(f"  ✅ Portrait exists for {name}")
                self.characters[name]['portrait_path'] = str(portrait_path)
                continue
            elif portrait_path.exists():
                print(f"  🗑️ Removing invalid/empty portrait for {name}")
                portrait_path.unlink()
                
            print(f"  🎨 Generating portrait for {name}...")
            
            # Construct Prompt
            # Background is already cleaned up as a string in generate_characters or load_characters
            # Extract Appearance specifically to avoid unrelated details
            appearance_text = self._extract_appearance(data['background'])
            gender_tags = self._detect_gender(data['background'])
            
            prompt = (
                f"(masterpiece, best quality, ultra-detailed:1.3), "
                f"(solo:1.5), {gender_tags}, "
                f"character portrait of {name}, "
                f"({appearance_text}:1.2), "
                f"detailed face, (full body shot:1.1), standing pose, "
                f"cinematic lighting, dramatic atmosphere, highly detailed skin texture, "
                f"8k uhd, dslr, soft lighting, volumetric lighting, sharp focus"
            )
            negative_prompt = (
                "(deformed, blurry, bad anatomy, disfigured, mutated, malformed:1.4), "
                "(extra limbs, extra legs, extra arms, fused fingers, too many fingers, missing fingers:1.4), "
                "long neck, fused body, floating limbs, disconnected limbs, "
                "text, watermark, signature, username, error, jpeg artifacts, "
                "bad hands, low quality, worst quality"
            )
            
            try:
                # Execute Tool
                # Note: Tool execution in CrewAI/LangChain usually expects a string input or specific dict. 
                # Since we have the raw tool instance from MCP, we call it directly if it's a StructuredTool, 
                # or verify how it's wrapped. Assuming standard CrewAI/LangChain Tool invoke.
                
                # Check if we can invoke it
                if hasattr(img_tool, 'run'):
                     # Some MCP tools might need specific arguments mapping
                    result = img_tool.run(
                        workflow_name=self.portrait_workflow,
                        prompt=prompt,
                        negative_prompt=negative_prompt,
                        output_path=str(char_folder / "portrait.png")
                    )
                    
                    # Save Prompt
                    try:
                        prompt_path = char_folder / "portrait_prompt.txt"
                        with open(prompt_path, "w", encoding="utf-8") as f:
                            f.write(f"POSITIVE:\n{prompt}\n\nNEGATIVE:\n{negative_prompt}")
                        print(f"  📝 Prompt saved to {prompt_path}")
                    except Exception as e:
                        print(f"  ⚠️ Failed to save prompt file: {e}")

                    # Check if result indicates success or if we need to simplify
                    print(f"  ✨ Portrait Generated: {result}")
                    self.characters[name]['portrait_path'] = str(portrait_path)
                else:
                    print(f"  ❌ Tool {img_tool.name} has no run method.")

            except Exception as e:
                print(f"  ❌ Failed to generate portrait for {name}: {e}")

        
    def load_characters(self, character_names: List[str]) -> Dict:
        """Load character backgrounds and portraits from folders."""
        for name in character_names:
            char_folder = self.characters_path / name
            if not char_folder.exists():
                print(f"⚠️ Character folder not found: {char_folder}")
                continue
                
            # Load background
            bg_file = char_folder / "background.md"
            portrait_file = self._find_portrait(char_folder)
            
            background = ""
            if bg_file.exists():
                with open(bg_file, 'r', encoding='utf-8') as f:
                    background = f.read()
            
            self.characters[name] = {
                "name": name,
                "background": background,
                "portrait_path": str(portrait_file) if portrait_file else None
            }
            
        return self.characters
    
    def _find_portrait(self, char_folder: Path) -> Optional[Path]:
        """Find portrait image in character folder."""
        for ext in ['.png', '.jpg', '.jpeg']:
            portrait = char_folder / f"portrait{ext}"
            if portrait.exists():
                return portrait
        return None
    
    def get_character_context(self) -> str:
        """Get formatted character information for agent context."""
        if not self.characters:
            return "No predefined characters. Create as needed."
        
        context_parts = ["=== CHARACTER REFERENCE SHEET ==="]
        for name, data in self.characters.items():
            context_parts.append(f"\n## {name}")
            context_parts.append(data['background'])
        
        return "\n".join(context_parts)
