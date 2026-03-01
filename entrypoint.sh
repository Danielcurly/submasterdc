#!/bin/bash
set -e

# Default to running as root if PUID/PGID are not set
PUID=${PUID:-0}
PGID=${PGID:-0}

# Create a group and user if we are mapping to a non-root user
if [ "$PUID" -ne 0 ]; then
    echo "Starting with UID: $PUID, GID: $PGID"
    
    # Check if group already exists
    if ! getent group "$PGID" >/dev/null; then
        groupadd -g "$PGID" appgroup
    fi
    
    # Check if user already exists
    if ! getent passwd "$PUID" >/dev/null; then
        useradd -u "$PUID" -g "$PGID" -d /app -s /bin/bash appuser
    fi

    # Assuming /app/data and /app/logs should be owned by the user
    mkdir -p /app/data /app/logs
    chown -R "$PUID:$PGID" /app/data /app/logs
    
    # Switch to the created user to run the app
    exec gosu "$PUID:$PGID" "$@"
else
    echo "Starting as root"
    exec "$@"
fi
