#!/usr/bin/python3
"""Audio playback management with volume control."""

import subprocess
import threading
import re
import time
from pathlib import Path
from typing import Optional, List, Dict


class AudioPlayer:
    """Handles audio playback using mpg123 with volume control."""

    def __init__(self, audio_device: Optional[str] = None):
        self.current_process: Optional[subprocess.Popen] = None
        self.current_file: Optional[str] = None
        self.current_volume: int = 50  # Default volume 50%
        self.audio_device = audio_device
        self.lock = threading.Lock()

    def set_audio_device(self, device: Optional[str]):
        """Set the audio output device."""
        self.audio_device = device

    def get_audio_device(self) -> Optional[str]:
        """Get the current audio output device."""
        return self.audio_device

    def play(self, file_path: Path, volume: int = 50, loop: bool = True) -> bool:
        """
        Start playing an audio file.

        Args:
            file_path: Path to the audio file
            volume: Volume level (0-100)
            loop: Whether to loop the audio
        """
        # Check if audio device is configured
        if not self.audio_device:
            return False

        # Validate volume
        volume = max(0, min(100, volume))
        self.current_volume = volume

        # Stop any current playback - do this outside the lock to avoid deadlock
        self._stop_internal()

        with self.lock:
            try:
                # Build command
                cmd = ["mpg123", "-q"]

                # Add audio device
                cmd.extend(["-a", self.audio_device])

                # Add volume control
                # mpg123 uses -f for gain/volume where 32768 is normal (100%)
                # Scale volume from 0-100 to 0-32768
                gain = int((volume / 100.0) * 32768)
                cmd.extend(["-f", str(gain)])

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
                self.current_volume = 50
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
                self.current_volume = 50
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

    def get_current_volume(self) -> int:
        """Get current volume level."""
        with self.lock:
            if self.current_process and self.current_process.poll() is None:
                return self.current_volume
            return 50  # Default volume when not playing

    @staticmethod
    def list_audio_devices() -> List[Dict[str, str]]:
        """List available audio devices using aplay -L."""
        devices = []

        try:
            # Run aplay with shorter timeout and handle errors better
            result = subprocess.run(
                ["aplay", "-L"],
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
            lines = result.stdout.strip().split('\n')
            current_device = None
            current_description = []

            skip_devices = ["null", "jack", "oss", "lavrate", "samplerate",
                            "speexrate", "speex", "upmix", "vdownmix", "usbstream"]

            for line in lines:
                if line and not line.startswith(' '):
                    if current_device and current_device not in skip_devices:
                        description = ' '.join(current_description).strip()
                        devices.append({
                            "id": current_device,
                            "name": description if description else current_device,
                            "card": -1,
                            "device": -1,
                            "card_id": current_device,
                            "card_name": current_device,
                            "device_name": description if description else current_device
                        })

                    current_device = line
                    current_description = []
                elif line.strip() and current_device:
                    current_description.append(line.strip())

            if current_device and current_device not in skip_devices:
                description = ' '.join(current_description).strip()
                devices.append({
                    "id": current_device,
                    "name": description if description else current_device,
                    "card": -1,
                    "device": -1,
                    "card_id": current_device,
                    "card_name": current_device,
                    "device_name": description if description else current_device
                })

        except subprocess.TimeoutExpired:
            # If aplay times out, return empty list
            pass
        except Exception:
            # Any other error, return empty list
            pass

        return devices