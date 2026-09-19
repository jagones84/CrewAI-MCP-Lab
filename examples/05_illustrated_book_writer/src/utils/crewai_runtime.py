from __future__ import annotations

import os
from pathlib import Path

import appdirs


def configure_crewai_runtime(runtime_root: str | Path) -> dict[str, str]:
    """Redirect CrewAI runtime/config paths into a workspace-local directory."""
    root = Path(runtime_root).resolve()
    home_dir = root / "home"
    localappdata_dir = root / "localappdata"
    appdata_dir = root / "appdata"
    config_path = home_dir / ".config" / "crewai" / "settings.json"

    config_path.parent.mkdir(parents=True, exist_ok=True)
    localappdata_dir.mkdir(parents=True, exist_ok=True)
    appdata_dir.mkdir(parents=True, exist_ok=True)

    os.environ["HOME"] = str(home_dir)
    os.environ["USERPROFILE"] = str(home_dir)
    os.environ["LOCALAPPDATA"] = str(localappdata_dir)
    os.environ["APPDATA"] = str(appdata_dir)
    os.environ["CREWAI_TRACING_ENABLED"] = "false"
    os.environ["OTEL_SDK_DISABLED"] = "true"
    os.environ["LITELLM_SUCCESS_CALLBACKS"] = ""
    os.environ["LITELLM_FAILURE_CALLBACKS"] = ""
    os.environ.pop("AGENTOPS_API_KEY", None)

    def _workspace_user_data_dir(
        appname: str | None = None,
        appauthor: str | None = None,
        version: str | None = None,
        roaming: bool = False,
    ) -> str:
        base = localappdata_dir / (appauthor or "CrewAI") / (appname or "default")
        if version:
            base = base / version
        base.mkdir(parents=True, exist_ok=True)
        return str(base)

    appdirs.user_data_dir = _workspace_user_data_dir
    appdirs.user_cache_dir = _workspace_user_data_dir

    return {
        "runtime_root": str(root),
        "home": str(home_dir),
        "localappdata": str(localappdata_dir),
        "appdata": str(appdata_dir),
        "config_path": str(config_path),
    }
