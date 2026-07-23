# Use official Python runtime as base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    ffmpeg \
    git \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for better Docker caching)
COPY backend/requirements.txt .
COPY backend/tts/requirements.txt ./tts/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application
COPY backend/ .

# Expose port (Render uses 10000, but FastAPI will read PORT env var)
EXPOSE 8080

# Set environment variables
ENV PORT=8080
ENV PYTHONUNBUFFERED=1

# Create storage directory for local Walrus mode
RUN mkdir -p storage/walrus

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT}/docs || exit 1

# Run the application
CMD ["python", "server.py"]
