#!/bin/bash
set -e

# Ensure the data and logs directories exist and are writable
mkdir -p /app/data /app/logs

# Check if we can write to the data directory
if [ ! -w "/app/data" ]; then
    echo "Warning: /app/data directory is not writable by current user."
    echo "This is likely due to Docker volume mounting permissions."
    echo "The application may fail to create the database file."
    
    # Try to create a test file to verify write permissions
    if ! touch /app/data/.write_test 2>/dev/null; then
        echo "Error: Cannot write to /app/data directory."
        echo "Please ensure the Docker volume has proper permissions."
        echo "You may need to:"
        echo "  1. Run the container with proper user mapping"
        echo "  2. Or fix volume permissions manually"
        exit 1
    else
        rm -f /app/data/.write_test
        echo "Write permission check passed."
    fi
fi

# Execute the original command
exec "$@"
