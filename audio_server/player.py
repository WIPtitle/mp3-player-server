#!/usr/bin/python3
"""Audio playback management."""

import subprocess
import threading
import re
import time
from pathlib import Path
from typing import Optional, List, Dict


class AudioPlayer:
    """Handles audio playback using mpg123."""

    def __init__(self, audio_device: Optional[str] = None):
        self.current_process: Optional[subprocess.Popen] = None
        self.current_file: Optional[str] = None
        self.audio_device = audio_device
        self.lock = threading.Lock()

    def set_audio_device(self, device: Optional[str]):
        """Set the audio output device."""
        self.audio_device = device

    def get_audio_device(self) -> Optional[str]:
        """Get the current audio output device."""
        return self.audio_device

    def play(self, file_path: Path, loop: bool = True) -> bool:
        """Start playing an audio file."""
        # Check if audio device is configured
        if not self.audio_device:
            return False

        # Stop any current playback - do this outside the lock to avoid deadlock
        self._stop_internal()

        with self.lock:
            try:
                # Build command
                cmd = ["mpg123", "-q"]

                # Add audio device
                cmd.extend(["-a", self.audio_device])

                # Add loop if requested
                if loop:
                    cmd.extend(["--loop", "-1"])

                # Add file path
                cmd.append(str(file_path))

                # Start mpg123
                self.current_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE  # Capture stderr to detect immediate failures
                )

                # Give mpg123 a moment to start and check if it's still running
                time.sleep(0.1)  # Small delay to allow mpg123 to initialize

                # Check if process is still running
                if self.current_process.poll() is not None:
                    # Process has already exited, likely due to error
                    stderr_output = self.current_process.stderr.read() if self.current_process.stderr else b""
                    self.current_process = None
                    print(f"mpg123 failed to start: {stderr_output.decode('utf-8', errors='ignore')}")
                    return False

                self.current_file = file_path.stem
                return True
            except Exception as e:
                print(f"Error starting playback: {e}")
                self.current_process = None
                self.current_file = None
                return False

    def _stop_internal(self) -> bool:
        """Internal stop method without lock - for use when lock is already held or to avoid deadlock."""
        with self.lock:
            if self.current_process:
                try:
                    self.current_process.terminate()
                    # Don't wait too long to avoid blocking
                    self.current_process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    try:
                        self.current_process.kill()
                        self.current_process.wait(timeout=0.5)
                    except:
                        pass
                except Exception:
                    pass

                self.current_process = None
                self.current_file = None
                return True
            return False

    def stop(self) -> bool:
        """Stop current playback."""
        return self._stop_internal()

    def is_playing(self) -> bool:
        """Check if audio is currently playing."""
        with self.lock:
            if self.current_process:
                # Use poll() which is non-blocking
                return self.current_process.poll() is None
            return False

    def get_current(self) -> Optional[str]:
        """Get name of currently playing file."""
        # Quick check without holding lock for too long
        with self.lock:
            if self.current_process and self.current_process.poll() is None:
                return self.current_file
            return None

    @staticmethod
    def list_audio_devices() -> List[Dict[str, str]]:
        """List available audio devices using aplay -l."""
        devices = []

        try:
            # Run aplay with shorter timeout and handle errors better
            result = subprocess.run(
                ["aplay", "-l"],
                capture_output=True,
                text=True,
                timeout=2,  # Reduced timeout
                check=False,  # Don't raise on non-zero exit
                env={'LANG': 'C'}  # Force English output for parsing
            )

            # Check if command succeeded
            if result.returncode != 0:
                return devices

            # Parse aplay output
            lines = result.stdout.split('\n')

            for line in lines:
                # Match card line
                card_match = re.match(r'card (\d+): (\w+) \[(.*?)\], device (\d+): (.*?) \[(.*?)\]', line)
                if card_match:
                    card_num = card_match.group(1)
                    card_id = card_match.group(2)
                    card_name = card_match.group(3)
                    device_num = card_match.group(4)
                    device_id = card_match.group(5)
                    device_name = card_match.group(6)

                    # Create device identifier in plughw format
                    device_hw = f"plughw:{card_num},{device_num}"

                    devices.append({
                        "id": device_hw,
                        "name": f"{card_name} - {device_name}",
                        "card": int(card_num),
                        "device": int(device_num),
                        "card_id": card_id,
                        "card_name": card_name,
                        "device_name": device_name
                    })

        except subprocess.TimeoutExpired:
            # If aplay times out, return empty list
            pass
        except Exception:
            # Any other error, return empty list
            pass

        return devices