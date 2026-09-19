import yaml
import os

class ConfigLoader:
    @staticmethod
    def load_config(config_path):
        """
        Loads the YAML configuration file.
        """
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Config file not found at: {config_path}")
            
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
