#!/usr/bin/python3
"""HTTP server for Audio Server."""

import http.server
import json
import os
from typing import Any, Dict
import traceback


class AudioRequestHandler(http.server.BaseHTTPRequestHandler):
    """HTTP request handler for Audio Server."""

    # These will be set by main
    storage = None
    player = None
    html_file = None

    # Shorter timeout
    timeout = 5

    def do_OPTIONS(self):
        """Handle CORS preflight requests."""
        try:
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, PUT, POST, DELETE, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.end_headers()
        except:
            pass

    def do_GET(self):
        """Handle GET requests."""
        try:
            print(f"GET {self.path}")

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
        except Exception as e:
            print(f"Error in GET: {e}")
            traceback.print_exc()
            try:
                self.send_error(500, str(e))
            except:
                pass

    def _serve_html(self):
        """Serve the HTML dashboard."""
        try:
            if self.html_file and os.path.exists(self.html_file):
                with open(self.html_file, 'rb') as f:
                    content = f.read()
            else:
                content = b"<html><body><h1>Audio Server</h1></body></html>"

            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.send_header('Content-Length', str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            print(f"Error serving HTML: {e}")

    def do_PUT(self):
        """Handle PUT requests."""
        try:
            print(f"PUT {self.path}")
            if self.path.startswith('/api/audio/'):
                self._save_audio()
            else:
                self.send_error(404, "Not Found")
        except Exception as e:
            print(f"Error in PUT: {e}")
            try:
                self.send_error(500, str(e))
            except:
                pass

    def do_POST(self):
        """Handle POST requests."""
        try:
            print(f"POST {self.path}")
            if self.path.startswith('/api/play/'):
                self._play_audio()
            elif self.path == '/api/stop':
                self._stop_audio()
            else:
                self.send_error(404, "Not Found")
        except Exception as e:
            print(f"Error in POST: {e}")
            try:
                self.send_error(500, str(e))
            except:
                pass

    def do_DELETE(self):
        """Handle DELETE requests."""
        try:
            print(f"DELETE {self.path}")
            if self.path.startswith('/api/audio/'):
                self._delete_audio()
            else:
                self.send_error(404, "Not Found")
        except Exception as e:
            print(f"Error in DELETE: {e}")
            try:
                self.send_error(500, str(e))
            except:
                pass

    def _get_status(self):
        """Get server status."""
        try:
            # Get data first before sending response
            playing = self.player.is_playing() if self.player else False
            current = self.player.get_current() if self.player else None
            files = self.storage.list_files() if self.storage else []

            response = {
                "playing": playing,
                "current": current,
                "files": files
            }

            print(f"Status: playing={playing}, current={current}, files={len(files)}")
            self._send_json_response(200, response)
        except Exception as e:
            print(f"Error in _get_status: {e}")
            traceback.print_exc()
            self._send_json_response(500, {"error": str(e)})

    def _list_audio(self):
        """List all audio files."""
        try:
            files = self.storage.list_files() if self.storage else []
            self._send_json_response(200, {"files": files})
        except Exception as e:
            print(f"Error in _list_audio: {e}")
            self._send_json_response(500, {"error": str(e)})

    def _check_audio(self):
        """Check if audio file exists."""
        try:
            name = self.path.split('/api/audio/')[1]
            if self.storage and self.storage.exists(name):
                self._send_json_response(200, {"exists": True, "name": name})
            else:
                self._send_json_response(404, {"error": f"Audio file '{name}' not found"})
        except Exception as e:
            print(f"Error in _check_audio: {e}")
            self._send_json_response(500, {"error": str(e)})

    def _save_audio(self):
        """Save audio file."""
        try:
            name = self.path.split('/api/audio/')[1]
            content_length = int(self.headers.get('Content-Length', 0))

            if content_length > 50 * 1024 * 1024:  # 50MB limit
                self._send_json_response(413, {"error": "File too large (max 50MB)"})
                return

            data = self.rfile.read(content_length)

            if self.storage:
                self.storage.save(name, data)
                self._send_json_response(200, {"message": f"Audio file '{name}' saved"})
            else:
                self._send_json_response(500, {"error": "Storage not initialized"})
        except Exception as e:
            print(f"Error in _save_audio: {e}")
            self._send_json_response(500, {"error": str(e)})

    def _delete_audio(self):
        """Delete audio file."""
        try:
            name = self.path.split('/api/audio/')[1]

            # Stop if currently playing
            if self.player and self.player.get_current() == name:
                self.player.stop()

            if self.storage and self.storage.delete(name):
                self._send_json_response(200, {"message": f"Audio file '{name}' deleted"})
            else:
                self._send_json_response(404, {"error": f"Audio file '{name}' not found"})
        except Exception as e:
            print(f"Error in _delete_audio: {e}")
            self._send_json_response(500, {"error": str(e)})

    def _play_audio(self):
        """Play audio file."""
        try:
            name = self.path.split('/api/play/')[1]
            print(f"Trying to play: {name}")

            if not self.storage:
                self._send_json_response(500, {"error": "Storage not initialized"})
                return

            file_path = self.storage.get_path(name)
            if not file_path:
                self._send_json_response(404, {"error": f"Audio file '{name}' not found"})
                return

            if not self.player:
                self._send_json_response(500, {"error": "Player not initialized"})
                return

            if self.player.play(file_path):
                self._send_json_response(200, {"message": f"Playing '{name}'"})
            else:
                self._send_json_response(500, {"error": "Failed to start playback"})
        except Exception as e:
            print(f"Error in _play_audio: {e}")
            traceback.print_exc()
            self._send_json_response(500, {"error": str(e)})

    def _stop_audio(self):
        """Stop audio playback."""
        try:
            if self.player and self.player.stop():
                self._send_json_response(200, {"message": "Playback stopped"})
            else:
                self._send_json_response(200, {"message": "No audio playing"})
        except Exception as e:
            print(f"Error in _stop_audio: {e}")
            self._send_json_response(500, {"error": str(e)})

    def _send_json_response(self, code: int, data: Dict[str, Any]):
        """Send JSON response."""
        try:
            json_str = json.dumps(data)
            json_bytes = json_str.encode('utf-8')

            self.send_response(code)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(json_bytes)))
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json_bytes)
        except Exception as e:
            print(f"Error sending response: {e}")

    def log_message(self, format, *args):
        """Basic logging."""
        print(f"{self.address_string()} - {format % args}")