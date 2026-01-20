#!/bin/bash
# MyAIGist Local - One-Click Deployment Script
# Deploys production environment with Ollama, Whisper, and Piper

set -e  # Exit on error

echo "🚀 MyAIGist Local - One-Click Deployment"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check prerequisites
echo "📋 Checking prerequisites..."

if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker not found. Please install Docker Desktop.${NC}"
    echo "   Download from: https://www.docker.com/products/docker-desktop"
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo -e "${RED}❌ Docker Compose not found. Please install Docker Compose.${NC}"
    exit 1
fi

# Use 'docker compose' (v2) or 'docker-compose' (v1)
DOCKER_COMPOSE="docker compose"
if ! docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
fi

echo -e "${GREEN}✅ Docker and Docker Compose found${NC}"
echo ""

# Load or create environment
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  .env not found, creating from template...${NC}"
    cp .env.example .env
    echo -e "${GREEN}✅ Created .env file${NC}"
    echo -e "${YELLOW}📝 Please review .env settings if needed${NC}"
    echo ""
fi

# Create required directories
echo "📁 Creating required directories..."
mkdir -p data uploads static/audio
echo -e "${GREEN}✅ Directories created${NC}"
echo ""

# Pull Docker images
echo "📦 Pulling Docker images (this may take a few minutes)..."
$DOCKER_COMPOSE pull
echo -e "${GREEN}✅ Images pulled successfully${NC}"
echo ""

# Start Ollama service first
echo "🤖 Starting Ollama service..."
$DOCKER_COMPOSE up -d ollama
echo "⏳ Waiting for Ollama to be ready..."
sleep 10

# Check if Ollama is responding
if ! curl -f http://localhost:11434/ > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Ollama not responding yet, waiting longer...${NC}"
    sleep 10
fi

# Download Ollama models
echo ""
echo "📥 Downloading Ollama models (this will take 10-20 minutes)..."
echo "   Model: qwen2.5:14b (~9GB)"
echo "   Model: nomic-embed-text (~1GB)"
echo ""

docker exec myaigist-ollama ollama pull qwen2.5:14b
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ qwen2.5:14b downloaded successfully${NC}"
else
    echo -e "${RED}❌ Failed to download qwen2.5:14b${NC}"
    exit 1
fi

docker exec myaigist-ollama ollama pull nomic-embed-text
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ nomic-embed-text downloaded successfully${NC}"
else
    echo -e "${RED}❌ Failed to download nomic-embed-text${NC}"
    exit 1
fi

echo ""
echo "🚀 Starting all services..."
$DOCKER_COMPOSE up -d

# Wait for services to be ready
echo "⏳ Waiting for services to initialize..."
sleep 15

# Health checks
echo ""
echo "🏥 Running health checks..."

# Check app
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ App is healthy${NC}"
else
    echo -e "${YELLOW}⚠️  App health check failed, checking logs...${NC}"
    $DOCKER_COMPOSE logs --tail=20 app
fi

# Check Ollama
if curl -f http://localhost:11434/ > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Ollama is healthy${NC}"
else
    echo -e "${RED}❌ Ollama health check failed${NC}"
fi

# Check Whisper
if curl -f http://localhost:9000/ > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Whisper is healthy${NC}"
else
    echo -e "${YELLOW}⚠️  Whisper may still be initializing${NC}"
fi

echo ""
echo "=========================================="
echo -e "${GREEN}✅ MyAIGist Local is running!${NC}"
echo "=========================================="
echo ""
echo "🌐 Access your application at:"
echo "   http://localhost:8000"
echo ""
echo "📊 Service endpoints:"
echo "   App:     http://localhost:8000"
echo "   Ollama:  http://localhost:11434"
echo "   Whisper: http://localhost:9000"
echo "   Piper:   http://localhost:10200"
echo ""
echo "📝 Useful commands:"
echo "   View logs:    $DOCKER_COMPOSE logs -f app"
echo "   Stop:         $DOCKER_COMPOSE down"
echo "   Restart:      $DOCKER_COMPOSE restart"
echo "   Status:       $DOCKER_COMPOSE ps"
echo ""
echo "💡 Tip: Add '127.0.0.1  myaigist.local' to /etc/hosts"
echo "   Then access via: http://myaigist.local:8000"
echo ""
