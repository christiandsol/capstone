#!/bin/bash
set -e

# ------------------------
# Deployment script
# ------------------------

# Build the project
echo "Building frontend..."
npm install
npm run build
echo "Build finished."

# Versioned folder name (git short hash)
BUILD_ID=$(git rev-parse --short HEAD)
DEST="/var/www/builds/$BUILD_ID"

# Ensure parent directory exists (with sudo)
echo "Creating build directory $DEST..."
sudo mkdir -p "$DEST"

# Move the build to the versioned folder (with sudo)
echo "Moving build to $DEST..."
sudo mv dist "$DEST"

# Update the 'current' symlink to point to the new build (with sudo)
echo "Updating symlink /var/www/current -> $DEST"
sudo ln -sfn "$DEST" /var/www/current

echo "Deployment of build $BUILD_ID completed!"

