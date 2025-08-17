#!/bin/bash

PACKAGE_NAME="audio-server"
VERSION="1.4.0"
ARCH="all"
MAINTAINER="Your Name <your.email@example.com>"
DESCRIPTION="Network audio playback service with file storage"

BUILD_DIR="./build"
PACKAGE_DIR="${BUILD_DIR}/${PACKAGE_NAME}_${VERSION}_${ARCH}"

echo "Building ${PACKAGE_NAME} version ${VERSION}..."

# Clean build directory
rm -rf ${BUILD_DIR}
mkdir -p ${BUILD_DIR}

# Create package structure
mkdir -p ${PACKAGE_DIR}/DEBIAN
mkdir -p ${PACKAGE_DIR}/usr/lib/audio-server/audio_server
mkdir -p ${PACKAGE_DIR}/usr/lib/audio-server/web
mkdir -p ${PACKAGE_DIR}/usr/bin
mkdir -p ${PACKAGE_DIR}/etc/audio-server
mkdir -p ${PACKAGE_DIR}/lib/systemd/system
mkdir -p ${PACKAGE_DIR}/usr/share/doc/audio-server
mkdir -p ${PACKAGE_DIR}/var/lib/audio-server/data

# Create control file
cat > ${PACKAGE_DIR}/DEBIAN/control << EOF
Package: ${PACKAGE_NAME}
Version: ${VERSION}
Section: utils
Priority: optional
Architecture: ${ARCH}
Maintainer: ${MAINTAINER}
Description: ${DESCRIPTION}
 Audio Server provides a REST API for managing and playing audio files
 over the network. Features include file storage, playback control,
 audio device selection, and simple HTTP API for integration.
Depends: python3 (>= 3.7), systemd, mpg123, alsa-utils
EOF

# Create postinst script
cat > ${PACKAGE_DIR}/DEBIAN/postinst << 'EOF'
#!/bin/bash
set -e

# Create default config if not exists
if [ ! -f /etc/audio-server/config.json ]; then
    echo '{"port": 8888, "storage_dir": "/var/lib/audio-server/data", "audio_device": null}' > /etc/audio-server/config.json
fi

# Set permissions
chmod 755 /var/lib/audio-server
chmod 755 /var/lib/audio-server/data

systemctl daemon-reload
systemctl enable audio-server.service
systemctl start audio-server.service

echo ""
echo "Audio Server installed successfully!"
echo ""
echo "Commands:"
echo "  audio-server status       - Show server status"
echo "  audio-server set-port     - Change server port"
echo ""
echo "API endpoint: http://localhost:8888"
echo "Storage directory: /var/lib/audio-server/data"
echo "Configuration: /etc/audio-server/config.json"
echo ""
echo "NOTE: Select an audio device in the web interface before playing files"
echo ""

exit 0
EOF

# Create prerm script
cat > ${PACKAGE_DIR}/DEBIAN/prerm << 'EOF'
#!/bin/bash
set -e

systemctl stop audio-server.service || true
systemctl disable audio-server.service || true

exit 0
EOF

# Create postrm script
cat > ${PACKAGE_DIR}/DEBIAN/postrm << 'EOF'
#!/bin/bash
set -e

if [ "$1" = "purge" ]; then
    rm -rf /etc/audio-server
    rm -rf /var/lib/audio-server
fi

systemctl daemon-reload

exit 0
EOF

# Set permissions for DEBIAN scripts
chmod 755 ${PACKAGE_DIR}/DEBIAN/postinst
chmod 755 ${PACKAGE_DIR}/DEBIAN/prerm
chmod 755 ${PACKAGE_DIR}/DEBIAN/postrm

# Copy Python modules
cp -r audio_server/* ${PACKAGE_DIR}/usr/lib/audio-server/audio_server/
chmod -R 755 ${PACKAGE_DIR}/usr/lib/audio-server/audio_server/

# Copy main script
cp audio-server-main.py ${PACKAGE_DIR}/usr/lib/audio-server/
chmod 755 ${PACKAGE_DIR}/usr/lib/audio-server/audio-server-main.py

# Copy web files
cp web/index.html ${PACKAGE_DIR}/usr/lib/audio-server/web/
chmod 644 ${PACKAGE_DIR}/usr/lib/audio-server/web/index.html

# Copy CLI script
cp audio-server-cli.py ${PACKAGE_DIR}/usr/bin/audio-server
chmod 755 ${PACKAGE_DIR}/usr/bin/audio-server

# Copy systemd service
cp debian/audio-server.service ${PACKAGE_DIR}/lib/systemd/system/
chmod 644 ${PACKAGE_DIR}/lib/systemd/system/audio-server.service

# Create default config
echo '{"port": 8888, "storage_dir": "/var/lib/audio-server/data", "audio_device": null}' > ${PACKAGE_DIR}/etc/audio-server/config.json
chmod 644 ${PACKAGE_DIR}/etc/audio-server/config.json

# Copy documentation
if [ -f README.md ]; then
    cp README.md ${PACKAGE_DIR}/usr/share/doc/audio-server/
fi

if [ -f docs/audio-server-openapi.yaml ]; then
    cp docs/audio-server-openapi.yaml ${PACKAGE_DIR}/usr/share/doc/audio-server/
    chmod 644 ${PACKAGE_DIR}/usr/share/doc/audio-server/audio-server-openapi.yaml
fi

# Create version file
echo "${VERSION}" > ${PACKAGE_DIR}/usr/share/doc/audio-server/VERSION

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
else
    echo "Error: Package build failed"
    exit 1
fi