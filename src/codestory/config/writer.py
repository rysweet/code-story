import os
import toml
from typing import Any
from dotenv import set_key

def update_env(key: str, value: str, env_file: str = '.env'):
    """Update a value in the .env file."""
    set_key(env_file, key, value)

def update_toml(section: str, key: str, value: Any, toml_file: str = '.codestory.toml'):
    """Update a value in the .codestory.toml file."""
    try:
        config = toml.load(toml_file) if os.path.exists(toml_file) else {}
    except Exception:
        config = {}
    if section not in config:
        config[section] = {}
    config[section][key] = value
    with open(toml_file, 'w') as f:
        toml.dump(config, f)

def update_config(section: str, key: str, value: Any, persist_to: str = 'env'):
    """Update configuration in memory and optionally persist to file."""
    from .settings import get_settings
    settings = get_settings()
    if hasattr(settings, section) and hasattr(getattr(settings, section), key):
        setattr(getattr(settings, section), key, value)
    if persist_to == 'env':
        update_env(f"{section.upper()}_{key.upper()}", str(value))
    elif persist_to == 'toml':
        update_toml(section, key, value)
