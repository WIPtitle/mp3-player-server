#!/usr/bin/env python3
"""Audio playback management using pygame."""

import pygame
import sys
import time
from pathlib import Path
from typing import Optional
import threading
import atexit


class AudioPlayer:
    """Handles audio playback using pygame mixer."""

    def __init__(self):
        self.current_file: Optional[str] = None
        self.log_file = "/tmp/audio-server.log"
        self._initialized = False
        self._lock = threading.Lock()

        # Initialize pygame mixer
        self._init_pygame()

        # Cleanup on exit
        atexit.register(self._cleanup)

    def _init_pygame(self):
        """Initialize pygame mixer with optimal settings."""
        try:
            # Pre-initialize with optimized settings for audio server use
            pygame.mixer.pre_init(
                frequency=44100,  # Standard frequency
                size=-16,  # 16-bit signed samples
                channels=2,  # Stereo
                buffer=1024  # Small buffer to reduce latency
            )

            pygame.mixer.init()

            # Set volume to maximum level
            pygame.mixer.music.set_volume(1.0)

            self._initialized = True
            self.log("Pygame mixer initialized successfully")

        except pygame.error as e:
            self.log(f"ERROR: Failed to initialize pygame mixer: {e}")
            self._initialized = False
        except Exception as e:
            self.log(f"ERROR: Unexpected error during pygame init: {e}")
            self._initialized = False

    def _cleanup(self):
        """Cleanup pygame resources."""
        try:
            if self._initialized and pygame.mixer.get_init():
                pygame.mixer.music.stop()
                pygame.mixer.quit()
                self.log("Pygame mixer cleaned up")
        except:
            pass  # Ignore cleanup errors

    def log(self, msg):
        """Log to stderr and file."""
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        log_msg = f"[PYGAME-PLAYER] {msg}"

        # Log to stderr
        sys.stderr.write(f"{log_msg}\n")
        sys.stderr.flush()

        # Log to file
        try:
            with open(self.log_file, 'a') as f:
                f.write(f"{timestamp} - {log_msg}\n")
        except:
            pass  # Ignore file logging errors

    def play(self, file_path: Path) -> bool:
        """Start playing an audio file in continuous loop."""
        with self._lock:
            # Stop any current playback
            self.stop()

            if not self._initialized:
                self.log("ERROR: Pygame mixer not initialized")
                return False

            try:
                self.log(f"Starting playback: {file_path}")

                if not file_path.exists():
                    self.log(f"ERROR: File not found: {file_path}")
                    return False

                # Verify it's an audio file
                if not str(file_path).lower().endswith(('.mp3', '.wav', '.ogg')):
                    self.log(f"WARNING: File may not be a supported audio format: {file_path}")

                # Load and play the audio file
                pygame.mixer.music.load(str(file_path))

                # Play with infinite loop (-1 means loop forever)
                pygame.mixer.music.play(loops=-1)

                # Small delay to let pygame start
                time.sleep(0.1)

                # Verify playback started
                if not pygame.mixer.music.get_busy():
                    self.log("ERROR: Pygame failed to start playback")
                    return False

                self.current_file = file_path.stem
                self.log(f"SUCCESS: Playing {self.current_file} in continuous loop")
                return True

            except pygame.error as e:
                self.log(f"PYGAME ERROR: {e}")
                self.current_file = None
                return False
            except Exception as e:
                self.log(f"EXCEPTION: {e}")
                import traceback
                self.log(f"Traceback: {traceback.format_exc()}")
                self.current_file = None
                return False

    def stop(self) -> bool:
        """Stop current playback."""
        with self._lock:
            if not self._initialized:
                return False

            try:
                if pygame.mixer.music.get_busy():
                    self.log("Stopping playback")
                    pygame.mixer.music.stop()

                    # Wait a moment for stop to take effect
                    time.sleep(0.1)

                    self.current_file = None
                    self.log("Playback stopped successfully")
                    return True
                else:
                    # Not playing, but reset state anyway
                    self.current_file = None
                    return True

            except pygame.error as e:
                self.log(f"PYGAME ERROR during stop: {e}")
                self.current_file = None
                return False
            except Exception as e:
                self.log(f"EXCEPTION during stop: {e}")
                self.current_file = None
                return False

    def is_playing(self) -> bool:
        """Check if audio is currently playing."""
        if not self._initialized:
            return False

        try:
            busy = pygame.mixer.music.get_busy()

            # If pygame says not busy but we think we're playing, clear state
            if not busy and self.current_file:
                self.log("Playback ended unexpectedly, clearing state")
                self.current_file = None

            return busy

        except pygame.error:
            self.current_file = None
            return False
        except Exception:
            self.current_file = None
            return False

    def get_current(self) -> Optional[str]:
        """Get name of currently playing file."""
        if self.is_playing():
            return self.current_file
        else:
            # Clear state if not actually playing
            self.current_file = None
            return None

    def set_volume(self, volume: float) -> bool:
        """Set playback volume (0.0 to 1.0)."""
        if not self._initialized:
            return False

        try:
            volume = max(0.0, min(1.0, volume))
            pygame.mixer.music.set_volume(volume)
            self.log(f"Volume set to: {volume:.1%}")
            return True
        except Exception as e:
            self.log(f"Error setting volume: {e}")
            return False

    def get_volume(self) -> float:
        """Get current volume (0.0 to 1.0)."""
        if not self._initialized:
            return 0.0

        try:
            return pygame.mixer.music.get_volume()
        except:
            return 0.0

    def pause(self) -> bool:
        """Pause current playback."""
        if not self._initialized:
            return False

        try:
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.pause()
                self.log("Playback paused")
                return True
            return False
        except Exception as e:
            self.log(f"Error pausing: {e}")
            return False

    def unpause(self) -> bool:
        """Resume paused playback."""
        if not self._initialized:
            return False

        try:
            pygame.mixer.music.unpause()
            self.log("Playback resumed")
            return True
        except Exception as e:
            self.log(f"Error resuming: {e}")
            return False

    def get_status(self) -> dict:
        """Get detailed player status."""
        return {
            "initialized": self._initialized,
            "playing": self.is_playing(),
            "current_file": self.get_current(),
            "volume": self.get_volume(),
            "mixer_frequency": pygame.mixer.get_init()[0] if self._initialized and pygame.mixer.get_init() else None,
            "mixer_format": pygame.mixer.get_init()[1] if self._initialized and pygame.mixer.get_init() else None,
            "mixer_channels": pygame.mixer.get_init()[2] if self._initialized and pygame.mixer.get_init() else None
        }