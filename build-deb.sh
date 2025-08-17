#!/bin/bash

PACKAGE_NAME="audio-server"
VERSION="1.3.0"
ARCH="all"
MAINTAINER="Your Name <your.email@example.com>"
DESCRIPTION="Network audio playbook service running as user service"

BUILD_DIR="./build"
PACKAGE_DIR="${BUILD_DIR}/${PACKAGE_NAME}_${VERSION}_${ARCH}"

echo "Building ${PACKAGE_NAME} version ${VERSION} (User Service)..."

# Clean build directory
rm -rf ${BUILD_DIR}
mkdir -p ${BUILD_DIR}

# Create package structure for user service
mkdir -p ${PACKAGE_DIR}/DEBIAN
mkdir -p ${PACKAGE_DIR}/usr/lib/audio-server/audio_server
mkdir -p ${PACKAGE_DIR}/usr/lib/audio-server/web
mkdir -p ${PACKAGE_DIR}/usr/bin
mkdir -p ${PACKAGE_DIR}/usr/share/audio-server
mkdir -p ${PACKAGE_DIR}/usr/share/doc/audio-server

# Create control file
cat > ${PACKAGE_DIR}/DEBIAN/control << EOF
Package: ${PACKAGE_NAME}
Version: ${VERSION}
Section: utils
Priority: optional
Architecture: ${ARCH}
Maintainer: ${MAINTAINER}
Description: ${DESCRIPTION}
 Audio Server provides a REST API for managing and playing audio files.
 Runs as user systemd service with full audio access. Configurations
 stored in user directory, no root privileges required for operation.
 Features gapless loop playback, volume control, and HTTP API.
Depends: python3 (>= 3.7), systemd, python3-pygame, sudo
EOF

# Create postinst script for user service setup
cat > ${PACKAGE_DIR}/DEBIAN/postinst << 'EOF'
#!/bin/bash
set -e

echo "Setting up Audio Server user service..."

# Function to setup for specific user
setup_for_user() {
    local username="$1"
    local user_home="$2"

    echo "Setting up Audio Server for user: $username"

    # Create user directories
    sudo -u "$username" mkdir -p "$user_home/.config/audio-server"
    sudo -u "$username" mkdir -p "$user_home/.local/share/audio-server/data"

    # Create user config
    if [ ! -f "$user_home/.config/audio-server/config.json" ]; then
        sudo -u "$username" sh -c "echo '{\"port\": 8888, \"storage_dir\": \"$user_home/.local/share/audio-server/data\"}' > '$user_home/.config/audio-server/config.json'"
    fi

    # Create user systemd service
    sudo -u "$username" mkdir -p "$user_home/.config/systemd/user"

    cat > "/tmp/audio-server-user.service" << SERVICE_EOF
[Unit]
Description=Audio Server (User Service)
After=graphical-session.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 -u /usr/lib/audio-server/audio-server-main.py --user-mode
Restart=on-failure
RestartSec=5
Environment="PYTHONUNBUFFERED=1"
WorkingDirectory=/usr/lib/audio-server

[Install]
WantedBy=default.target
SERVICE_EOF

    sudo -u "$username" cp "/tmp/audio-server-user.service" "$user_home/.config/systemd/user/audio-server.service"
    rm "/tmp/audio-server-user.service"

    # Enable lingering first (this creates user session if needed)
    echo "Enabling lingering for $username..."
    loginctl enable-linger "$username" 2>/dev/null || {
        echo "⚠️  Could not enable lingering (may need manual setup)"
    }

    # Wait a moment for linger to take effect
    sleep 2

    # Check if user has systemd session
    if sudo -u "$username" systemctl --user status >/dev/null 2>&1; then
        echo "✅ User systemd session available"

        # Enable and start service
        sudo -u "$username" systemctl --user daemon-reload
        sudo -u "$username" systemctl --user enable audio-server.service

        if sudo -u "$username" systemctl --user start audio-server.service; then
            echo "✅ Audio Server started successfully for $username"
            echo "🌐 Access: http://localhost:8888"
        else
            echo "⚠️  Service creation successful but start failed"
            echo "   You can start it manually after login:"
            echo "   systemctl --user start audio-server"
        fi
    else
        echo "⚠️  No active user session detected (headless system?)"
        echo "✅ Service files created successfully"
        echo ""
        echo "🔧 Manual startup required:"
        echo "   1. Login as $username (SSH or console)"
        echo "   2. Run: systemctl --user start audio-server"
        echo "   3. Enable auto-start: systemctl --user enable audio-server"
        echo ""
        echo "Or run the setup script after login:"
        echo "   /usr/share/audio-server/setup-user.sh"
    fi

    echo ""
    echo "📁 Configuration:"
    echo "   Config: $user_home/.config/audio-server/"
    echo "   Storage: $user_home/.local/share/audio-server/data/"
    echo ""
    echo "🔧 User management commands:"
    echo "   systemctl --user status audio-server"
    echo "   systemctl --user restart audio-server"
    echo "   journalctl --user -u audio-server -f"

    return 0
}

