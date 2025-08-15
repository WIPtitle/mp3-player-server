#!/usr/bin/python3
"""Main entry point for Audio Server."""

import os
import sys
import socketserver

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from audio_server import AudioStorage, AudioPlayer, AudioRequestHandler, CONFIG_FILE


def main():
    """Start the Audio Server."""
    # Load config or use defaults
    port = 8888
    storage_dir = "/var/lib/audio-server/data"

    if os.path.exists(CONFIG_FILE):
        import json
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
            port = config.get("port", port)
            storage_dir = config.get("storage_dir", storage_dir)

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

    # Start HTTP server
    with socketserver.ThreadingTCPServer(("", port), AudioRequestHandler) as httpd:
        print(f"Audio Server started on port {port}")
        print(f"Storage directory: {storage_dir}")
        httpd.serve_forever()


if __name__ == '__main__':
    main()