#!/usr/bin/python3
"""HTTP server for Audio Server."""

import http.server
import json
import os
from typing import Any, Dict


class AudioRequestHandler(http.server.BaseHTTPRequestHandler):
    """HTTP request handler for Audio Server."""

    # These will be set by main
    storage = None
    player = None
    html_file = None

    def do_OPTIONS(self):
        """Handle CORS preflight requests."""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, PUT, POST, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        """Handle GET requests."""
        if self.path == '/':
            self._serve_html()
        elif self.path == '/api/status':
            self._get_status()
        elif self.path == '/api/audio':
            self._list_audio()
        elif self.path.startswith('/api/audio/'):
            self._check_audio()
        else:
            self.send_error(404, "Not Found")

    def _serve_html(self):
        """Serve the HTML dashboard."""
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()

        if self.html_file and os.path.exists(self.html_file):
            with open(self.html_file, 'r', encoding='utf-8') as f:
                content = f.read()
        else:
            content = "<html><body><h1>Audio Server</h1><p>Web console not found.</p></body></html>"

        self.wfile.write(content.encode())

    def do_PUT(self):
        """Handle PUT requests."""
        if self.path.startswith('/api/audio/'):
            self._save_audio()
        else:
            self.send_error(404, "Not Found")

    def do_POST(self):
        """Handle POST requests."""
        if self.path.startswith('/api/play/'):
            self._play_audio()
        elif self.path == '/api/stop':
            self._stop_audio()
        else:
            self.send_error(404, "Not Found")

    def do_DELETE(self):
        """Handle DELETE requests."""
        if self.path.startswith('/api/audio/'):
            self._delete_audio()
        else:
            self.send_error(404, "Not Found")

    def _get_status(self):
        """Get server status."""
        response = {
            "playing": self.player.is_playing(),
            "current": self.player.get_current(),
            "files": self.storage.list_files()
        }
        self._send_json_response(200, response)

    def _list_audio(self):
        """List all audio files."""
        files = self.storage.list_files()
        self._send_json_response(200, {"files": files})

    def _check_audio(self):
        """Check if audio file exists."""
        name = self.path.split('/api/audio/')[1]
        if self.storage.exists(name):
            self._send_json_response(200, {"exists": True, "name": name})
        else:
            self._send_json_response(404, {"error": f"Audio file '{name}' not found"})

    def _save_audio(self):
        """Save audio file."""
        name = self.path.split('/api/audio/')[1]

        try:
            content_length = int(self.headers['Content-Length'])
            if content_length > 50 * 1024 * 1024:  # 50MB limit
                self._send_json_response(413, {"error": "File too large (max 50MB)"})
                return

            data = self.rfile.read(content_length)
            self.storage.save(name, data)

            self._send_json_response(200, {"message": f"Audio file '{name}' saved"})
        except Exception as e:
            self._send_json_response(500, {"error": str(e)})

    def _delete_audio(self):
        """Delete audio file."""
        name = self.path.split('/api/audio/')[1]

        # Stop if currently playing
        if self.player.get_current() == name:
            self.player.stop()

        if self.storage.delete(name):
            self._send_json_response(200, {"message": f"Audio file '{name}' deleted"})
        else:
            self._send_json_response(404, {"error": f"Audio file '{name}' not found"})

    def _play_audio(self):
        """Play audio file."""
        name = self.path.split('/api/play/')[1]

        file_path = self.storage.get_path(name)
        if not file_path:
            self._send_json_response(404, {"error": f"Audio file '{name}' not found"})
            return

        if self.player.play(file_path):
            self._send_json_response(200, {"message": f"Playing '{name}'"})
        else:
            self._send_json_response(500, {"error": "Failed to start playback"})

    def _stop_audio(self):
        """Stop audio playback."""
        if self.player.stop():
            self._send_json_response(200, {"message": "Playback stopped"})
        else:
            self._send_json_response(200, {"message": "No audio playing"})

    def _send_json_response(self, code: int, data: Dict[str, Any]):
        """Send JSON response."""
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def log_message(self, format, *args):
        """Suppress default logging."""
        pass