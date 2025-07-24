# Docker Database Connection Fix

## Problem
When starting the booking application in a Docker container, you may encounter this error:
```
sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) unable to open database file
```

## Root Cause
This error occurs due to two main issues:

1. **Premature Database Initialization**: Database tables were being created immediately when the module was imported, before proper database setup.
2. **Docker Volume Permission Issues**: Docker volume mounting can override directory permissions, preventing the application from writing to the database file.

## Fixes Applied

### 1. Fixed Database Initialization Order
- Removed premature `models.Base.metadata.create_all(bind=engine)` from `src/booking/__init__.py`
- Database tables are now created only through the proper `create_db_and_tables()` function in `run.py`

### 2. Added Entrypoint Script
- Created `entrypoint.sh` to check directory permissions at runtime
- Provides helpful error messages and diagnostics for permission issues
- Automatically creates required directories

### 3. Updated Dockerfile
- Added entrypoint script to handle runtime permission checks
- Improved directory setup and permissions

## Usage

### Standard Usage
The container should now start normally with:
```bash
docker-compose up
```

The main `docker-compose.yml` now includes user mapping (`1000:1000`) by default to prevent permission issues.

### Customizing User Mapping
If you need to run with different user permissions, set the `DOCKER_USER` environment variable:

```bash
# Use your actual UID:GID (find with 'id' command)
DOCKER_USER="$(id -u):$(id -g)" docker-compose up

# Or export it for persistent use
export DOCKER_USER="$(id -u):$(id -g)"
docker-compose up
```

### Alternative Solutions (if needed)
Additional solutions are available in `docker-compose.override.yml`:

#### Option 1: Run as Root (Quick Fix)
Uncomment in `docker-compose.override.yml`:
```yaml
user: "0:0"
```

#### Option 2: Use Bind Mounts (Development)
Uncomment in `docker-compose.override.yml`:
```yaml
volumes:
  - ./data:/app/data
  - ./logs:/app/logs
```

### Manual Volume Permission Fix
If using named volumes, you can fix permissions manually:
```bash
# Stop the container
docker-compose down

# Remove the problematic volume
docker volume rm booking_booking_data

# Restart (volume will be recreated)
docker-compose up
```

## Testing the Fix

1. Stop any running containers:
   ```bash
   docker-compose down
   ```

2. Rebuild the image:
   ```bash
   docker-compose build
   ```

3. Start the container:
   ```bash
   docker-compose up
   ```

4. Check the logs for successful database initialization:
   ```bash
   docker-compose logs booking-app
   ```

You should see messages like:
- "Write permission check passed."
- "✅ Database schema is compatible"
- "✅ Initial admin user created successfully"

## Troubleshooting

If the issue persists:

1. Check container logs: `docker-compose logs booking-app`
2. Verify volume permissions: `docker volume inspect booking_booking_data`
3. Try one of the permission solutions in `docker-compose.override.yml`
4. For development, consider using bind mounts instead of named volumes
