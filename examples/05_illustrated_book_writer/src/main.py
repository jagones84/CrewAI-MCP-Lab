import os
import sys
import logging
from dotenv import load_dotenv

# Ensure we can import from local modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.config import ConfigLoader
from core.flow import IllustratedBookFlow
from services.llama_controller import LlamaController
from services.ollama_controller import OllamaController

def kickoff():
    print("==========================================")
    print("   🤖 ILLUSTRATED BOOK WRITER AGENT 🤖   ")
    print("==========================================")
    
    # Load Environment
    # main.py is in src/, so we go up 4 levels to get to repo root (src -> 05 -> examples -> Crewai)
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    dotenv_path = os.path.join(repo_root, ".env")
    load_dotenv(dotenv_path=dotenv_path, override=True)
    os.environ["CREWAI_TRACING_ENABLED"] = "true"

    try:
        # Load Config
        config = ConfigLoader.load_config()
        
        # [INTEGRATION] Apply Infrastructure Configuration (YAML)
        infra = config.get("infrastructure", {})
        
        # 1. LLM Setup
        llm_sel = infra.get("llm_selected", "openrouter")
        llm_profile = infra.get("llm_profiles", {}).get(llm_sel)
        
        if llm_profile:
            print(f"🔧 Using LLM Provider: {llm_sel.upper()} ({llm_profile['model']})")
            
            # Ensure agents config exists
            if "agents" not in config: config["agents"] = {}
            if "llm" not in config["agents"]: config["agents"]["llm"] = {}
            
            # Apply Profile
            config["agents"]["llm"]["model"] = llm_profile["model"]
            config["agents"]["llm"]["base_url"] = llm_profile["base_url"]
            config["agents"]["llm"]["temperature"] = llm_profile.get("temperature", 0.7)
            
            # Handle API Key
            if "api_key" in llm_profile:
                os.environ["OPENAI_API_KEY"] = llm_profile["api_key"]
                
            # [INTEGRATION] Auto-Manage Servers (Mutual Exclusion)
            if "llama_cp" in llm_sel.lower():
                # If using LlamaCP, ensure Ollama is stopped
                print(f"⚙️  Initializing LlamaCP Manager...")
                # Kill Ollama first to free port/resources if needed (though ports differ, VRAM might not)
                # But we don't have Ollama config here easily unless we load it.
                # Let's assume standard port 11434 check.
                # Or better, instantiate OllamaController just to kill.
                try:
                    ollama_cfg = infra.get("llm_profiles", {}).get("ollama", {})
                    if ollama_cfg:
                        temp_ollama = OllamaController(ollama_cfg)
                        temp_ollama.kill_existing_process()
                except:
                    pass

                controller = LlamaController(llm_profile)
                controller.ensure_server_running()

            elif "ollama" in llm_sel.lower():
                # If using Ollama, ensure LlamaCP is stopped
                print(f"⚙️  Initializing Ollama Manager...")
                # Kill LlamaCP first
                try:
                    # We need a LlamaController to kill, but we need config.
                    # Try to find a llama_cp profile to use for kill config
                    lcp_cfg = infra.get("llm_profiles", {}).get("llama_cp_local", {})
                    if lcp_cfg:
                        temp_llama = LlamaController(lcp_cfg)
                        temp_llama.kill_existing_process()
                except:
                    pass

                controller = OllamaController(llm_profile)
                controller.start_server()
                controller.load_model()


        # 2. Image Gen Setup
        img_sel = infra.get("image_selected", "local_standard")
        img_profile = infra.get("image_profiles", {}).get(img_sel)
        
        if img_profile:
            srv = img_profile.get("comfy_server", "comfyui")
            print(f"🎨 Using Image Provider: {img_sel.upper()} (Server: {srv})")
            config["agents"]["comfy_server"] = srv

        # Setup Logging
                
        # Setup Logging
        log_dir = os.path.join(config['project']['root'], "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "session.log")
        
        logging.basicConfig(
            filename=log_file,
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            force=True
        )
        print(f"   📝 Logging to: {log_file}")
        
        # Flatten config for Flow
        # Extract relevant parts (New Schema)
        project_cfg = config.get("project", {})
        book_cfg = config.get("book", {})
        story_cfg = config.get("story", {})
        styles_cfg = config.get("styles", {})
        char_cfg = config.get("characters", {})

        app_config = {
            "project_root": project_cfg.get("root"),
            "title": book_cfg.get("title", "Untitled"),
            "genre": book_cfg.get("genre", "Fiction"),
            "theme": book_cfg.get("theme", "None"),
            "mode": book_cfg.get("mode", "create"),
            "modification_prompt": book_cfg.get("modification_prompt", ""),
            
            # Story Structure
            "target_chapters": story_cfg.get("structure", {}).get("chapters", 5),
            "scenes_per_chapter": story_cfg.get("structure", {}).get("scenes_per_chapter", 4),
            "images_per_chapter": story_cfg.get("structure", {}).get("images_per_chapter", 1),
            
            # Characters (Raw config needed for nesting logic in flow or passing pre-parsed)
            "characters": char_cfg, 
            "char_folder": project_cfg.get("paths", {}).get("characters", "Characters"),
            
            # Paths
            "rag_path": project_cfg.get("paths", {}).get("rag_db", "rag_db"),
            
            # Styles
            "pdf_style": styles_cfg.get("pdf", {}),
            "workflow_name": styles_cfg.get("images", {}).get("workflow", "image_perfectDeliberate_text_to_image_API.json"),
            "writing_style": config.get("writing", {}),
            
            # Agents (Pass raw agents config for BookAgents)
            "agents": config.get("agents", {})
        }

        print(f"🚀 Launching Process for '{app_config['title']}'...")
        
        # Run Flow
        IllustratedBookFlow(initial_config=app_config).kickoff()
        
    except Exception as e:
        print(f"❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    kickoff()
