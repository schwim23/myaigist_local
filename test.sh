#!/bin/bash
# MyAIGist Local - Automated Test Suite
# Runs automated tests against QA environment

set -e  # Exit on error

echo "🧪 MyAIGist Local - Test Suite"
echo "==============================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Use 'docker compose' (v2) or 'docker-compose' (v1)
DOCKER_COMPOSE="docker compose"
if ! docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
fi

# Start QA environment
echo "🚀 Starting QA environment..."
./deploy-qa.sh

echo ""
echo "⏳ Waiting for services to stabilize..."
sleep 10

# Run health checks
echo ""
echo "🏥 Health Checks"
echo "================"

# Check app
if curl -f http://localhost:8001/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ App health check passed${NC}"
else
    echo -e "${RED}❌ App health check failed${NC}"
    exit 1
fi

# Check Ollama
if curl -f http://localhost:11435/ > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Ollama health check passed${NC}"
else
    echo -e "${RED}❌ Ollama health check failed${NC}"
fi

# Check Whisper
if curl -f http://localhost:9001/ > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Whisper health check passed${NC}"
else
    echo -e "${YELLOW}⚠️  Whisper may be initializing${NC}"
fi

echo ""
echo "🧪 Running Integration Tests"
echo "============================"

# Test 1: Homepage loads
echo -n "Test 1: Homepage loads... "
if curl -s http://localhost:8001/ | grep -q "MyAIGist"; then
    echo -e "${GREEN}✅ PASS${NC}"
else
    echo -e "${RED}❌ FAIL${NC}"
fi

# Test 2: API endpoints respond
echo -n "Test 2: Health endpoint... "
HEALTH=$(curl -s http://localhost:8001/health)
if echo $HEALTH | grep -q "healthy\|ok"; then
    echo -e "${GREEN}✅ PASS${NC}"
else
    echo -e "${YELLOW}⚠️  Response: $HEALTH${NC}"
fi

# Test 3: Ollama API
echo -n "Test 3: Ollama API... "
if curl -s http://localhost:11435/api/tags | grep -q "models"; then
    echo -e "${GREEN}✅ PASS${NC}"
else
    echo -e "${RED}❌ FAIL${NC}"
fi

echo ""
echo "📊 Test Summary"
echo "==============="
echo "Basic health checks completed"
echo ""
echo -e "${YELLOW}💡 For manual testing, visit: http://localhost:8001${NC}"
echo ""
echo "🧹 Cleanup"
echo "=========="
read -p "Stop QA environment? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Stopping QA services..."
    $DOCKER_COMPOSE -f docker-compose.qa.yml down
    echo -e "${GREEN}✅ QA environment stopped${NC}"
fi

echo ""
echo "================================="
echo -e "${GREEN}✅ Test Suite Complete${NC}"
echo "================================="
