#!/bin/bash
# Setup Docker log rotation for FreeHekim RAG API
# This script should be run with sudo on the server

set -e

echo "🔧 Setting up Docker log rotation..."

# Backup existing daemon.json if it exists
if [ -f /etc/docker/daemon.json ]; then
    echo "📦 Backing up existing /etc/docker/daemon.json"
    sudo cp /etc/docker/daemon.json /etc/docker/daemon.json.backup.$(date +%Y%m%d)
fi

# Copy new daemon.json
echo "📝 Installing log rotation config..."
sudo cp $(dirname "$0")/daemon.json /etc/docker/daemon.json

# Restart Docker daemon to apply changes
echo "🔄 Restarting Docker daemon..."
sudo systemctl restart docker

# Wait for Docker to start
echo "⏳ Waiting for Docker to start..."
sleep 5

# Verify Docker is running
if sudo systemctl is-active --quiet docker; then
    echo "✅ Docker daemon restarted successfully"
    echo "✅ Log rotation configured:"
    echo "   - Max log size: 10MB"
    echo "   - Max files: 3"
    echo "   - Compression: enabled"
else
    echo "❌ Error: Docker failed to start"
    echo "   Restoring backup..."
    if [ -f /etc/docker/daemon.json.backup.$(date +%Y%m%d) ]; then
        sudo cp /etc/docker/daemon.json.backup.$(date +%Y%m%d) /etc/docker/daemon.json
        sudo systemctl restart docker
    fi
    exit 1
fi

echo ""
echo "🎉 Log rotation setup complete!"
