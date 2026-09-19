import yaml
import os
from crewai import LLM
from dotenv import load_dotenv


STALE_OPENROUTER_MODELS = {
    "google/gemini-2.0-flash-001": "google/gemini-2.5-flash-lite",
}

def load_config():
    config_path = os.path.join(os.path.dirname(__file__), "..", "config", "preferences.yaml")
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config not found at {config_path}")
    
    with open(config_path, "r") as f:
        return yaml.safe_load(f)

def get_llm(name="llm"):
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    load_dotenv(os.path.join(repo_root, ".env"), override=True)
    config = load_config()
    llm_config = config.get(name, {})
    
    provider = llm_config.get("provider", "openrouter")
    model = llm_config.get("model", "google/gemini-2.5-flash-lite")
    temperature = llm_config.get("temperature", 0.7)

    if provider == "openrouter":
        model = os.environ.get("OPENROUTER_MODEL") or model
        model = STALE_OPENROUTER_MODELS.get(model, model)
        if model and not model.startswith("openrouter/"):
            model = f"openrouter/{model}"
        api_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENAI_API_KEY")
        if api_key and not os.environ.get("OPENROUTER_API_KEY"):
            os.environ["OPENROUTER_API_KEY"] = api_key
        os.environ.pop("OPENAI_API_BASE", None)
        return LLM(
            model=model,
            api_key=api_key,
            temperature=temperature,
        )

    return LLM(
        model=f"{provider}/{model}" if provider != "openai" else model,
        temperature=temperature
    )
