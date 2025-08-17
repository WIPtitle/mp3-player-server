#!/usr/bin/python3
"""Audio playback management."""

import subprocess
import threading
import re
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
        with self.lock:
            # Check if audio device is configured
            if not self.audio_device:
                return False

            # Stop any current playback
            self.stop()

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

    @staticmethod
    def list_audio_devices() -> List[Dict[str, str]]:
        """List available audio devices using aplay -l."""
        devices = []

        try:
            # Run aplay with timeout
            result = subprocess.run(
                ["aplay", "-l"],
                capture_output=True,
                text=True,
                check=True,
                timeout=5,
                env={'LANG': 'C'}  # Force English output for parsing
            )

            # Parse aplay output
            lines = result.stdout.split('\n')
            current_card = None

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

        except subprocess.CalledProcessError:
            # If aplay fails, return empty list
            pass
        except Exception:
            # Any other error, return empty list
            pass

        return devices