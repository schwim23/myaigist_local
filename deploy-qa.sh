#!/bin/bash
# MyAIGist Local - QA Environment Deployment Script
# Deploys QA environment for testing with faster, smaller models

set -e  # Exit on error

echo "🧪 MyAIGist Local - QA Deployment"
echo "=================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker not found${NC}"
    exit 1
fi

# Use 'docker compose' (v2) or 'docker-compose' (v1)
DOCKER_COMPOSE="docker compose"
if ! docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
fi

echo -e "${GREEN}✅ Docker found${NC}"
echo ""

# Create QA directories
echo "📁 Creating QA directories..."
mkdir -p data_qa uploads_qa static/audio
echo -e "${GREEN}✅ QA directories created${NC}"
echo ""

# Pull images
echo "📦 Pulling Docker images..."
$DOCKER_COMPOSE -f docker-compose.qa.yml pull
echo -e "${GREEN}✅ Images pulled${NC}"
echo ""

# Start Ollama QA
echo "🤖 Starting Ollama QA service..."
$DOCKER_COMPOSE -f docker-compose.qa.yml up -d ollama
sleep 10

# Download smaller model for QA
echo "📥 Downloading QA model (qwen2.5:14b)..."
docker exec myaigist-ollama-qa ollama pull qwen2.5:14b
docker exec myaigist-ollama-qa ollama pull nomic-embed-text
echo -e "${GREEN}✅ Models downloaded${NC}"
echo ""

# Start all QA services
echo "🚀 Starting all QA services..."
$DOCKER_COMPOSE -f docker-compose.qa.yml up -d

echo "⏳ Waiting for services..."
sleep 15

# Health check
if curl -f http://localhost:8001/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ QA environment is healthy${NC}"
else
    echo -e "${YELLOW}⚠️  QA health check failed${NC}"
fi

echo ""
echo "=================================="
echo -e "${GREEN}✅ QA Environment Running!${NC}"
echo "=================================="
echo ""
echo "🌐 QA Application: http://localhost:8001"
echo ""
echo "📝 Commands:"
echo "   Logs:  $DOCKER_COMPOSE -f docker-compose.qa.yml logs -f"
echo "   Stop:  $DOCKER_COMPOSE -f docker-compose.qa.yml down"
echo ""
