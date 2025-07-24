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

# Copy dependency files first (for better caching)
COPY pyproject.toml uv.lock* ./

# Install Python dependencies using UV
RUN uv sync --frozen --no-dev

# Copy application code
COPY . .

# Create directories for data persistence
RUN mkdir -p /app/data /app/logs && \
    chown -R appuser:appuser /app

# Create a non-root user for running the application
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/oidc/providers || exit 1

# Set environment variables for production
ENV PYTHONPATH=/app \
    DATABASE_URL=sqlite:///./data/booking.db

# Command to run the application
CMD ["uv", "run", "python", "run.py"]
