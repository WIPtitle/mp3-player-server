#!/usr/bin/python3
"""Configuration for Audio Server."""

import json
import os
import tempfile

# Config path from env var, default to /etc for production
CONFIG_FILE = os.environ.get("MP3_PLAYER_SERVER_CONFIG_PATH", "/etc/mp3-player-server/config.json")
DEFAULT_PORT = 8888
DEFAULT_STORAGE_DIR = "/var/lib/mp3-player-server/data"


def load_config():
    """Load configuration from file."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
        except (json.JSONDecodeError, OSError):
            # Corrupt/truncated config (e.g. an unclean power loss on an older
            # non-atomic write): fall back to defaults instead of crashing.
            config = {}
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


def atomic_write_json(path, data):
    """Crash-safe JSON write.

    Writes to a temp file in the same directory, fsyncs it, atomically renames
    it into place, then fsyncs the directory. On power loss the target is left
    as either the complete old file or the complete new one -- never truncated.
    """
    directory = os.path.dirname(path) or "."
    os.makedirs(directory, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=directory, prefix=".config-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tmp, 0o644)
        os.replace(tmp, path)
        dir_fd = os.open(directory, os.O_DIRECTORY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def save_config(config):
    """Save configuration to file (crash-safe atomic write)."""
    atomic_write_json(CONFIG_FILE, config)