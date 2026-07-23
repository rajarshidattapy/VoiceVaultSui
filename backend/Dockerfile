# Use lightweight Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# LuxTTS dependencies need FFmpeg/audio libraries, and its tokenizer dependency
# is installed from a Git source.
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency manifests before the application for cacheable installs.
COPY requirements.txt .
COPY tts/requirements.txt ./tts/requirements.txt

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy all backend code
COPY . .

# Expose backend port
EXPOSE 8000

# Start FastAPI server
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
