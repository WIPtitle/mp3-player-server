#!/usr/bin/python3
"""Command-line interface for Audio Server."""

import sys
import json
import os
import subprocess
import tempfile

CONFIG_FILE = "/etc/mp3-player-server/config.json"
SERVICE_NAME = "mp3-player-server.service"


def load_config():
    """Load configuration from file."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {"port": 8888, "storage_dir": "/var/lib/mp3-player-server/data", "audio_device": None}


def save_config(config):
    """Save configuration to file (crash-safe atomic write)."""
    directory = os.path.dirname(CONFIG_FILE) or "."
    os.makedirs(directory, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=directory, prefix=".config-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(config, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tmp, 0o644)
        os.replace(tmp, CONFIG_FILE)
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


def set_port(port):
    """Set server port and restart service."""
    try:
        port = int(port)
        if port < 1 or port > 65535:
            print("Error: Port must be between 1 and 65535")
            sys.exit(1)

        config = load_config()
        old_port = config.get("port", 8888)

        if old_port == port:
            print(f"Port is already set to {port}")
            return

        config["port"] = port
        save_config(config)

        print(f"Port set to {port}")
        print("Restarting service...")

        try:
            subprocess.run(["systemctl", "restart", SERVICE_NAME], check=True)
            print("Service restarted successfully")
            print(f"Audio Server now listening on port {port}")
        except subprocess.CalledProcessError:
            print("Error: Failed to restart service")
            print("Try: sudo systemctl restart mp3-player-server")

    except ValueError:
        print("Error: Invalid port number")
        sys.exit(1)


def get_status():
    """Show current configuration and service status."""
    config = load_config()
    port = config.get("port", 8888)
    storage_dir = config.get("storage_dir", "/var/lib/mp3-player-server/data")
    audio_device = config.get("audio_device")

    print(f"Current port: {port}")
    print(f"Storage directory: {storage_dir}")
    print(f"Audio device: {audio_device if audio_device else 'Not configured'}")

    try:
        result = subprocess.run(["systemctl", "is-active", SERVICE_NAME],
                                capture_output=True, text=True)
        status = result.stdout.strip()
        print(f"Service status: {status}")

        if status == "active":
            print(f"API endpoint: http://localhost:{port}")
    except:
        print("Service status: unknown")


def show_help():
    """Show help message."""
    print("Audio Server Control")
    print("")
    print("Commands:")
    print("  mp3-player-server status       Show current configuration and status")
    print("  mp3-player-server set-port <port>  Set server port (requires restart)")
    print("  mp3-player-server help         Show this help message")
    print("")
    print("Service control:")
    print("  sudo systemctl start mp3-player-server    Start service")
    print("  sudo systemctl stop mp3-player-server     Stop service")
    print("  sudo systemctl restart mp3-player-server  Restart service")
    print("  sudo journalctl -u mp3-player-server -f   View logs")


def main():
    if len(sys.argv) < 2:
        show_help()
        sys.exit(0)

    command = sys.argv[1]

    if command == "status":
        get_status()
    elif command == "set-port" and len(sys.argv) == 3:
        set_port(sys.argv[2])
    elif command == "help" or command == "--help" or command == "-h":
        show_help()
    else:
        print(f"Unknown command: {command}")
        print("Use 'mp3-player-server help' for usage information")
        sys.exit(1)


if __name__ == "__main__":
    main()