# Detect installation context
INSTALL_USER=""
INSTALL_HOME=""

# Method 1: SUDO_USER (most common)
if [ -n "$SUDO_USER" ] && [ "$SUDO_USER" != "root" ]; then
    INSTALL_USER="$SUDO_USER"
    INSTALL_HOME=$(getent passwd "$SUDO_USER" | cut -d: -f6)
    echo "Detected installation by user: $INSTALL_USER"
fi

# Method 2: Check if we're in a user context despite running as root
if [ -z "$INSTALL_USER" ]; then
    # Look for active desktop session
    if command -v who >/dev/null 2>&1; then
        ACTIVE_USER=$(who | grep '(:0' | head -1 | awk '{print $1}')
        if [ -n "$ACTIVE_USER" ] && [ "$ACTIVE_USER" != "root" ]; then
            INSTALL_USER="$ACTIVE_USER"
            INSTALL_HOME=$(getent passwd "$ACTIVE_USER" | cut -d: -f6)
            echo "Detected active desktop user: $INSTALL_USER"
        fi
    fi
fi

# Method 3: First normal user as fallback
if [ -z "$INSTALL_USER" ]; then
    FIRST_USER=$(getent passwd | awk -F: '$3 >= 1000 && $3 < 65534 { print $1; exit }')
    if [ -n "$FIRST_USER" ]; then
        INSTALL_USER="$FIRST_USER"
        INSTALL_HOME=$(getent passwd "$FIRST_USER" | cut -d: -f6)
        echo "Using first normal user: $INSTALL_USER"
    fi
fi

if [ -n "$INSTALL_USER" ] && [ -n "$INSTALL_HOME" ]; then
    setup_for_user "$INSTALL_USER" "$INSTALL_HOME"
else
    echo "⚠️  Could not detect target user for installation"
    echo ""
    echo "Manual setup required:"
    echo "   /usr/share/audio-server/setup-user.sh"
    echo ""
    echo "Or setup for specific user:"
    echo "   sudo -u USERNAME /usr/share/audio-server/setup-user.sh"
fi

echo ""
echo "🎵 Audio Server installation completed!"

exit 0
EOF

# Create prerm script
cat > ${PACKAGE_DIR}/DEBIAN/prerm << 'EOF'
#!/bin/bash
set -e

echo "Removing Audio Server user services..."

