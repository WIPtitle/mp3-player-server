#!/usr/bin/python3
"""Main entry point for Audio Server."""

import os
import sys
import http.server
import socketserver

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from audio_server import AudioStorage, AudioPlayer, AudioRequestHandler, CONFIG_FILE


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True  # Important: threads die when main dies


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

    # Use standard HTTPServer for simpler threading
    with ThreadedTCPServer(("", port), AudioRequestHandler) as httpd:
        print(f"Audio Server started on port {port}")
        print(f"Storage directory: {storage_dir}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down...")
            player.stop()


if __name__ == '__main__':
    main()