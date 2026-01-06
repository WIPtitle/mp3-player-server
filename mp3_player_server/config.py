#!/usr/bin/python3
"""Configuration for Audio Server."""

import json
import os

# Config path from env var, default to /etc for production
CONFIG_FILE = os.environ.get("MP3_PLAYER_SERVER_CONFIG_PATH", "/etc/mp3-player-server/config.json")
DEFAULT_PORT = 8888
DEFAULT_STORAGE_DIR = "/var/lib/mp3-player-server/data"


def load_config():
    """Load configuration from file."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
    else:
        config = {}

    # Set defaults
    if 'port' not in config:
        config['port'] = DEFAULT_PORT
    if 'storage_dir' not in config:
        config['storage_dir'] = DEFAULT_STORAGE_DIR
    if 'audio_device' not in config:
        config['audio_device'] = None

    return config


def save_config(config):
    """Save configuration to file."""
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)