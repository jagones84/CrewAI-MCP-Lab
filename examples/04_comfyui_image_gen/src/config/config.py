"""YAML configuration loader with explicit error reporting."""

from __future__ import annotations

import os
from typing import Any

import yaml


class ConfigLoader:
    @staticmethod
    def load_config(config_path: str) -> dict[str, Any]:
        """Load a YAML configuration file and return it as a dictionary.

        Args:
            config_path: Absolute path to the YAML configuration file.

        Returns:
            Parsed configuration dictionary.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If the file is empty or not a YAML mapping.
        """
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Config file not found at: {config_path}")

        with open(config_path, "r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle)

        if data is None:
            raise ValueError(f"Config file is empty: {config_path}")
        if not isinstance(data, dict):
            raise ValueError(
                f"Config file must contain a YAML mapping at the top level: {config_path}"
            )
        return data
