#!/usr/bin/python3
"""Audio file storage management."""

import os
from pathlib import Path
from typing import Optional


class AudioStorage:
    """Manages audio file storage on disk."""

    def __init__(self, storage_dir: str):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def save(self, name: str, data: bytes) -> None:
        """Save audio file to disk."""
        # Sanitize filename
        safe_name = os.path.basename(name)
        if not safe_name.endswith('.mp3'):
            safe_name += '.mp3'

        file_path = self.storage_dir / safe_name
        with open(file_path, 'wb') as f:
            f.write(data)

    def exists(self, name: str) -> bool:
        """Check if audio file exists."""
        safe_name = os.path.basename(name)
        if not safe_name.endswith('.mp3'):
            safe_name += '.mp3'

        file_path = self.storage_dir / safe_name
        return file_path.exists()

    def get_path(self, name: str) -> Optional[Path]:
        """Get full path to audio file."""
        if not self.exists(name):
            return None

        safe_name = os.path.basename(name)
        if not safe_name.endswith('.mp3'):
            safe_name += '.mp3'

        return self.storage_dir / safe_name

    def delete(self, name: str) -> bool:
        """Delete audio file."""
        file_path = self.get_path(name)
        if file_path and file_path.exists():
            file_path.unlink()
            return True
        return False

    def list_files(self) -> list:
        """List all stored audio files."""
        files = []
        for file_path in self.storage_dir.glob("*.mp3"):
            files.append(file_path.stem)
        return sorted(files)