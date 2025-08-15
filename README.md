# Audio Server

A lightweight network audio playback service with REST API for managing and playing audio files remotely.

## What it does

The service provides a simple HTTP API to upload, store, and play MP3 audio files on a remote machine. It supports:
- File storage with persistent disk storage
- Playback control (play/stop)
- File management (upload/delete/list)
- Single audio stream (one file playing at a time)
- Automatic looping of played files

## How it works

The service runs as a systemd daemon listening on port 8888 (configurable). Audio files are stored in `/var/lib/audio-server/data` and persist across service restarts. When a play request is received, the server uses `mpg123` to play the audio file on the default audio output device in a continuous loop until stopped.

## Installation

Build and install the deb package:
```bash
./build-deb.sh
sudo dpkg -i build/audio-server_*_all.deb
```

## Usage

### Web Console
Access the web console at `http://localhost:8888` for a visual interface to manage and play audio files.

### CLI Commands

```bash
# Check server status and configuration
audio-server status

# Change server port (requires restart)
audio-server set-port 9000

# Show help
audio-server help
```

### Upload an audio file
```bash
curl -X PUT http://localhost:8888/api/audio/alarm \
  --data-binary @alarm.mp3
```

### Play an audio file
```bash
curl -X POST http://localhost:8888/api/play/alarm
```

### Stop playback
```bash
curl -X POST http://localhost:8888/api/stop
```

### Check server status
```bash
curl http://localhost:8888/api/status
```

### List available files
```bash
curl http://localhost:8888/api/audio
```

### Delete an audio file
```bash
curl -X DELETE http://localhost:8888/api/audio/alarm
```

## REST API

Complete REST API documentation is available in the `audio-server-openapi.yaml` file, which can be imported into Postman or any OpenAPI-compatible tool.

### Endpoints

- `GET /api/status` - Get server status and current playback
- `GET /api/audio` - List all stored audio files
- `GET /api/audio/{name}` - Check if file exists
- `PUT /api/audio/{name}` - Upload/save audio file
- `DELETE /api/audio/{name}` - Delete audio file
- `POST /api/play/{name}` - Start playing audio file
- `POST /api/stop` - Stop current playback

## Configuration

The service configuration is stored in `/etc/audio-server/config.json`:
```json
{
  "port": 8888,
  "storage_dir": "/var/lib/audio-server/data"
}
```

Changes require service restart:
```bash
sudo systemctl restart audio-server
```

## System Requirements

- Python 3.7 or higher
- mpg123 (installed automatically with package)
- Systemd
- Audio output device

## Service Management

```bash
# Check status
sudo systemctl status audio-server

# Start/stop/restart
sudo systemctl start audio-server
sudo systemctl stop audio-server
sudo systemctl restart audio-server

# View logs
sudo journalctl -u audio-server -f
```

## Uninstallation

```bash
# Remove package
sudo dpkg -r audio-server

# Remove package and all data
sudo dpkg -r --purge audio-server
```