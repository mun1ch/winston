#!/usr/bin/env python3
"""
Configuration module for bill payment scripts.
Loads configuration from YAML files.
"""
import os
import yaml
from pathlib import Path

# Get the directory where this script is located
BASE_DIR = Path(__file__).parent

def load_yaml_config(yaml_file):
    """Load a YAML configuration file."""
    config_path = BASE_DIR / "config" / yaml_file
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    with open(config_path, 'r') as file:
        return yaml.safe_load(file)

# Load the T-Mobile configuration
TMOBILE_CONFIG = load_yaml_config("tmobile.yaml") 