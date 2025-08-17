#!/usr/bin/python3
"""Audio playback management."""

import subprocess
import threading
from pathlib import Path
from typing import Optional


class AudioPlayer:
    """Handles audio playback using mpg123."""

    def __init__(self):
        self.current_process: Optional[subprocess.Popen] = None
        self.current_file: Optional[str] = None
        self.lock = threading.Lock()

    def play(self, file_path: Path) -> bool:
        """Start playing an audio file."""
        with self.lock:
            # Stop any current playback
            self.stop()

            try:
                # Start mpg123 with loop
                self.current_process = subprocess.Popen(
                    ["mpg123", "--loop", "-1", "-q", str(file_path)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                self.current_file = file_path.stem
                return True
            except Exception:
                return False

    def stop(self) -> bool:
        """Stop current playback."""
        with self.lock:
            if self.current_process:
                try:
                    self.current_process.terminate()
                    self.current_process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self.current_process.kill()
                except Exception:
                    pass

                self.current_process = None
                self.current_file = None
                return True
            return False

    def is_playing(self) -> bool:
        """Check if audio is currently playing."""
        with self.lock:
            if self.current_process:
                return self.current_process.poll() is None
            return False

    def get_current(self) -> Optional[str]:
        """Get name of currently playing file."""
        with self.lock:
            if self.is_playing():
                return self.current_file
            return None