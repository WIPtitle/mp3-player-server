#!/usr/bin/python3
"""Command-line interface for Audio Server."""

import sys
import json
import os
import subprocess

CONFIG_FILE = "/etc/audio-server/config.json"
SERVICE_NAME = "audio-server.service"


def load_config():
    """Load configuration from file."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {"port": 8888, "storage_dir": "/var/lib/audio-server/data", "audio_device": None}


def save_config(config):
    """Save configuration to file."""
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)


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
            print("Try: sudo systemctl restart audio-server")

    except ValueError:
        print("Error: Invalid port number")
        sys.exit(1)


def get_status():
    """Show current configuration and service status."""
    config = load_config()
    port = config.get("port", 8888)
    storage_dir = config.get("storage_dir", "/var/lib/audio-server/data")
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
    print("  audio-server status       Show current configuration and status")
    print("  audio-server set-port <port>  Set server port (requires restart)")
    print("  audio-server help         Show this help message")
    print("")
    print("Service control:")
    print("  sudo systemctl start audio-server    Start service")
    print("  sudo systemctl stop audio-server     Stop service")
    print("  sudo systemctl restart audio-server  Restart service")
    print("  sudo journalctl -u audio-server -f   View logs")


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
        print("Use 'audio-server help' for usage information")
        sys.exit(1)


if __name__ == "__main__":
    main()