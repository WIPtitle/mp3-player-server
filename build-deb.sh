#!/bin/bash

PACKAGE_NAME="mp3-player-server"
VERSION="1.5.0"
ARCH="all"
MAINTAINER="Your Name <your.email@example.com>"
DESCRIPTION="Network audio playback service with file storage and volume control"

BUILD_DIR="./build"
PACKAGE_DIR="${BUILD_DIR}/${PACKAGE_NAME}_${VERSION}_${ARCH}"

echo "Building ${PACKAGE_NAME} version ${VERSION}..."

# Clean build directory
rm -rf ${BUILD_DIR}
mkdir -p ${BUILD_DIR}

# Create package structure
mkdir -p ${PACKAGE_DIR}/DEBIAN
mkdir -p ${PACKAGE_DIR}/usr/lib/mp3-player-server/mp3_player_server
mkdir -p ${PACKAGE_DIR}/usr/lib/mp3-player-server/web
mkdir -p ${PACKAGE_DIR}/usr/bin
mkdir -p ${PACKAGE_DIR}/etc/mp3-player-server
mkdir -p ${PACKAGE_DIR}/lib/systemd/system
mkdir -p ${PACKAGE_DIR}/usr/share/doc/mp3-player-server
mkdir -p ${PACKAGE_DIR}/var/lib/mp3-player-server/data

# Create control file
cat > ${PACKAGE_DIR}/DEBIAN/control << EOF
Package: ${PACKAGE_NAME}
Version: ${VERSION}
Section: utils
Priority: optional
Architecture: ${ARCH}
Maintainer: ${MAINTAINER}
Description: ${DESCRIPTION}
 MP3 Player Server provides a REST API for managing and playing mp3 files
 over the network. Features include file storage, playback control with
 volume adjustment (0-100%), audio device selection, and simple HTTP API
 for integration.
Depends: python3 (>= 3.7), systemd, mpg123, alsa-utils
EOF

# Create postinst script
cat > ${PACKAGE_DIR}/DEBIAN/postinst << 'EOF'
#!/bin/bash
set -e

# Create default config if not exists
if [ ! -f /etc/mp3-player-server/config.json ]; then
    echo '{"port": 8888, "storage_dir": "/var/lib/mp3-player-server/data", "audio_device": null}' > /etc/mp3-player-server/config.json
fi

# Set permissions
chmod 755 /var/lib/mp3-player-server
chmod 755 /var/lib/mp3-player-server/data

systemctl daemon-reload
systemctl enable mp3-player-server.service
systemctl start mp3-player-server.service

echo ""
echo "MP3 Player Server installed successfully!"
echo ""
echo "Commands:"
echo "  mp3-player-server status       - Show server status"
echo "  mp3-player-server set-port     - Change server port"
echo ""
echo "API endpoint: http://localhost:8888"
echo "Storage directory: /var/lib/mp3-player-server/data"
echo "Configuration: /etc/mp3-player-server/config.json"
echo ""
echo "NOTE: Select an audio device in the web interface before playing files"
echo "      Volume control is now available (0-100%)"
echo ""

exit 0
EOF

# Create prerm script
cat > ${PACKAGE_DIR}/DEBIAN/prerm << 'EOF'
#!/bin/bash
set -e

systemctl stop mp3-player-server.service || true
systemctl disable mp3-player-server.service || true

exit 0
EOF

# Create postrm script
cat > ${PACKAGE_DIR}/DEBIAN/postrm << 'EOF'
#!/bin/bash
set -e

if [ "$1" = "purge" ]; then
    rm -rf /etc/mp3-player-server
    rm -rf /var/lib/mp3-player-server
fi

systemctl daemon-reload

exit 0
EOF

# Set permissions for DEBIAN scripts
chmod 755 ${PACKAGE_DIR}/DEBIAN/postinst
chmod 755 ${PACKAGE_DIR}/DEBIAN/prerm
chmod 755 ${PACKAGE_DIR}/DEBIAN/postrm

# Copy Python modules
cp -r mp3_player_server/* ${PACKAGE_DIR}/usr/lib/mp3-player-server/mp3_player_server/
chmod -R 755 ${PACKAGE_DIR}/usr/lib/mp3-player-server/mp3_player_server/

# Copy main script
cp mp3-player-server-main.py ${PACKAGE_DIR}/usr/lib/mp3-player-server/
chmod 755 ${PACKAGE_DIR}/usr/lib/mp3-player-server/mp3-player-server-main.py

# Copy web files
cp web/index.html ${PACKAGE_DIR}/usr/lib/mp3-player-server/web/
chmod 644 ${PACKAGE_DIR}/usr/lib/mp3-player-server/web/index.html

# Copy CLI script
cp mp3-player-server-cli.py ${PACKAGE_DIR}/usr/bin/mp3-player-server
chmod 755 ${PACKAGE_DIR}/usr/bin/mp3-player-server

# Copy systemd service
cp debian/mp3-player-server.service ${PACKAGE_DIR}/lib/systemd/system/
chmod 644 ${PACKAGE_DIR}/lib/systemd/system/mp3-player-server.service

# Config is created by postinst only if it doesn't exist (preserves existing config on upgrade)

# Copy documentation
if [ -f README.md ]; then
    cp README.md ${PACKAGE_DIR}/usr/share/doc/mp3-player-server/
fi

if [ -f docs/mp3-player-server-openapi.yaml ]; then
    cp docs/mp3-player-server-openapi.yaml ${PACKAGE_DIR}/usr/share/doc/mp3-player-server/
    chmod 644 ${PACKAGE_DIR}/usr/share/doc/mp3-player-server/mp3-player-server-openapi.yaml
fi

# Create version file
echo "${VERSION}" > ${PACKAGE_DIR}/usr/share/doc/mp3-player-server/VERSION

# Build the package
dpkg-deb --build ${PACKAGE_DIR}

if [ $? -eq 0 ]; then
    echo ""
    echo "Package built successfully: ${BUILD_DIR}/${PACKAGE_NAME}_${VERSION}_${ARCH}.deb"
    echo ""
    echo "To install:"
    echo "  sudo dpkg -i ${BUILD_DIR}/${PACKAGE_NAME}_${VERSION}_${ARCH}.deb"
    echo ""
    echo "To uninstall:"
    echo "  sudo dpkg -r ${PACKAGE_NAME}"
    echo ""
    echo "New in version ${VERSION}:"
    echo "  - Volume control (0-100%) with required parameter"
    echo "  - Web console volume slider"
    echo "  - Quick volume presets"
else
    echo "Error: Package build failed"
    exit 1
fi