#!/bin/sh
# Copy default config files into the mounted volume if they don't exist yet.
# This handles first-run when the host directory is empty.

if [ ! -f /app/config/config.yaml ]; then
    cp /app/config-defaults/config.yaml /app/config/config.yaml
    echo "Copied default config.yaml to /app/config/"
fi

if [ ! -f /app/config/config.yaml.example ]; then
    cp /app/config-defaults/config.yaml.example /app/config/config.yaml.example
    echo "Copied config.yaml.example to /app/config/"
fi

exec "$@"
