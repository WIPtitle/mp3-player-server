#!/usr/bin/python3
"""Main entry point for Audio Server."""

import os
import sys
import json
import logging
import socketserver

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mp3_player_server import AudioStorage, AudioPlayer, AudioRequestHandler

# Setup logging - goes to stdout/stderr which systemd captures in journal
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    datefmt='%H:%M:%S',
    stream=sys.stdout
)
logger = logging.getLogger("mp3-player-server")


def main():
    """Start the Audio Server."""
    # Config path from env var, default to /etc for production
    CONFIG_FILE = os.environ.get("MP3_PLAYER_SERVER_CONFIG_PATH", "/etc/mp3-player-server/config.json")

    # Defaults
    port = 8888
    storage_dir = "/var/lib/mp3-player-server/data"
    audio_device = None

    # Load config if exists
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                port = config.get("port", port)
                storage_dir = config.get("storage_dir", storage_dir)
                audio_device = config.get("audio_device", audio_device)
        except Exception as e:
            print(f"Error loading config: {e}")
    else:
        # Create default config
        config = {"port": port, "storage_dir": storage_dir, "audio_device": audio_device}
        try:
            os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f, indent=2)
            print(f"Created default config: {CONFIG_FILE}")
        except PermissionError:
            print(f"Warning: Cannot create config at {CONFIG_FILE} (permission denied)")
        except Exception as e:
            print(f"Warning: Cannot create config: {e}")

    # Initialize components
    storage = AudioStorage(storage_dir)
    player = AudioPlayer(audio_device)

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
    AudioRequestHandler.config = config
    AudioRequestHandler.config_file = CONFIG_FILE
    AudioRequestHandler.user_mode = False

    # Start HTTP server with explicit address reuse
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.ThreadingTCPServer(("", port), AudioRequestHandler) as httpd:
        print(f"Audio Server started on port {port}")
        print(f"Storage directory: {storage_dir}")
        if audio_device:
            print(f"Audio device: {audio_device}")
        else:
            print("WARNING: No audio device configured. Please select one in the web interface.")

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down...")
            httpd.shutdown()


if __name__ == '__main__':
    main()