"""
Configuration utilities for LinkedIn MCP server
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

# Default configuration
DEFAULT_CONFIG = {
    "session_dir": "sessions",
    "data_dir": "data",
    "log_level": "INFO",
    "browser_timeout": 30,
    "api_timeout": 15,
    "resume_templates_dir": "templates/resume",
    "cover_letter_templates_dir": "templates/cover_letter",
    "max_retry_attempts": 3,
    "retry_delay": 2,
    "use_ai": True,
    "ai_provider": "openai",
    "openai_model": "gpt-4",
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
}

# Config singleton
_config_instance = None

def get_config() -> Dict[str, Any]:
    """
    Get the configuration settings
    Loads from config.json if available, otherwise uses defaults
    
    Returns:
        Dict containing configuration settings
    """
    global _config_instance
    
    if _config_instance is not None:
        return _config_instance
    
    config = DEFAULT_CONFIG.copy()
    
    # Try to load config from file
    config_path = Path("config.json")
    if config_path.exists():
        try:
            with open(config_path, "r") as f:
                file_config = json.load(f)
                config.update(file_config)
        except Exception as e:
            print(f"Error loading config file: {str(e)}")
    
    # Check for environment variable overrides
    for key in config:
        env_key = f"LINKEDIN_MCP_{key.upper()}"
        if env_key in os.environ:
            env_value = os.environ[env_key]
            
            # Try to parse as JSON first (for complex types)
            try:
                config[key] = json.loads(env_value)
            except json.JSONDecodeError:
                # If not valid JSON, use as string
                config[key] = env_value
    
    # Ensure directories exist
    for dir_key in ["session_dir", "data_dir", "resume_templates_dir", "cover_letter_templates_dir"]:
        if dir_key in config:
            Path(config[dir_key]).mkdir(parents=True, exist_ok=True)
    
    _config_instance = config
    return config

def update_config(key: str, value: Any) -> None:
    """
    Update a configuration setting
    
    Args:
        key: Configuration key to update
        value: New value for the key
    """
    config = get_config()
    config[key] = value
    
    # Optionally save to file
    try:
        with open("config.json", "w") as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        print(f"Error saving config file: {str(e)}")

def reset_config() -> None:
    """Reset configuration to defaults"""
    global _config_instance
    _config_instance = None
    
    # Remove config file if it exists
    config_path = Path("config.json")
    if config_path.exists():
        try:
            config_path.unlink()
        except Exception as e:
            print(f"Error removing config file: {str(e)}")