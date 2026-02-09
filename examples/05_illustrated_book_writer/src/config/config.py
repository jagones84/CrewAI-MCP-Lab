import os
import yaml
import logging
from .settings import AppSettings

class ConfigLoader:
    @staticmethod
    def load_config(config_path=None):
        if not config_path:
            # Default to ../config.yaml relative to this file (modules -> src -> root)
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            config_path = os.path.join(base_dir, "config", "config.yaml")
        
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Config file not found: {config_path}")
            
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f) or {}
            
        # Load Environment Settings
        settings = AppSettings()
        
        # Inject Settings into Config (Merge)
        # This allows .env to override or supplement config.yaml
        
        if "infrastructure" not in config:
            config["infrastructure"] = {}
            
        # SSH Configuration injection
        if settings.ssh_host:
            if "ssh" not in config["infrastructure"]:
                config["infrastructure"]["ssh"] = {}
            config["infrastructure"]["ssh"]["host"] = settings.ssh_host
            config["infrastructure"]["ssh"]["user"] = settings.ssh_user
            config["infrastructure"]["ssh"]["key_path"] = settings.ssh_key_path
            
        # Validate critical sections
        required = ['project', 'book', 'story', 'agents']
        for sec in required:
            if sec not in config:
                logging.warning(f"Config missing section: {sec}")
                
        return config
