#!/bin/bash
set -e

# Build
npm run build

# Versioned folder
BUILD_ID=$(git rev-parse --short HEAD)
DEST="/var/www/builds/$BUILD_ID"

# Make sure parent directory exists
mkdir -p "$DEST"

# Move build there
mv dist "$DEST"

# Update symlink
ln -sfn "$DEST" /var/www/current

echo "Deployed build $BUILD_ID"

