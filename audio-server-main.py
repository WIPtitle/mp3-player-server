#!/usr/bin/python3
"""Main entry point for Audio Server."""

import os
import sys
import json
import socketserver

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from audio_server import AudioStorage, AudioPlayer, AudioRequestHandler


def main():
    """Start the Audio Server."""
    # Load config
    CONFIG_FILE = "/etc/audio-server/config.json"

    port = 8888
    storage_dir = "/var/lib/audio-server/data"
    audio_device = None

    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                port = config.get("port", port)
                storage_dir = config.get("storage_dir", storage_dir)
                audio_device = config.get("audio_device", audio_device)
        except Exception as e:
            print(f"Error loading config: {e}")
            config = {"port": port, "storage_dir": storage_dir, "audio_device": audio_device}
    else:
        config = {"port": port, "storage_dir": storage_dir, "audio_device": audio_device}

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