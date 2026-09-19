import os
import sys
import logging
from dotenv import load_dotenv

# Ensure we can import from local modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.config import ConfigLoader
from utils.crewai_runtime import configure_crewai_runtime


def extract_writing_style(config):
    """Prefer story.content writing settings while keeping legacy fallback support."""
    story_content = config.get("story", {}).get("content", {})
    legacy_writing = config.get("writing", {})
    if not legacy_writing:
        return story_content
    merged = dict(legacy_writing)
    for key, value in story_content.items():
        merged[key] = value
    return merged


def apply_selected_llm_profile(
    config,
    infra,
    llama_controller_cls=None,
    ollama_controller_cls=None,
):
    """Apply the selected LLM profile and manage only local providers."""
    llm_sel = infra.get("llm_selected", "openrouter")
    llm_profile = infra.get("llm_profiles", {}).get(llm_sel)

    if not llm_profile:
        return None

    print(f"🔧 Using LLM Provider: {llm_sel.upper()} ({llm_profile['model']})")

    if "agents" not in config:
        config["agents"] = {}
    if "llm" not in config["agents"]:
        config["agents"]["llm"] = {}

    config["agents"]["llm"]["model"] = llm_profile["model"]
    config["agents"]["llm"]["base_url"] = llm_profile["base_url"]
    config["agents"]["llm"]["temperature"] = llm_profile.get("temperature", 0.7)

    if "api_key" in llm_profile:
        os.environ["OPENAI_API_KEY"] = llm_profile["api_key"]

    provider_kind = llm_profile.get("provider_kind", "")
    is_llama_local = provider_kind == "llama_cpp_local" or (
        not provider_kind and "llama_cp" in llm_sel.lower()
    )
    is_ollama_local = provider_kind == "ollama_local" or (
        not provider_kind and "ollama" in llm_sel.lower()
    )

    if is_llama_local:
        print("⚙️  Initializing LlamaCP Manager...")
        if ollama_controller_cls is None:
            from services.ollama_controller import OllamaController

            ollama_controller_cls = OllamaController
        if llama_controller_cls is None:
            from services.llama_controller import LlamaController

            llama_controller_cls = LlamaController

        try:
            ollama_cfg = infra.get("llm_profiles", {}).get("ollama", {})
            if ollama_cfg and ollama_controller_cls is not None:
                temp_ollama = ollama_controller_cls(ollama_cfg)
                kill_existing_process = getattr(temp_ollama, "kill_existing_process", None)
                if callable(kill_existing_process):
                    kill_existing_process()
        except Exception:
            pass

        controller = llama_controller_cls(llm_profile)
        controller.ensure_server_running()
    elif is_ollama_local:
        print("⚙️  Initializing Ollama Manager...")
        if llama_controller_cls is None:
            from services.llama_controller import LlamaController

            llama_controller_cls = LlamaController
        if ollama_controller_cls is None:
            from services.ollama_controller import OllamaController

            ollama_controller_cls = OllamaController

        try:
            lcp_cfg = infra.get("llm_profiles", {}).get("llama_cp_local", {})
            if lcp_cfg and llama_controller_cls is not None:
                temp_llama = llama_controller_cls(lcp_cfg)
                kill_existing_process = getattr(temp_llama, "kill_existing_process", None)
                if callable(kill_existing_process):
                    kill_existing_process()
        except Exception:
            pass

        controller = ollama_controller_cls(llm_profile)
        controller.start_server()
        controller.load_model()

    return llm_profile


def kickoff():
    print("==========================================")
    print("   🤖 ILLUSTRATED BOOK WRITER AGENT 🤖   ")
    print("==========================================")
    
    # Load Environment
    # main.py is in src/, so we go up 4 levels to get to repo root (src -> 05 -> examples -> Crewai)
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    example_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dotenv_path = os.path.join(repo_root, ".env")
    load_dotenv(dotenv_path=dotenv_path, override=True)
    runtime_info = configure_crewai_runtime(os.path.join(example_root, "outputs", "_crewai_runtime"))
    print(f"🗂️  CrewAI runtime redirected to: {runtime_info['runtime_root']}")

    from core.flow import IllustratedBookFlow

    try:
        # Load Config
        config = ConfigLoader.load_config()
        
        # [INTEGRATION] Apply Infrastructure Configuration (YAML)
        infra = config.get("infrastructure", {})
        
        # 1. LLM Setup
        apply_selected_llm_profile(config, infra)


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
        writing_style_cfg = extract_writing_style(config)

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
            "writing_style": writing_style_cfg,
            
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
