import os
import json
import shutil
import yaml
from datetime import datetime
from pathlib import Path
from crewai.flow.flow import Flow, start, listen
from crewai import Crew

from .state import BookState
from services.rag import KnowledgeBase
from services.pdf_generator import PDFBook, FPDF, clean_text
from services.characters import CharacterManager
from services.bible import WorldBible

from agents.agents import BookAgents
from agents.tasks import BookTasks

class IllustratedBookFlow(Flow[BookState]):
    
    def __init__(self, initial_config=None):
        super().__init__()
        self.config = initial_config
        # Pass config to Agents for model selection
        self.agents = BookAgents(config=self.config)
        # Initialize tools (SSH + MCP)
        self.agents.initialize_tools()
        
        self.tasks = BookTasks()
        
        # Apply config to State
        if initial_config:
            self._apply_config(initial_config)
            
        # Set up paths
        self._setup_paths(initial_config)

        # Save Config to Output
        self._save_run_config()
        
        # Init Subsystems
        self.kb = KnowledgeBase(book_title=self.state.title, db_path=self.state.rag_path)
        self.bible = WorldBible(assets_dir=os.path.join(self.output_dir, "assets"))
        
        # Load characters if specified
        self._init_characters(initial_config)

        # Attempt to load state
        self.load_state()
        
        # Reconcile config with loaded state
        if initial_config:
            self._reconcile_state(initial_config)

    def _apply_config(self, cfg):
        self.state.title = cfg.get("title", "Untitled")
        self.state.genre = cfg.get("genre", "Fiction")
        self.state.theme = cfg.get("theme", "None")
        self.state.target_chapters = cfg.get("target_chapters", 5)
        self.state.scenes_per_chapter = cfg.get("scenes_per_chapter", 4)
        self.state.images_per_chapter = cfg.get("images_per_chapter", 1)
        self.state.mode = cfg.get("mode", "create")
        self.state.modification_prompt = cfg.get("modification_prompt", "")
        self.state.workflow_name = cfg.get("workflow_name", "image_perfectDeliberate_text_to_image_API.json")
        self.state.action = cfg.get("action", "generate_book")
        self.state.regen_images = cfg.get("regen_images", False)
        self.state.regen_chapters = cfg.get("regen_chapters", [])
        
        # Styles
        pdf_style = cfg.get("pdf_style", {})
        print(f"DEBUG: pdf_style = {pdf_style}")
        self.state.pdf_bg_color = tuple(pdf_style.get("bg_color", (10,5,5)))
        self.state.pdf_text_color = tuple(pdf_style.get("text_color", (220,220,220)))
        self.state.pdf_line_spacing = pdf_style.get("line_spacing", 5)
        self.state.pdf_font_body = pdf_style.get("font_body", "times")
        self.state.pdf_font_header = pdf_style.get("font_header", "times")
        
        # Writing
        w_style = cfg.get("writing_style", {})
        self.state.target_word_count = w_style.get("word_count", 700)
        self.state.language = w_style.get("language", "English")

    def _setup_paths(self, cfg):
        # Force project to live in its own subdirectory inside 'outputs' to prevent root clutter
        safe_title = "".join([c if c.isalnum() else "_" for c in self.state.title]).strip()
        
        # Robust pathing: find current project root relative to this file
        # flow.py is in src/modules/flow.py
        current_file = Path(__file__).resolve()
        project_root = current_file.parent.parent.parent
        
        # If we are in 'src', go one more up if it's the 05_... folder
        if project_root.name == "src":
            project_root = project_root.parent
            
        self.output_dir = os.path.join(project_root, "outputs", safe_title)
        self.state.rag_path = os.path.join(self.output_dir, cfg.get("rag_path", "rag_db"))
        self.project_root = project_root
        os.makedirs(self.output_dir, exist_ok=True)

    def _save_run_config(self):
        """Saves the configuration used for this run to the output directory."""
        if not self.output_dir or not self.config:
            return
            
        try:
            # 1. Save the parsed/merged config object as JSON/YAML
            dump_path = os.path.join(self.output_dir, "run_config.yaml")
            with open(dump_path, "w", encoding="utf-8") as f:
                yaml.dump(self.config, f, default_flow_style=False)
            print(f"📄 Saved Run Configuration to: {dump_path}")
            
            # 2. Try to copy the original config file if it exists
            # Assuming standard location: project_root/config/config.yaml
            if hasattr(self, 'project_root'):
                src_config = os.path.join(self.project_root, "config", "config.yaml")
                if os.path.exists(src_config):
                    shutil.copy2(src_config, os.path.join(self.output_dir, "original_config.yaml"))
        except Exception as e:
            print(f"⚠️ Failed to save run config: {e}")

    def _init_characters(self, cfg):
        if cfg and cfg.get("characters"):
            char_folder = os.path.join(self.output_dir, cfg.get("char_folder", "Characters"))
            self.char_manager = CharacterManager(char_folder)
            char_cfg = cfg.get("characters", {})
            predefined = char_cfg.get("predefined", {})
            chars_list = predefined.get("main", []) + predefined.get("supporting", [])
            self.char_manager.load_characters(chars_list)
            
            # Setup Portrait Generation
            portrait_cfg = cfg.get("characters", {}).get("portraits", {})
            self.char_manager.setup_portrait_generation(
                enabled=portrait_cfg.get("enabled", False),
                workflow=portrait_cfg.get("workflow", ""),
                tools=self.agents.comfy_tools
            )
            
            self.state.character_context = self.char_manager.get_character_context()
            print(f"📚 Loaded {len(self.char_manager.characters)} characters")
        else:
            self.char_manager = None

    def save_state(self):
        file_path = os.path.join(self.output_dir, "book_state.json")
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(self.state.json())
        except Exception as e:
            print(f"❌ Failed to save state: {e}")

    def load_state(self):
        file_path = os.path.join(self.output_dir, "book_state.json")
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # We only restore content-related state, config is handled by _reconcile_state
                    self.state.outline = data.get("outline", [])
                    self.state.book_content = data.get("book_content", [])
                    self.state.last_summary = data.get("last_summary", "")
                    self.state.master_plot = data.get("master_plot", "")
                    self.state.character_context = data.get("character_context", "")
                    # Load State Machine Registry
                    self.state.chapter_registry = data.get("chapter_registry", {})
                    self.state.recursive_summaries = {int(k): v for k, v in data.get("recursive_summaries", {}).items()}
                    print(f"📂 State loaded from {file_path}")
            except Exception as e:
                 print(f"❌ Failed to load state: {e}")

    def _validate_preflight(self):
        """Ensure environment is healthy before starting generation."""
        print("🛡️ Running Pre-flight Validation...")
        # 1. Check consistency of registry vs outline
        for ch in self.state.outline:
            title = ch['title']
            status = self.state.chapter_registry.get(title, "pending")
            if status == "completed":
                # Verify content actually exists
                content = next((c for c in self.state.book_content if c['title'] == title), None)
                if not content or not content.get("scenes"):
                    print(f"  ⚠️ Inconsistency found: '{title}' marked completed but has no content. Reverting to pending.")
                    self.state.chapter_registry[title] = "pending"
        
        # 2. Check Assets (Example placeholder)
        # if not os.path.exists(self.state.assets_path): ...
        print("  ✅ Validation complete.")

    def _reconcile_state(self, cfg):
        """Reconcile initial config with loaded state to detect changes."""
        print("🔄 Reconciling Config with State...")
        
        # 1. Check for additional chapters
        target = cfg.get("target_chapters", self.state.target_chapters)
        if len(self.state.outline) > 0 and target > len(self.state.outline):
            diff = target - len(self.state.outline)
            print(f"📈 DETECTED: Expansion needed (+{diff} chapters)")
            # We don't call the task here, we'll handle it in generate_outline logic or a separate start
            self.state.target_chapters = target
            
        # 2. Check for character updates
        if cfg.get("characters"):
             predefined = cfg.get("characters", {}).get("predefined", {})
             all_predefined = predefined.get("main", []) + predefined.get("supporting", [])
             
             # If we have characters in config but state context is old/empty/missing some
             # We trigger a refresh if the context doesn't mention some predefined names
             missing = [name for name in all_predefined if name not in self.state.character_context]
             if missing:
                 print(f"👥 DETECTED: New characters in config: {missing}")
                 # Clearing context forces regeneration including the new ones
                 # Or we could just append, but regenerate_characters is cleaner for consistency
                 self.state.character_context = "" 

        # 3. Update style/modes from config
        self.state.mode = cfg.get("mode", self.state.mode)
        self.state.action = cfg.get("action", self.state.action)
        self.state.modification_prompt = cfg.get("modification_prompt", self.state.modification_prompt)
        self.state.regen_images = cfg.get("regen_images", self.state.regen_images)
        self.state.regen_chapters = cfg.get("regen_chapters", self.state.regen_chapters)

        # 4. Sync Characters (Cleanup & Generate)
        self._sync_characters()
        
        # 5. Run Validation
        self._validate_preflight()

    def _sync_characters(self):
        print("🔄 Syncing Character Directories & Portraits...")
        
        # 1. Identify Active Characters
        active_names = []
        if self.state.character_context:
            for line in self.state.character_context.split('\n'):
                if line.strip().startswith("## "):
                    active_names.append(line.strip()[3:].strip())
        
        # Fallback to config if state is empty/cleared
        if not active_names and self.config:
             char_cfg = self.config.get("characters", {})
             predefined = char_cfg.get("predefined", {})
             active_names = predefined.get("main", []) + predefined.get("supporting", [])

        if not active_names:
            print("   ⚠️ No active characters found to sync.")
            return

        print(f"   👥 Active Characters: {active_names}")

        # 2. Cleanup Directory
        char_root = os.path.join(self.output_dir, "Characters")
        if os.path.exists(char_root):
            for item in os.listdir(char_root):
                item_path = os.path.join(char_root, item)
                # Remove if it is a directory and NOT in the active list
                if os.path.isdir(item_path) and item not in active_names:
                    print(f"   🗑️ Removing orphaned folder: {item}")
                    try:
                        shutil.rmtree(item_path)
                    except Exception as e:
                        print(f"     ! Failed to delete {item}: {e}")

        # 3. Trigger Portrait Generation
        # Ensure Manager is ready
        if not self.char_manager:
            self.char_manager = CharacterManager(char_root)
            self.char_manager.load_characters(active_names)
        else:
            # Refresh loaded characters just in case
             self.char_manager.load_characters(active_names)

        # Ensure tools are configured
        if self.agents and hasattr(self.agents, 'comfy_tools'):
             self.char_manager.setup_portrait_generation(
                enabled=True,
                workflow=self.state.workflow_name,
                tools=self.agents.comfy_tools
            )
             self.char_manager.generate_portraits()
        else:
            print("   ⚠️ Agents/Tools not initialized, skipping portrait sync.")

    @start()
    def generate_characters(self):
        """Generate characters before the story begins."""
        if self.state.mode == "modify":
            return
            
        if hasattr(self.state, 'action') and self.state.action == "regenerate_pdf":
            print(f"⏩ Skipping Character Generation (Regenerate PDF Only)")
            return
            
        # Resume Check
        if self.state.character_context and len(self.state.character_context) > 50:
             print(f"⏩ Resuming: Characters already generated.")
             if self.char_manager:
                 self.char_manager.generate_portraits()
             return

        print(f"👥 Generating Characters for '{self.state.title}'...")

    # ... (rest of function omitted for brevity in instruction, but since this is a specific block replace, I focus on the start of the function)
    # Wait, replace_file_content needs strict matching. I should do them as multiple chunks or separate calls if the lines are far apart.
    # The functions are sequential. I can probably do it in one or multiple chunks.

    # Chunk 1: generate_characters
    # Chunk 2: generate_master_plot
    # Chunk 3: generate_outline
    
    # I cannot define the replacement content in the instruction. I must provide the chunks.
    # Since I need to construct the chunks carefully, I will focus on one chunk per function to be safe.
    # Actually, let's look at the file lines again from previous turn.
    # generate_characters @ 131
    # generate_master_plot @ 230
    # generate_outline @ 254
    
    # I will use multi_replace_file_content if available? 
    # Yes, default_api:multi_replace_file_content is available.
    
    # Chunk 1 - generate_characters
    # Chunk 2 - generate_master_plot
    # Chunk 3 - generate_outline

        
        architect = self.agents.story_architect()
        illustrator = self.agents.illustrator()
        
        # Get count and names from config
        char_count = 4
        mandatory_names = []
        if self.config:
            char_cfg = self.config.get("characters", {})
            char_count = char_cfg.get("generation", {}).get("count", 4)
            predefined = char_cfg.get("predefined", {})
            mandatory_names = predefined.get("main", []) + predefined.get("supporting", [])
        
        design_task = self.tasks.character_design_task(
            architect, 
            genre=self.state.genre, 
            theme=self.state.theme,
            count=char_count,
            mandatory_names=mandatory_names
        )
        
        crew = Crew(agents=[architect], tasks=[design_task], verbose=True)
        try:
            res = str(crew.kickoff())
            res = res.replace("```json", "").replace("```", "").strip()
            if "{" in res:
                res = res[res.find("{"):res.rfind("}")+1]
            
            char_data = json.loads(res).get("characters", [])
            print(f"✅ Created {len(char_data)} character profiles.")
            
            # Context builder
            context_parts = ["=== CHARACTER REFERENCE SHEET ==="]
            
            # Folder setup
            char_root = os.path.join(self.output_dir, "Characters")
            os.makedirs(char_root, exist_ok=True)
            
            for char in char_data:
                name = char['name']
                print(f"  > Processing {name}...")
                
                c_folder = os.path.join(char_root, name)
                os.makedirs(c_folder, exist_ok=True)
                
                # Cleanup appearance/personality if they are dicts from LLM
                appearance = char['appearance']
                if isinstance(appearance, dict):
                    appearance = ", ".join([f"{k}: {v}" for k, v in appearance.items()])
                
                personality = char['personality']
                if isinstance(personality, dict):
                    personality = ", ".join([f"{k}: {v}" for k, v in personality.items()])

                # Save Background
                full_bio = f"Role: {char['role']}\nAppearance: {appearance}\nPersonality: {personality}\nBackstory: {char['backstory']}"
                with open(os.path.join(c_folder, "background.md"), "w", encoding="utf-8") as f:
                    f.write(full_bio)
                    
                context_parts.append(f"\n## {name}")
                context_parts.append(full_bio)
                
                # Generate Portrait
                print(f"    > Generating portrait prompt...")
                portrait_task = self.tasks.character_portrait_task(illustrator, char)
                prompt_output = str(Crew(agents=[illustrator], tasks=[portrait_task]).kickoff())
                
                # Parse positive and negative prompts
                positive_prompt = prompt_output
                negative_prompt = ""
                
                if "POSITIVE PROMPT:" in prompt_output and "NEGATIVE PROMPT:" in prompt_output:
                    parts = prompt_output.split("NEGATIVE PROMPT:")
                    positive_prompt = parts[0].replace("POSITIVE PROMPT:", "").strip()
                    negative_prompt = parts[1].strip()
                    print(f"    📝 Parsed prompts (Pos: {len(positive_prompt)} chars, Neg: {len(negative_prompt)} chars)")
                else:
                    print(f"    ⚠️ Warning: Prompt not in expected format, using as-is")
                
                # Validate character name in prompt
                if name.lower() not in positive_prompt.lower():
                    print(f"    ⚠️ Warning: Character name '{name}' not found in prompt")
                
                # Call ComfyUI
                print(f"    > Generating image (ComfyUI)...")
                target_img = os.path.join(c_folder, "portrait.png")
                
                try:
                    gen_tool = None
                    print(f"    🔍 Looking for 'generate_image' in {len(self.agents.comfy_tools)} tools:")
                    for tool in self.agents.comfy_tools:
                        print(f"       - Available Tool: {tool.name}")
                        if "generate_image" in tool.name:
                            gen_tool = tool
                            break
                    
                    if gen_tool:
                        # Try to pass negative prompt if tool supports it
                        try:
                            gen_tool._run(
                                workflow_name=self.state.workflow_name,
                                prompt=positive_prompt,
                                negative_prompt=negative_prompt,
                                output_path=target_img
                            )
                            print(f"    ✅ Portrait saved with negative prompt.")
                        except TypeError:
                            # Fallback if tool doesn't support negative_prompt parameter
                            print(f"    ℹ️ Tool doesn't support negative_prompt, using positive only")
                            gen_tool._run(
                                workflow_name=self.state.workflow_name,
                                prompt=positive_prompt,
                                output_path=target_img
                            )
                            print(f"    ✅ Portrait saved.")
                    else:
                        print("    ⚠️ ComfyUI tool not found.")
                except Exception as e:
                    print(f"    ❌ Portrait generation failed: {e}")
            
            self.state.character_context = "\n".join(context_parts)
            
            # Trigger Portrait Generation for new characters (and existing if missing)
            if self.char_manager:
                self.char_manager.generate_portraits()
                
            self.save_state()
            
        except Exception as e:
            print(f"❌ Character Generation Error: {e}")
            self.state.character_context = f"Characters for a {self.state.genre} story with theme {self.state.theme}."

    @listen(generate_characters)
    def generate_master_plot(self):
        if self.state.mode == "modify": return
        
        if hasattr(self.state, 'action') and self.state.action == "regenerate_pdf":
            print(f"⏩ Skipping Master Plot (Regenerate PDF Only)")
            return

        # Resume Check
        if self.state.master_plot and len(self.state.master_plot) > 50:
            print(f"⏩ Resuming: Master Plot already exists.")
            return
        
        print(f"🎬 Creating Master Plot for '{self.state.title}'...")
        architect = self.agents.story_architect()
        
        task = self.tasks.master_plot_task(
            architect,
            title=self.state.title,
            genre=self.state.genre,
            theme=self.state.theme,
            character_context=self.state.character_context
        )
        
        crew = Crew(agents=[architect], tasks=[task], verbose=True)
        try:
            master_plot_text = str(crew.kickoff())
            self.state.master_plot = master_plot_text
            self.save_state()
        except Exception as e:
            print(f"❌ Master Plot Error: {e}")
            self.state.master_plot = f"A {self.state.genre} story set in a world themed around {self.state.theme}."
    
    @listen(generate_master_plot)
    def generate_outline(self):
        # Action Check
        if hasattr(self.state, 'action') and self.state.action == "regenerate_pdf":
            print(f"⏩ Skipping Outline (Regenerate PDF Only)")
            return

        architect = self.agents.story_architect()
        
        # Determine Mode
        needs_extension = len(self.state.outline) > 0 and self.state.target_chapters > len(self.state.outline)
        
        if self.state.mode == "modify":
            print(f"🔧 MODIFICATION MODE: {self.state.modification_prompt}")
            task = self.tasks.update_outline_task(
                architect, 
                current_outline=json.dumps(self.state.outline, indent=2),
                modification_prompt=self.state.modification_prompt
            )
        elif needs_extension:
            print(f"📈 EXTENSION MODE: Adding chapters up to {self.state.target_chapters}")
            task = self.tasks.extend_outline_task(
                architect,
                current_outline=json.dumps(self.state.outline, indent=2),
                target_chapters=self.state.target_chapters,
                master_plot=self.state.master_plot
            )
        else:
            # Resume Check
            if self.state.outline and len(self.state.outline) > 0:
                 print(f"⏩ Resuming: Outline already exists.")
                 return
                 
            print(f"✨ CREATION MODE: {self.state.target_chapters} Chapters")
            task = self.tasks.structure_task(
                architect, 
                genre=f"{self.state.genre} - Theme: {self.state.theme}", 
                title=self.state.title, 
                chapter_count=self.state.target_chapters,
                master_plot=self.state.master_plot,
                character_context=self.state.character_context
            )
        
        print(f"Creating/Updating Outline for '{self.state.title}'...")
        crew = Crew(agents=[architect], tasks=[task], verbose=True)
        try:
            res_raw = str(crew.kickoff())
            res_raw = res_raw.replace("```json", "").replace("```", "").strip()
            if "{" in res_raw:
                res_raw = res_raw[res_raw.find("{"):res_raw.rfind("}")+1]
            
            res = json.loads(res_raw)
            self.state.outline = res.get("outline", [])
            self.save_state()
        except Exception as e:
            print(f"❌ Outline Generation Error: {e}")
            if not self.state.outline:
                self.state.outline = [{"chapter": 1, "title": "Start", "summary": "Begin.", "status": "pending"}]

    @listen(generate_outline)
    def production_loop(self):
        # Action Check
        if hasattr(self.state, 'action') and self.state.action == "regenerate_pdf":
            print(f"⏩ Skipping Production Loop (Regenerate PDF Only)")
            return

        img_dir = os.path.join(self.output_dir, "images")
        os.makedirs(img_dir, exist_ok=True)
        
        mgr = self.agents.continuity_manager()
        architect = self.agents.story_architect()
        writer = self.agents.chapter_writer()
        editor = self.agents.editor()
        illustrator = self.agents.illustrator()
        
        # Get Static Context
        bible_ctx = self.bible.get_context()
        
        for index, ch in enumerate(self.state.outline):
            print(f"\n=== CHAPTER {ch['chapter']}: {ch['title']} ===")
            
            # --- STATE MACHINE CHECK ---
            reg_status = self.state.chapter_registry.get(ch['title'], "pending")
            
            # Force Regen Check
            if ch['chapter'] in self.state.regen_chapters:
                print(f"  🔄 Forced Regeneration active for Chapter {ch['chapter']}")
                reg_status = "pending"
            
            if reg_status == "completed":
                print(f"  ✅ Chapter {ch['chapter']} is COMPLETED in Registry. Skipping.")
                continue
            
            print(f"  ⚙️ Status: {reg_status.upper()} -> Starting Generation...")
            
            # Atomic Cleanup: If we are here, we are rewriting the chapter.
            # Remove any existing content for this chapter to avoid duplicates/corruption.
            self.state.book_content = [c for c in self.state.book_content if c['title'] != ch['title']]
            
            # Context Preparation (Rolling Context)
            query_content = f"{ch['title']} {ch['summary']}"
            ctx = self.kb.query_context(query_content)
            
            # Recursive Summaries
            # Level 0: Master Plot (Global)
            # Level 1: Arc Summary (Last 3 chapters? For now just master plot or specific field)
            # Level 2: Previous Chapter Summary
            
            prev_ch_idx = ch['chapter'] - 1
            recent_summary = self.state.recursive_summaries.get(prev_ch_idx, "Start of story.")
            # For Arc, we could synthesize summaries of 1-(N-1). For now using Master Plot as proxy.
            
            # Breakdown
            breakdown_task = self.tasks.breakdown_chapter_task(architect, ch, ctx, scene_count=self.state.scenes_per_chapter)
            try:
                raw_json = str(Crew(agents=[architect], tasks=[breakdown_task]).kickoff())
                raw_json = raw_json.replace("```json", "").replace("```", "").strip()
                if "{" in raw_json: raw_json = raw_json[raw_json.find("{"):raw_json.rfind("}")+1]
                scenes_data = json.loads(raw_json).get("scenes", [])
            except Exception as e:
                print(f"  ! Breakdown failed ({e})")
                scenes_data = [{"number": 1, "name": "Event", "description": ch['summary'], "setting": "Unknown", "emotional_beat": "Neutral"}]

            # Writing/Illustrating Loop
            total_scenes = len(scenes_data)
            target_imgs = self.state.images_per_chapter
            img_indices = set()
            if target_imgs > 0 and total_scenes > 0:
                step = max(1, total_scenes / (target_imgs + 1))
                for i in range(target_imgs):
                    img_indices.add(int((i + 1) * step) - 1)
            
            chapter_full_text = ""
            current_scene_text = ""
            final_scenes_storage = []
            
            for idx, scene in enumerate(scenes_data):
                print(f"\n  -- Scene {scene['number']}: {scene['name']} --")
                
                # Briefing with ENRICHED CONTEXT
                brief_task = self.tasks.briefing_task(
                    mgr, ch, ctx, 
                    recursive_summaries={2: recent_summary, 1: self.state.master_plot},
                    world_bible_context=bible_ctx
                )
                brief = str(Crew(agents=[mgr], tasks=[brief_task]).kickoff())
                
                # Write
                write_task = self.tasks.write_scene_task(
                    writer, scene, brief, chapter_full_text,
                    character_context=self.state.character_context,
                    word_count=self.state.target_word_count
                )
                draft = str(Crew(agents=[writer], tasks=[write_task]).kickoff())
                
                # Critique with BIBLE
                critique_task = self.tasks.critique_scene_task(editor, draft, world_bible_context=bible_ctx)
                feedback = str(Crew(agents=[editor], tasks=[critique_task]).kickoff())
                
                # Revise
                if "APPROVED" not in feedback:
                    revise_task = self.tasks.revise_scene_task(writer, draft, feedback, word_count=self.state.target_word_count)
                    final_text = str(Crew(agents=[writer], tasks=[revise_task]).kickoff())
                    final_text = clean_text(final_text)
                else:
                    final_text = clean_text(draft)
                
                current_scene_text = final_text
                chapter_full_text += f"\n\n### {scene['name']}\n{final_text}"
                
                # Illustration Logic (Preserved)
                final_img_path = None
                if idx in img_indices:
                    img_filename = f"ch_{ch['chapter']}_sc_{scene['number']}.png"
                    target_path = os.path.join(img_dir, img_filename)
                    
                    if os.path.exists(target_path) and os.path.getsize(target_path) > 1024 and not self.state.regen_images:
                        final_img_path = target_path
                    else:
                        print(f"    🎨 Generating illustration...")
                        prompt_task = self.tasks.illustration_task(
                            illustrator, ch, final_text, target_path,
                            character_context=self.state.character_context
                        )
                        prompt_output = str(Crew(agents=[illustrator], tasks=[prompt_task]).kickoff()).strip()
                        
                        # Parse positive and negative prompts
                        positive_prompt = prompt_output
                        negative_prompt = ""
                        
                        if "POSITIVE PROMPT:" in prompt_output and "NEGATIVE PROMPT:" in prompt_output:
                            parts = prompt_output.split("NEGATIVE PROMPT:")
                            positive_prompt = parts[0].replace("POSITIVE PROMPT:", "").strip()
                            negative_prompt = parts[1].strip()
                        
                        # --- Gender Injection for Scenes ---
                        scene_gender_tags = []
                        context_lower = self.state.character_context.lower()
                        
                        for line in self.state.character_context.split('\n'):
                            if line.strip().startswith("## "):
                                char_name = line.strip()[3:].strip()
                                if char_name in positive_prompt:
                                    char_bio_start = context_lower.find(f"## {char_name.lower()}")
                                    char_bio = context_lower[char_bio_start:char_bio_start+1000] if char_bio_start != -1 else ""
                                    
                                    m_score = char_bio.count(" he ") + char_bio.count(" him ") + char_bio.count(" man ") + char_bio.count(" male ")
                                    f_score = char_bio.count(" she ") + char_bio.count(" her ") + char_bio.count(" woman ") + char_bio.count(" female ")
                                    
                                    if m_score > f_score:
                                        scene_gender_tags.append("(1boy:1.4), (male:1.3)")
                                    elif f_score > m_score:
                                        scene_gender_tags.append("(1girl:1.4), (female:1.3)")
                        
                        gender_inject = ", ".join(set(scene_gender_tags)) if scene_gender_tags else "(solo:1.4), (1person:1.3)"
                        if len(scene_gender_tags) > 1:
                            gender_inject = ", ".join(set(scene_gender_tags))

                        # Apply High-Quality Template
                        positive_prompt = (
                            f"(masterpiece, best quality, ultra-detailed:1.3), "
                            f"{gender_inject}, "
                            f"({positive_prompt}:1.2), "
                            f"(cinematic lighting, dramatic atmosphere, detailed background:1.1), "
                            f"8k uhd, dslr, soft lighting, volumetric lighting, sharp focus, intricate details"
                        )
                        
                        if not negative_prompt:
                            negative_prompt = (
                                "(deformed, blurry, bad anatomy, disfigured, mutated, malformed:1.4), "
                                "(extra limbs, extra legs, extra arms, fused fingers, too many fingers, missing fingers:1.4), "
                                "long neck, fused body, floating limbs, disconnected limbs, "
                                "text, watermark, signature, username, error, jpeg artifacts, "
                                "bad hands, low quality, worst quality"
                            )
                        else:
                            negative_prompt = (
                                f"(deformed, blurry, bad anatomy, disfigured:1.4), {negative_prompt}, "
                                "(extra limbs, extra legs, extra arms, missing fingers:1.4), "
                                "text, watermark, signature, bad hands"
                            )
                        
                        # Save Prompt to File
                        prompt_filename = f"ch_{ch['chapter']}_sc_{scene['number']}_prompt.txt"
                        prompt_path = os.path.join(img_dir, prompt_filename)
                        try:
                            with open(prompt_path, "w", encoding="utf-8") as pf:
                                pf.write(f"POSITIVE PROMPT:\n{positive_prompt}\n\nNEGATIVE PROMPT:\n{negative_prompt}")
                            print(f"    📝 Chapter prompt saved to {prompt_filename}")
                        except Exception as e:
                            print(f"    ⚠️ Failed to save chapter prompt: {e}")

                        try:
                            gen_tool = None
                            for tool in self.agents.comfy_tools:
                                if tool.name == "generate_image":
                                    gen_tool = tool
                                    break
                            
                            if gen_tool:
                                try:
                                    gen_tool.run(
                                        workflow_name=self.state.workflow_name,
                                        prompt=positive_prompt,
                                        negative_prompt=negative_prompt,
                                        output_path=target_path
                                    )
                                except TypeError:
                                    gen_tool.run(
                                        workflow_name=self.state.workflow_name,
                                        prompt=positive_prompt,
                                        output_path=target_path
                                    )
                                
                                if os.path.exists(target_path):
                                    final_img_path = target_path
                        except Exception as e:
                            print(f"       ⚠️ ComfyUI generation failed: {e}")
                
                final_scenes_storage.append({
                    "title": scene['name'],
                    "text": final_text,
                    "image": final_img_path
                })
            
            # Store Chapter (Atomic Update)
            new_entry = {"title": ch['title'], "scenes": final_scenes_storage}
            self.state.book_content.append(new_entry)
            
            # Update Registry
            self.state.chapter_registry[ch['title']] = "completed"
            
            # Update Recursive Summary
            self.state.recursive_summaries[ch['chapter']] = current_scene_text[-500:] # Naive summary for now, ideally generated
            self.state.last_summary = f"End of Chap {ch['chapter']}: " + current_scene_text[-200:]
            
            self.kb.add_narrative(chapter_full_text, ch['title'], ch['summary'])
            self._save_progress()
            self.save_state()

    def _save_progress(self):
        safe_title = "".join([c if c.isalnum() else "_" for c in self.state.title]).strip()
        progress_path = os.path.join(self.output_dir, f"{safe_title}.md")
        try:
            with open(progress_path, "w", encoding="utf-8") as f:
                f.write(f"# {self.state.title}\n\n")
                if self.state.character_context:
                    f.write("## Characters\n\n")
                    f.write(self.state.character_context)
                    f.write("\n\n---\n\n")
                for ch in self.state.book_content:
                    f.write(f"## {ch['title']}\n\n")
                    if "scenes" in ch:
                        for scene in ch["scenes"]:
                            if scene.get('image'):
                                f.write(f"![Illustration]({scene['image']})\n\n")
                            f.write(f"### {scene['title']}\n\n")
                            f.write(f"{scene['text']}\n\n")
        except Exception:
            pass

    @listen(production_loop)
    def publish(self):
        print("PUBLISHING PDF...")
        if not FPDF: return

        safe_title = "".join([c if c.isalnum() else "_" for c in self.state.title]).strip()
        pdf_path = os.path.join(self.output_dir, f"{safe_title}.pdf")
        
        pdf = PDFBook(
            book_title=self.state.title, 
            bg_color=self.state.pdf_bg_color, 
            text_color=self.state.pdf_text_color,
            line_spacing=self.state.pdf_line_spacing,
            font_body=self.state.pdf_font_body,
            font_header=self.state.pdf_font_header
        )
        pdf.add_page()
        
        pdf.set_font(self.state.pdf_font_header, 'B', 24)
        safe_text_color = [max(0, min(255, int(c))) if c is not None else 0 for c in self.state.pdf_text_color[:3]]
        pdf.set_text_color(*safe_text_color)
        pdf.cell(0, 60, self.state.title, align='C', ln=True)
        pdf.set_font(self.state.pdf_font_body, '', 14)
        pdf.cell(0, 10, 'A CrewAI Generated Novel', align='C', ln=True)
        
        # Character Profiles
        if self.char_manager:
            pdf.character_profiles(self.char_manager.characters, self.state.character_context)
        else:
            pdf.add_page()
            
        pdf.add_page()
        
        for ch in self.state.book_content:
            pdf.chapter_title(ch['title'])
            if "scenes" in ch:
                 pdf.chapter_body(ch['scenes'])
            
        try:
            pdf.output(pdf_path)
            print(f"🎉 PDF SUCCESS: {os.path.abspath(pdf_path)}")
        except Exception as e:
            print(f"❌ PDF WRITE FAILED: {e}")

        # Move Config (CUT not COPY) to the output directory automatically
        try:
            # flow.py is in src/modules/flow.py, so 3 levels up is the project root
            root_dir = Path(__file__).resolve().parent.parent.parent
            config_src = root_dir / "config.yaml"
            
            if config_src.exists():
                target_config = os.path.join(self.output_dir, "config.yaml")
                if os.path.exists(target_config):
                    os.remove(target_config)
                shutil.copy(str(config_src), target_config)
                print(f"📦 Flow automatically copied config.yaml to {target_config}")
        except Exception as e:
            print(f"⚠️ Failed to move config.yaml automatically: {e}")
