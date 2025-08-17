#!/usr/bin/env python3
"""Main entry point for Audio Server with user mode support."""

import os
import sys
import http.server
import socketserver
import argparse
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from audio_server import AudioStorage, AudioPlayer, AudioRequestHandler


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


def load_config(user_mode=False):
    """Load configuration from appropriate location."""
    if user_mode:
        # User mode: config in ~/.config/audio-server/
        config_file = os.path.expanduser("~/.config/audio-server/config.json")
        default_storage = os.path.expanduser("~/.local/share/audio-server/data")
    else:
        # System mode: config in /etc/
        config_file = "/etc/audio-server/config.json"
        default_storage = "/var/lib/audio-server/data"

    # Default configuration
    default_config = {
        "port": 8888,
        "storage_dir": default_storage
    }

    # Load from file if exists
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
                # Ensure required keys exist
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
                return config
        except Exception as e:
            print(f"Warning: Could not load config from {config_file}: {e}")
            print("Using default configuration")

    return default_config


def ensure_directories(config, user_mode=False):
    """Ensure required directories exist."""
    storage_dir = config["storage_dir"]

    # Create storage directory
    os.makedirs(storage_dir, exist_ok=True)

    if user_mode:
        # Create user config directory
        config_dir = os.path.expanduser("~/.config/audio-server")
        os.makedirs(config_dir, exist_ok=True)


def main():
    """Start the Audio Server."""
    parser = argparse.ArgumentParser(description='Audio Server')
    parser.add_argument('--user-mode', action='store_true',
                        help='Run in user mode (configs in ~/.config/)')

    args = parser.parse_args()

    print(f"Starting Audio Server ({'user' if args.user_mode else 'system'} mode)")

    # Load configuration
    config = load_config(args.user_mode)
    port = config["port"]
    storage_dir = config["storage_dir"]

    print(f"Port: {port}")
    print(f"Storage: {storage_dir}")

    # Ensure directories exist
    ensure_directories(config, args.user_mode)

    # Initialize components
    storage = AudioStorage(storage_dir)
    player = AudioPlayer()

    # Set HTML file path
    html_file = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "web",
        "index.html"
    )

    # Set as class attributes
    AudioRequestHandler.storage = storage
    AudioRequestHandler.player = player
    AudioRequestHandler.html_file = html_file

    # Start server
    try:
        with ThreadedTCPServer(("", port), AudioRequestHandler) as httpd:
            print(f"Audio Server started on port {port}")
            if args.user_mode:
                print(f"Running as user: {os.getenv('USER', 'unknown')}")
                print(f"Config: ~/.config/audio-server/config.json")
                print(f"Storage: {storage_dir}")
            else:
                print(f"Config: /etc/audio-server/config.json")
                print(f"Storage: {storage_dir}")

            print(f"Access: http://localhost:{port}")

            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                print("\nShutting down...")
                player.stop()

    except PermissionError:
        print(f"Error: Permission denied on port {port}")
        if not args.user_mode and port < 1024:
            print("Hint: Ports below 1024 require root privileges")
            print("Consider using --user-mode or changing port in config")
        sys.exit(1)
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"Error: Port {port} already in use")
            print("Stop other services on this port or change configuration")
        else:
            print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()