# Try to stop services for all users who might have it
for user_home in /home/*; do
    if [ -d "$user_home" ] && [ -f "$user_home/.config/systemd/user/audio-server.service" ]; then
        username=$(basename "$user_home")
        echo "Stopping Audio Server for user: $username"

        sudo -u "$username" systemctl --user stop audio-server.service 2>/dev/null || true
        sudo -u "$username" systemctl --user disable audio-server.service 2>/dev/null || true
    fi
done

exit 0
EOF

# Create postrm script
cat > ${PACKAGE_DIR}/DEBIAN/postrm << 'EOF'
#!/bin/bash
set -e

if [ "$1" = "purge" ]; then
    echo "Removing Audio Server user data..."

    # Remove user configs and data if requested
    for user_home in /home/*; do
        if [ -d "$user_home/.config/audio-server" ]; then
            username=$(basename "$user_home")
            echo "Removing config for user: $username"
            rm -rf "$user_home/.config/audio-server"
            rm -rf "$user_home/.local/share/audio-server"
            rm -f "$user_home/.config/systemd/user/audio-server.service"
        fi
    done
fi

exit 0
EOF

# Set permissions for DEBIAN scripts
chmod 755 ${PACKAGE_DIR}/DEBIAN/postinst
chmod 755 ${PACKAGE_DIR}/DEBIAN/prerm
chmod 755 ${PACKAGE_DIR}/DEBIAN/postrm

# Copy Python modules (use original AudioPlayer, not dual-process)
cp -r audio_server/* ${PACKAGE_DIR}/usr/lib/audio-server/audio_server/
chmod -R 755 ${PACKAGE_DIR}/usr/lib/audio-server/audio_server/

# Copy main script (needs --user-mode support)
cp audio-server-main.py ${PACKAGE_DIR}/usr/lib/audio-server/
chmod 755 ${PACKAGE_DIR}/usr/lib/audio-server/audio-server-main.py

# Copy web files
cp web/index.html ${PACKAGE_DIR}/usr/lib/audio-server/web/
chmod 644 ${PACKAGE_DIR}/usr/lib/audio-server/web/index.html

# Create user setup script for manual installation
cat > ${PACKAGE_DIR}/usr/share/audio-server/setup-user.sh << 'EOF'
#!/bin/bash

echo "🎵 Audio Server User Setup"
echo "=========================="

CURRENT_USER=$(whoami)

if [ "$CURRENT_USER" = "root" ]; then
    echo "❌ Don't run this as root!"
    echo "   Run as the user who will use Audio Server:"
    echo "   ./setup-user.sh"
    exit 1
fi

echo "Setting up Audio Server for user: $CURRENT_USER"

# Create user directories
mkdir -p ~/.config/audio-server
mkdir -p ~/.local/share/audio-server/data

# Create user config
if [ ! -f ~/.config/audio-server/config.json ]; then
    echo '{"port": 8888, "storage_dir": "'$HOME'/.local/share/audio-server/data"}' > ~/.config/audio-server/config.json
fi

# Create user systemd directory
mkdir -p ~/.config/systemd/user

# Create user service file
cat > ~/.config/systemd/user/audio-server.service << 'SERVICE_EOF'
[Unit]
Description=Audio Server (User Service)
After=graphical-session.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 -u /usr/lib/audio-server/audio-server-main.py --user-mode
Restart=on-failure
RestartSec=5
Environment="PYTHONUNBUFFERED=1"
WorkingDirectory=/usr/lib/audio-server

[Install]
WantedBy=default.target
SERVICE_EOF

# Reload and enable
systemctl --user daemon-reload
systemctl --user enable audio-server.service

# Enable lingering
loginctl enable-linger $CURRENT_USER 2>/dev/null || echo "Note: Could not enable lingering (service won't auto-start on boot)"

# Start service
systemctl --user start audio-server.service

echo ""
if systemctl --user is-active --quiet audio-server.service; then
    echo "✅ Audio Server started successfully!"
    echo ""
    echo "🌐 Access: http://localhost:8888"
    echo "📁 Config: ~/.config/audio-server/"
    echo "📁 Storage: ~/.local/share/audio-server/data/"
    echo ""
    echo "🔧 Management commands:"
    echo "   systemctl --user status audio-server"
    echo "   systemctl --user restart audio-server"
    echo "   systemctl --user stop audio-server"
    echo "   journalctl --user -u audio-server -f"
    echo ""
    echo "🚀 Auto-start enabled (service will start automatically)"
else
    echo "❌ Service failed to start. Check logs:"
    echo "   journalctl --user -u audio-server -n 20"
fi
EOF

chmod 755 ${PACKAGE_DIR}/usr/share/audio-server/setup-user.sh

# Copy CLI script (modified for user service)
cat > ${PACKAGE_DIR}/usr/bin/audio-server << 'EOF'
#!/usr/bin/python3
"""Command-line interface for Audio Server (User Service)."""

import sys
import json
import os
import subprocess

def load_config():
    """Load user configuration."""
    config_file = os.path.expanduser("~/.config/audio-server/config.json")
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            return json.load(f)
    return {"port": 8888, "storage_dir": os.path.expanduser("~/.local/share/audio-server/data")}

def save_config(config):
    """Save user configuration."""
    config_file = os.path.expanduser("~/.config/audio-server/config.json")
    os.makedirs(os.path.dirname(config_file), exist_ok=True)
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)

def set_port(port):
    """Set server port and restart user service."""
    try:
        port = int(port)
        if port < 1 or port > 65535:
            print("Error: Port must be between 1 and 65535")
            sys.exit(1)

        config = load_config()
        old_port = config.get("port", 8888)

        if old_port == port:
            print(f"Port is already set to {port}")
            return

        config["port"] = port
        save_config(config)

        print(f"Port set to {port}")
        print("Restarting user service...")

        try:
            subprocess.run(["systemctl", "--user", "restart", "audio-server.service"], check=True)
            print("Service restarted successfully")
            print(f"Audio Server now listening on port {port}")
        except subprocess.CalledProcessError:
            print("Error: Failed to restart service")
            print("Try: systemctl --user restart audio-server")

    except ValueError:
        print("Error: Invalid port number")
        sys.exit(1)

def get_status():
    """Show current configuration and service status."""
    config = load_config()
    port = config.get("port", 8888)
    storage_dir = config.get("storage_dir", "~/.local/share/audio-server/data")

    print(f"Current port: {port}")
    print(f"Storage directory: {storage_dir}")

    try:
        result = subprocess.run(["systemctl", "--user", "is-active", "audio-server.service"],
                                capture_output=True, text=True)
        status = result.stdout.strip()
        print(f"Service status: {status}")

        if status == "active":
            print(f"API endpoint: http://localhost:{port}")
            print(f"Config: ~/.config/audio-server/")
    except:
        print("Service status: unknown")

def show_help():
    """Show help message."""
    print("Audio Server Control (User Service)")
    print("")
    print("Commands:")
    print("  audio-server status         Show current configuration and status")
    print("  audio-server set-port PORT  Set server port (requires restart)")
    print("  audio-server help           Show this help message")
    print("")
    print("User service control:")
    print("  systemctl --user start audio-server      Start service")
    print("  systemctl --user stop audio-server       Stop service")
    print("  systemctl --user restart audio-server    Restart service")
    print("  journalctl --user -u audio-server -f     View logs")
    print("")
    print("Files:")
    print("  ~/.config/audio-server/config.json       Configuration")
    print("  ~/.local/share/audio-server/data/         Audio files")

def main():
    if len(sys.argv) < 2:
        show_help()
        sys.exit(0)

    command = sys.argv[1]

    if command == "status":
        get_status()
    elif command == "set-port" and len(sys.argv) == 3:
        set_port(sys.argv[2])
    elif command == "help" or command == "--help" or command == "-h":
        show_help()
    else:
        print(f"Unknown command: {command}")
        print("Use 'audio-server help' for usage information")
        sys.exit(1)

if __name__ == "__main__":
    main()
EOF

chmod 755 ${PACKAGE_DIR}/usr/bin/audio-server

# Copy documentation
if [ -f README.md ]; then
    cp README.md ${PACKAGE_DIR}/usr/share/doc/audio-server/
fi

# Create user service documentation
cat > ${PACKAGE_DIR}/usr/share/doc/audio-server/USER-SERVICE.md << 'EOF'
# Audio Server - User Service Mode

Audio Server runs as a user systemd service, solving all audio permission issues.

## Architecture

- **Service**: Runs as your user account with full audio access
- **Configs**: `~/.config/audio-server/`
- **Storage**: `~/.local/share/audio-server/data/`
- **No root**: No root permissions needed for operation

## Installation

The package automatically sets up the service for the installing user.

## Manual Setup

If automatic setup failed:

```bash
/usr/share/audio-server/setup-user.sh
```

## Management Commands

```bash
# Service control
systemctl --user start audio-server
systemctl --user stop audio-server
systemctl --user restart audio-server
systemctl --user status audio-server

# View logs
journalctl --user -u audio-server -f

# Configuration
audio-server status
audio-server set-port 9000
```

## Auto-Start

Service automatically starts when you log in. To disable:

```bash
systemctl --user disable audio-server
```

## Multiple Users

Each user can run their own Audio Server instance:

```bash
# User 1: http://localhost:8888
# User 2: http://localhost:8889 (if they change port)
```

## Benefits

- ✅ Full audio access (no permission issues)
- ✅ User-specific configurations
- ✅ Works on all Linux distributions
- ✅ Simple management
- ✅ No root privileges required
- ✅ Multiple instances supported
EOF

# Create version file
echo "${VERSION}" > ${PACKAGE_DIR}/usr/share/doc/audio-server/VERSION

# Build the package
dpkg-deb --build ${PACKAGE_DIR}

if [ $? -eq 0 ]; then
    echo ""
    echo "📦 Package built successfully: ${BUILD_DIR}/${PACKAGE_NAME}_${VERSION}_${ARCH}.deb"
    echo ""
    echo "🎵 Audio Server v${VERSION} - User Service Edition"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "✨ USER SERVICE FEATURES:"
    echo "   • Runs as your user account (full audio access)"
    echo "   • Configurations in ~/.config/audio-server/"
    echo "   • Audio files in ~/.local/share/audio-server/data/"
    echo "   • Auto-detects installing user"
    echo "   • No root privileges needed for operation"
    echo "   • Auto-start on login"
    echo ""
    echo "🚀 INSTALLATION:"
    echo "   sudo apt install ./${BUILD_DIR}/${PACKAGE_NAME}_${VERSION}_${ARCH}.deb"
    echo ""
    echo "📋 POST-INSTALL:"
    echo "   • Service auto-configured for installing user"
    echo "   • Access: http://localhost:8888"
    echo "   • Manage: audio-server status"
    echo "   • Logs: journalctl --user -u audio-server -f"
    echo ""
    echo "🔧 MANUAL SETUP (if auto-setup fails):"
    echo "   /usr/share/audio-server/setup-user.sh"
    echo ""
else
    echo "❌ Error: Package build failed"
    exit 1
fi