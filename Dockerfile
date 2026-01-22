# MyAIGist Local - Fully local deployment with Ollama
# Use Python 3.11 slim image for smaller size
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (ffmpeg for audio/video processing)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create necessary directories
RUN mkdir -p uploads static/audio data

# Set environment variables
ENV FLASK_APP=main.py
ENV FLASK_ENV=production

# Expose the port the app runs on
EXPOSE 8000

# Use gunicorn for production deployment with extended timeout for slow hardware
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "1", "--timeout", "600", "--graceful-timeout", "600", "main:app"]
