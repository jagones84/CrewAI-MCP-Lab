from pathlib import Path

import yaml


EXAMPLE_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = EXAMPLE_ROOT / "config"


def load_yaml(file_name: str) -> dict:
    """Load a config YAML file for default-profile assertions."""
    config_path = CONFIG_DIR / file_name
    assert config_path.exists(), f"Missing expected config file: {config_path}"
    return yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}


def assert_dgx_qwen_defaults(config: dict) -> None:
    """Assert that the DGX Qwen tunneled profile is the default provider."""
    infrastructure = config["infrastructure"]

    assert infrastructure["llm_selected"] == "qwen_abliterated_dgx"

    profile = infrastructure["llm_profiles"]["qwen_abliterated_dgx"]
    assert profile["model"] == "qwen-3.6-35b-a3b-claude47-opus-abliterated"
    assert profile["base_url"] == "http://localhost:11003/v1"
    assert profile["api_key"] == "EMPTY"
    assert profile["provider_kind"] == "llama_cpp_remote"


def test_template_config_defaults_to_dgx_qwen():
    assert_dgx_qwen_defaults(load_yaml("config.template.yaml"))


def test_runtime_config_defaults_to_dgx_qwen():
    assert_dgx_qwen_defaults(load_yaml("config.yaml"))
