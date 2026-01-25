#!/bin/bash
set -e

BUILD_ID=$(git rev-parse --short HEAD)

npm run build
mv dist /var/www/builds/$BUILD_ID
ln -sfn /var/www/builds/$BUILD_ID /var/www/current

echo "Deployed build $BUILD_ID"
