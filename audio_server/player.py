#!/usr/bin/python3
"""Audio playback management."""

import subprocess
import time
import sys
import os
from pathlib import Path
from typing import Optional


class AudioPlayer:
    """Handles audio playback using mpg123."""

    def __init__(self):
        self.current_process: Optional[subprocess.Popen] = None
        self.current_file: Optional[str] = None
        self.log_file = "/tmp/audio-server.log"

    def log(self, msg):
        """Log to stderr and file."""
        sys.stderr.write(f"[PLAYER] {msg}\n")
        sys.stderr.flush()
        try:
            with open(self.log_file, 'a') as f:
                f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {msg}\n")
        except:
            pass

    def play(self, file_path: Path) -> bool:
        """Start playing an audio file."""
        self.stop()

        try:
            self.log(f"Starting playback: {file_path}")

            if not file_path.exists():
                self.log(f"ERROR: File not found: {file_path}")
                return False

            # Use shell to get proper environment
            cmd = f"mpg123 --loop -1 -q '{file_path}'"
            self.log(f"Command: {cmd}")

            self.current_process = subprocess.Popen(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL
            )

            time.sleep(0.3)
            poll = self.current_process.poll()

            if poll is not None:
                stdout, stderr = self.current_process.communicate()
                self.log(f"FAILED with code {poll}")
                self.log(f"STDERR: {stderr.decode('utf-8', errors='ignore')}")
                self.current_process = None
                return False

            self.current_file = file_path.stem
            self.log(f"SUCCESS: Playing {self.current_file}, PID={self.current_process.pid}")
            return True

        except Exception as e:
            self.log(f"EXCEPTION: {e}")
            import traceback
            self.log(traceback.format_exc())
            self.current_process = None
            self.current_file = None
            return False

    def stop(self) -> bool:
        """Stop current playback."""
        if self.current_process:
            try:
                pid = self.current_process.pid
                self.log(f"Stopping PID {pid}")
                self.current_process.terminate()
                time.sleep(0.1)
                if self.current_process.poll() is None:
                    self.current_process.kill()
                self.current_process = None
                self.current_file = None
                return True
            except Exception as e:
                self.log(f"Stop error: {e}")
                self.current_process = None
                self.current_file = None
        return False

    def is_playing(self) -> bool:
        """Check if audio is currently playing."""
        if not self.current_process:
            return False

        poll = self.current_process.poll()
        if poll is not None:
            self.log(f"Process ended: code {poll}")
            self.current_process = None
            self.current_file = None
            return False
        return True

    def get_current(self) -> Optional[str]:
        """Get name of currently playing file."""
        if self.is_playing():
            return self.current_file
        return None