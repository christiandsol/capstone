#!/bin/bash
set -e

echo "Building frontend..."
npm install
npm run build
echo "Build finished."

# Versioned build folder name based on git commit hash
BUILD_ID=$(git rev-parse --short HEAD)
DEST="/var/www/builds/$BUILD_ID"

echo "Creating build directory $DEST..."
sudo mkdir -p "$DEST"

echo "Copying build files..."
sudo cp -r dist/* "$DEST/"

echo "Setting permissions..."
sudo chmod -R 755 /var/www/builds

# Update the 'current' symlink to point to the new build
echo "Updating symlink /var/www/current -> $DEST"
sudo ln -sfn "$DEST" /var/www/current


echo "Deployment of build $BUILD_ID completed!"

