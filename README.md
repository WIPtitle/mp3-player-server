# MP3 Player Server

A lightweight network audio playback service with REST API for managing and playing audio files remotely.

## What it does

The service provides HTTP API (documented under docs/) to upload and play MP3 audio files on a remote machine.
Features include:
- File storage with persistent disk storage
- Playback control (play/stop)
- File management (upload/delete/list)
- Single audio stream (one file playing at a time)
- Automatic looping of played files
- Web console for easy management

## How it works

The service runs as a systemd daemon listening on port 8888 (configurable). Audio files are stored in `/var/lib/mp3-player-server/data` and persist across service restarts. When a play request is received, the server uses `mpg123` to play the audio file on the selected audio output device.

## Installation

Build and install the deb package (this will also install `mpg123`):
```bash
./build-deb.sh
sudo apt install build/mp3-player-server_*_all.deb
```

## Usage

### Web Console
Access the web console at `http://localhost:8888` for a visual interface to manage and play audio files.

### CLI Commands

```bash
# Check server status and configuration
mp3-player-server status

# Change server port (requires restart)
mp3-player-server set-port 9000

# Show help
mp3-player-server help
```

## System Requirements

- Python 3.7 or higher
- mpg123 (installed automatically with package if using apt)
- Systemd
- Audio output device

## Service Management

```bash
# Check status
sudo systemctl status mp3-player-server

# Start/stop/restart
sudo systemctl start mp3-player-server
sudo systemctl stop mp3-player-server
sudo systemctl restart mp3-player-server

# View logs
sudo journalctl -u mp3-player-server -f
```

## Uninstallation

```bash
# Remove package
sudo dpkg -r mp3-player-server

# Remove package and all data
sudo dpkg -r --purge mp3-player-server
```