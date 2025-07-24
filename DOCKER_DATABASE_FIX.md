# Docker Database Connection Fix

## Problem
When starting the booking application in a Docker container, you may encounter this error:
```
Warning: /app/data directory is not writable by current user.
This is likely due to Docker volume mounting permissions.
The application may fail to create the database file.
Error: Cannot write to /app/data directory.
```

## Root Cause
This error occurs due to Docker volume permission mismatches:

1. **User ID Conflicts**: The container user may not match the volume ownership
2. **Docker Volume Permission Issues**: Docker volume mounting can override directory permissions
3. **Platform Differences**: Different host systems (Linux, macOS, Windows) handle permissions differently

## Fixes Applied

### 1. Fixed User ID Mapping
- Updated Dockerfile to create user with UID/GID 1000:1000 to match docker-compose.yml
- This ensures consistent permissions between container and host

### 2. Enhanced Entrypoint Script
- Improved `entrypoint.sh` with detailed permission diagnostics
- Provides clear error messages and solution suggestions
- Shows directory ownership and permission information

### 3. Added Helper Script
- Created `docker-fix.sh` with automated solutions for common permission issues
- Provides multiple fix strategies with simple commands

## Quick Solutions

### Using the Helper Script (Recommended)
The easiest way to fix permission issues:

```bash
# Make the script executable (if not already)
chmod +x docker-fix.sh

# Test current setup
./docker-fix.sh test

# Try user mapping fix
./docker-fix.sh user-fix

# Or use bind mounts (development)
./docker-fix.sh bind-fix

# Or run as root (quick but less secure)
./docker-fix.sh root-fix

# Reset everything if needed
./docker-fix.sh reset
```

### Manual Solutions

#### Solution 1: User Mapping (Recommended)
```bash
# Use your actual UID:GID
DOCKER_USER="$(id -u):$(id -g)" docker-compose up
```

#### Solution 2: Root User (Quick Fix)
Create `docker-compose.override.yml`:
```yaml
services:
  booking-app:
    user: "0:0"
```

#### Solution 3: Bind Mounts (Development)
Create `docker-compose.override.yml`:
```yaml
services:
  booking-app:
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
```

#### Solution 4: Reset Volumes
```bash
docker-compose down
docker volume rm booking_booking_data booking_booking_logs
docker-compose up
```

## Testing the Fix

### Method 1: Using Helper Script
```bash
./docker-fix.sh test
```

### Method 2: Manual Testing
1. Stop any running containers:
   ```bash
   docker-compose down
   ```

2. Rebuild the image:
   ```bash
   docker-compose build --no-cache
   ```

3. Start the container:
   ```bash
   docker-compose up
   ```

4. Check the logs:
   ```bash
   docker-compose logs booking-app
   ```

### Expected Success Messages
You should see:
- "🚀 Starting Booking Application..."
- "✅ Writable" for both data and logs directories
- "✅ Permission checks completed successfully"
- "✅ Database schema is compatible"
- "✅ Initial admin user created successfully"

## Helper Script Commands

The `docker-fix.sh` script provides these commands:

- `./docker-fix.sh test` - Test current setup and show logs
- `./docker-fix.sh user-fix` - Use current user's UID:GID
- `./docker-fix.sh root-fix` - Run as root (creates override)
- `./docker-fix.sh bind-fix` - Use local directories (creates override)
- `./docker-fix.sh rebuild` - Rebuild image and restart
- `./docker-fix.sh reset` - Remove volumes and restart fresh
- `./docker-fix.sh clean` - Remove override file
- `./docker-fix.sh logs` - Show container logs
- `./docker-fix.sh help` - Show all commands

## Troubleshooting

### Still Getting Permission Errors?

1. **Check your platform**: 
   - Linux: User mapping usually works best
   - macOS: Bind mounts often work better
   - Windows: Root user might be needed

2. **Try different solutions in order**:
   ```bash
   ./docker-fix.sh user-fix    # Try this first
   ./docker-fix.sh bind-fix    # If user-fix doesn't work
   ./docker-fix.sh root-fix    # Last resort
   ```

3. **Check Docker Desktop settings** (Windows/macOS):
   - Ensure file sharing is enabled for your project directory
   - Check Docker Desktop resource settings

4. **Complete reset**:
   ```bash
   ./docker-fix.sh reset
   ```

### Getting More Information

```bash
# Show detailed container status
docker-compose ps

# Show volume information
docker volume inspect booking_booking_data

# Show detailed logs
docker-compose logs -f booking-app

# Check file permissions inside container
docker-compose exec booking-app ls -la /app/
```

## Platform-Specific Notes

### Linux
- User mapping usually works out of the box
- Use: `./docker-fix.sh user-fix`

### macOS
- Bind mounts often work better than named volumes
- Use: `./docker-fix.sh bind-fix`

### Windows
- May need to run as root due to permission mapping complexity
- Use: `./docker-fix.sh root-fix`
- Ensure Docker Desktop has file sharing enabled
