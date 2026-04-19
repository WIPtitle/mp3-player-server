#!/usr/bin/python3
"""Audio playback management with volume control."""

import subprocess
import threading
import re
import time
import logging
from pathlib import Path
from typing import Optional, List, Dict

logger = logging.getLogger("mp3-player-server")


class AudioPlayer:
    """Handles audio playback using mpg123 with volume control."""

    WARMUP_DURATION_S = 0.3

    def __init__(self, audio_device: Optional[str] = None):
        self.current_process: Optional[subprocess.Popen] = None
        self.current_file: Optional[str] = None
        self.current_volume: int = 50
        self.audio_device = audio_device
        self.lock = threading.Lock()
        self.auto_stop_timer: Optional[threading.Timer] = None
        self._stderr_thread: Optional[threading.Thread] = None

    def _warmup_device(self):
        """Wake the audio sink from suspend with an inaudible 1 Hz sine burst."""
        if not self.audio_device:
            return
        try:
            proc = subprocess.Popen(
                ["speaker-test", "-D", self.audio_device, "-t", "sine",
                 "-f", "1", "-l", "1", "-p", "1", "-P", "1"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            time.sleep(self.WARMUP_DURATION_S)
            proc.terminate()
            proc.wait(timeout=1)
            logger.info("[warmup] audio device pre-warmed (%ss)", self.WARMUP_DURATION_S)
        except Exception as e:
            logger.warning("[warmup] failed (non-fatal): %s", e)

    def set_audio_device(self, device: Optional[str]):
        """Set the audio output device."""
        self.audio_device = device

    def get_audio_device(self) -> Optional[str]:
        """Get the current audio output device."""
        return self.audio_device

    def _monitor_stderr(self, process: subprocess.Popen, file_name: str):
        """Monitor mpg123 stderr in a background thread."""
        try:
            for line in process.stderr:
                text = line.decode('utf-8', errors='ignore').strip()
                if text:
                    logger.warning("[mpg123 stderr] [%s] %s", file_name, text)
        except (ValueError, OSError):
            pass
        finally:
            exit_code = process.poll()
            if exit_code is not None and exit_code != 0:
                logger.error("[mpg123] [%s] process exited with code %d", file_name, exit_code)
            elif exit_code is not None:
                logger.info("[mpg123] [%s] process exited normally (code 0)", file_name)

    def play(self, file_path: Path, volume: int = 50, loop: bool = True, duration: Optional[int] = None) -> bool:
        """
        Start playing an audio file.

        Args:
            file_path: Path to the audio file
            volume: Volume level (0-100)
            loop: Whether to loop the audio
            duration: Maximum duration in seconds (auto-stop after this time)
        """
        if not self.audio_device:
            logger.error("[play] no audio device configured")
            return False

        volume = max(0, min(100, volume))
        self.current_volume = volume

        logger.info("[play] request: file=%s volume=%d loop=%s duration=%s device=%s",
                     file_path.name, volume, loop, duration, self.audio_device)

        self._stop_internal()
        self._warmup_device()

        with self.lock:
            try:
                cmd = ["mpg123", "-q"]
                cmd.extend(["-a", self.audio_device])

                gain = int((volume / 100.0) * 32768)
                cmd.extend(["-f", str(gain)])

                if loop:
                    cmd.extend(["--loop", "-1"])

                cmd.append(str(file_path))

                logger.info("[play] starting mpg123: %s", " ".join(cmd))

                self.current_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE
                )

                logger.info("[play] mpg123 started, pid=%d", self.current_process.pid)

                time.sleep(0.1)

                if self.current_process.poll() is not None:
                    stderr_output = self.current_process.stderr.read() if self.current_process.stderr else b""
                    exit_code = self.current_process.returncode
                    self.current_process = None
                    logger.error("[play] mpg123 died immediately, exit_code=%s stderr=%s",
                                 exit_code, stderr_output.decode('utf-8', errors='ignore'))
                    return False

                self.current_file = file_path.stem

                # Check if PulseAudio actually received the audio stream
                try:
                    pa_check = subprocess.run(
                        ["pactl", "list", "sink-inputs"],
                        capture_output=True, text=True, timeout=2
                    )
                    if pa_check.stdout.strip():
                        logger.info("[play] PA sink-inputs after start:\n%s", pa_check.stdout.strip())
                    else:
                        logger.warning("[play] PA has NO sink-inputs! Audio is NOT reaching PulseAudio")

                    pa_sinks = subprocess.run(
                        ["pactl", "list", "sinks", "short"],
                        capture_output=True, text=True, timeout=2
                    )
                    logger.info("[play] PA sinks: %s", pa_sinks.stdout.strip())
                except Exception as e:
                    logger.warning("[play] could not check PA state: %s", e)

                # Monitor stderr in background thread
                self._stderr_thread = threading.Thread(
                    target=self._monitor_stderr,
                    args=(self.current_process, self.current_file),
                    daemon=True
                )
                self._stderr_thread.start()

                if duration and duration > 0:
                    self.auto_stop_timer = threading.Timer(duration, self._auto_stop)
                    self.auto_stop_timer.start()

                logger.info("[play] playback started successfully: %s (pid=%d)",
                             self.current_file, self.current_process.pid)
                return True
            except Exception as e:
                logger.error("[play] exception starting playback: %s", e, exc_info=True)
                self.current_process = None
                self.current_file = None
                self.current_volume = 50
                return False

    def _auto_stop(self):
        """Automatically stop playback after duration expires."""
        self._stop_internal()

    def _cancel_timer(self):
        """Cancel the auto-stop timer if it exists."""
        if self.auto_stop_timer:
            self.auto_stop_timer.cancel()
            self.auto_stop_timer = None

    def _stop_internal(self) -> bool:
        """Internal stop method without lock."""
        self._cancel_timer()

        with self.lock:
            if self.current_process:
                pid = self.current_process.pid
                file_name = self.current_file
                poll_before = self.current_process.poll()
                logger.info("[stop] stopping pid=%d file=%s (already_dead=%s)",
                             pid, file_name, poll_before is not None)
                try:
                    self.current_process.terminate()
                    self.current_process.wait(timeout=1)
                    logger.info("[stop] pid=%d terminated, exit_code=%s",
                                 pid, self.current_process.returncode)
                except subprocess.TimeoutExpired:
                    logger.warning("[stop] pid=%d did not terminate in 1s, sending KILL", pid)
                    try:
                        self.current_process.kill()
                        self.current_process.wait(timeout=0.5)
                        logger.info("[stop] pid=%d killed", pid)
                    except Exception as e:
                        logger.error("[stop] pid=%d kill failed: %s", pid, e)
                except Exception as e:
                    logger.error("[stop] pid=%d terminate failed: %s", pid, e)

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
                poll = self.current_process.poll()
                if poll is not None:
                    logger.warning("[is_playing] process pid=%d found dead, exit_code=%d, file=%s",
                                    self.current_process.pid, poll, self.current_file)
                return poll is None
            return False

    def get_current(self) -> Optional[str]:
        """Get name of currently playing file."""
        with self.lock:
            if self.current_process and self.current_process.poll() is None:
                return self.current_file
            return None

    def get_current_volume(self) -> int:
        """Get current volume level."""
        with self.lock:
            if self.current_process and self.current_process.poll() is None:
                return self.current_volume
            return 50

    @staticmethod
    def list_audio_devices() -> List[Dict[str, str]]:
        """List available audio devices using aplay -L."""
        devices = []

        try:
            result = subprocess.run(
                ["aplay", "-L"],
                capture_output=True,
                text=True,
                timeout=2,
                check=False,
                env={'LANG': 'C'}
            )

            if result.returncode != 0:
                return devices

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
            pass
        except Exception:
            pass

        return devices