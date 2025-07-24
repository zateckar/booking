# Use Python 3.13 slim image as base
FROM python:3.13-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_CACHE_DIR=/tmp/uv-cache

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install UV package manager
RUN pip install uv

# Create app user and group
RUN groupadd -r appuser && useradd -r -g appuser appuser

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

# Create directories for data persistence and fix UV cache permissions
RUN mkdir -p /app/data /app/logs && \
    mkdir -p /tmp/uv-cache && \
    chown -R appuser:appuser /app /tmp/uv-cache

# Create a non-root user for running the application
USER appuser

# Expose port
EXPOSE 8000

# Set environment variables for production
ENV PYTHONPATH=/app \
    DATABASE_URL=sqlite:///./data/booking.db

# Command to run the application
CMD ["uv", "run", "python", "run.py"]
