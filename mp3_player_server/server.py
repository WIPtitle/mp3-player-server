#!/usr/bin/python3
"""HTTP server for Audio Server."""

import http.server
import json
import os
from typing import Any, Dict


class AudioRequestHandler(http.server.BaseHTTPRequestHandler):
    """HTTP request handler for Audio Server."""

    storage = None
    player = None
    html_file = None
    config = None
    config_file = None  # Path to config file for saving
    user_mode = False

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
        elif self.path == '/api/devices':
            self._list_devices()
        elif self.path == '/api/device':
            self._get_current_device()
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
        elif self.path == '/api/device':
            self._set_device()
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
            "current_volume": self.player.get_current_volume(),
            "files": self.storage.list_files(),
            "audio_device": self.player.get_audio_device()
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
            if content_length > 50 * 1024 * 1024:
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

        if self.player.get_current() == name:
            self.player.stop()

        if self.storage.delete(name):
            self._send_json_response(200, {"message": f"Audio file '{name}' deleted"})
        else:
            self._send_json_response(404, {"error": f"Audio file '{name}' not found"})

    def _play_audio(self):
        """Play audio file with volume control."""
        path_parts = self.path.split('?')
        name = path_parts[0].split('/api/play/')[1]

        params = {}
        if len(path_parts) > 1:
            for param in path_parts[1].split('&'):
                if '=' in param:
                    key, value = param.split('=', 1)
                    params[key] = value

        if 'volume' not in params:
            self._send_json_response(400, {"error": "Missing required parameter: volume (0-100)"})
            return

        try:
            volume = int(params['volume'])
            if volume < 0 or volume > 100:
                self._send_json_response(400, {"error": "Volume must be between 0 and 100"})
                return
        except ValueError:
            self._send_json_response(400, {"error": "Invalid volume value. Must be an integer between 0 and 100"})
            return

        loop = False
        if 'loop' in params:
            loop = params['loop'].lower() in ('true', '1', 'yes')

        duration = None
        if 'duration' in params:
            try:
                duration = int(params['duration'])
                if duration <= 0:
                    duration = None
            except ValueError:
                duration = None

        current_device = self.player.get_audio_device()
        if not current_device:
            self._send_json_response(400, {"error": "No audio device configured. Please select an audio device first."})
            return

        available_devices = self.player.list_audio_devices()
        device_ids = [d['id'] for d in available_devices]

        if current_device not in device_ids:
            self._send_json_response(400, {
                "error": f"Audio device '{current_device}' is not available. It may have been disconnected. Please select a different device or reconnect it."
            })
            return

        file_path = self.storage.get_path(name)
        if not file_path:
            self._send_json_response(404, {"error": f"Audio file '{name}' not found"})
            return

        if self.player.play(file_path, volume=volume, loop=loop, duration=duration):
            response_msg = f"Playing '{name}' at {volume}% volume"
            if loop:
                response_msg += " (loop)"
            else:
                response_msg += " (once)"
            if duration:
                response_msg += f" (max {duration}s)"
            self._send_json_response(200, {"message": response_msg})
        else:
            self._send_json_response(500, {"error": "Failed to start playback. Check audio device configuration."})

    def _stop_audio(self):
        """Stop audio playback."""
        if self.player.stop():
            self._send_json_response(200, {"message": "Playback stopped"})
        else:
            self._send_json_response(200, {"message": "No audio playing"})

    def _list_devices(self):
        """List available audio devices."""
        devices = self.player.list_audio_devices()
        current = self.player.get_audio_device()
        self._send_json_response(200, {
            "devices": devices,
            "current": current
        })

    def _get_current_device(self):
        """Get current audio device."""
        device = self.player.get_audio_device()
        self._send_json_response(200, {"device": device})

    def _set_device(self):
        """Set audio device."""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 0:
                data = json.loads(self.rfile.read(content_length))
                device = data.get('device')
            else:
                self._send_json_response(400, {"error": "No device specified"})
                return

            self.player.set_audio_device(device)

            self.config['audio_device'] = device

            # Save to config file if path is set
            if self.config_file:
                os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
                with open(self.config_file, 'w') as f:
                    json.dump(self.config, f, indent=2)

            self._send_json_response(200, {"message": f"Audio device set to '{device}'"})
        except Exception as e:
            self._send_json_response(500, {"error": str(e)})

    def _send_json_response(self, code: int, data: Dict[str, Any]):
        """Send JSON response."""
        try:
            self.send_response(code)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(data).encode())
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as e:
            print(f"Error sending response: {e}")

    def log_message(self, format, *args):
        """Suppress default logging."""
        pass