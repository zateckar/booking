#!/bin/bash
set -e

echo "🚀 Starting Booking Application..."
echo "Current user: $(id)"

# Ensure the data and logs directories exist
mkdir -p /app/data /app/logs

# Function to check and display directory permissions
check_permissions() {
    local dir=$1
    local name=$2
    
    echo "📁 Checking $name directory permissions..."
    echo "   Directory: $dir"
    echo "   Owner: $(stat -c '%U:%G' "$dir" 2>/dev/null || echo 'unknown')"
    echo "   Permissions: $(stat -c '%a' "$dir" 2>/dev/null || echo 'unknown')"
    
    if [ -w "$dir" ]; then
        echo "   ✅ Writable"
        return 0
    else
        echo "   ❌ Not writable"
        return 1
    fi
}

# Check data directory permissions
if ! check_permissions "/app/data" "data"; then
    echo ""
    echo "⚠️  WARNING: /app/data directory is not writable by current user."
    echo "This is likely due to Docker volume mounting permissions."
    
    # Try to create a test file to double-check
    if ! touch /app/data/.write_test 2>/dev/null; then
        echo ""
        echo "❌ CRITICAL: Cannot write to /app/data directory."
        echo "The application will fail to create the database file."
        echo ""
        echo "🔧 SOLUTIONS:"
        echo "1. Use proper user mapping in docker-compose.yml:"
        echo "   DOCKER_USER=\"\$(id -u):\$(id -g)\" docker-compose up"
        echo ""
        echo "2. Or run as root (less secure):"
        echo "   Uncomment 'user: \"0:0\"' in docker-compose.override.yml"
        echo ""
        echo "3. Or fix volume permissions manually:"
        echo "   docker-compose down"
        echo "   docker volume rm booking_booking_data"
        echo "   docker-compose up"
        echo ""
        echo "4. Or use bind mounts for development:"
        echo "   Uncomment bind mount volumes in docker-compose.override.yml"
        echo ""
        exit 1
    else
        rm -f /app/data/.write_test
        echo "   ℹ️  Test file creation succeeded despite warning"
    fi
fi

# Check logs directory permissions
check_permissions "/app/logs" "logs"

echo ""
echo "✅ Permission checks completed successfully"
echo "🏃 Executing command: $@"
echo ""

# Execute the original command
exec "$@"
