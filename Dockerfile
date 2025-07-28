# Use Python 3.13 slim image as base
FROM python:3.13-slim

# Set environment variables
ENV UV_CACHE_DIR=/tmp/uv-cache

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install UV package manager
RUN pip install uv

# Set work directory
WORKDIR /app

# Copy dependency files and source code needed for building
COPY pyproject.toml uv.lock* ./
COPY README.md ./
COPY src/ ./src/

# Install Python dependencies using UV
RUN uv sync --frozen --no-dev

# Copy remaining application code
COPY . .

# Copy and make entrypoint script executable
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Create directories for data persistence and fix UV cache permissions
RUN mkdir -p /tmp/uv-cache \
    && mkdir -p /app/data \
    && mkdir -p /app/logs \
    && mkdir -p /app/static/uploads \
    && mkdir -p /app/static/images/parking_lots

# Expose port
EXPOSE 8000

# Set environment variables for production
ENV PYTHONPATH=/app \
    DATABASE_URL=sqlite:///booking.db

# Use entrypoint script to handle permissions
ENTRYPOINT ["/app/entrypoint.sh"]

# Command to run the application
CMD ["uv", "run", "python", "run.py"]
