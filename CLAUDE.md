# MyAIGist Local - Development Workflow

Complete guide for developing, testing, and deploying MyAIGist Local.

## Overview

This document describes the full development cycle from code changes to production deployment, including QA testing, code quality checks, and GitHub synchronization.

## Development Cycle

```
Code Change → Code Simplifier → QA Deploy → Automated Tests → Manual Tests → Production → GitHub
```

## Step 1: Make Code Changes

Edit files locally using your preferred editor:

### Core Application
- `main.py` - Flask app, API endpoints
- `agents/*.py` - AI service modules

### Configuration
- `docker-compose.yml` - Production services
- `docker-compose.qa.yml` - QA environment
- `.env` - Environment configuration

### Frontend
- `static/js/app.js` - JavaScript application
- `static/css/styles.css` - Styling
- `templates/*.html` - HTML templates

### Local Development Server

For quick testing without Docker:

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export OLLAMA_HOST=http://localhost:11434
export WHISPER_HOST=http://localhost:9000
export PIPER_HOST=http://localhost:10200

# Run dev server
python main.py
```

**Note**: Ollama, Whisper, and Piper services must be running (via Docker or locally).

## Step 2: Run Code Simplifier Agent

The code-simplifier agent analyzes code quality and suggests improvements.

### When to Run

- Before committing major features
- After adding new dependencies
- Before version releases
- When Docker image size grows >800MB

### How to Run

Using Claude Code CLI:

```bash
# Analyze code quality
claude analyze --agents code-simplifier

# Review the generated report
cat simplifier_report.md
```

### What It Checks

1. **Code Complexity**
   - Cyclomatic complexity score
   - Long functions (>50 lines)
   - Deep nesting (>4 levels)

2. **Unused Code**
   - Unused imports
   - Dead functions
   - Unreferenced variables

3. **Docker Optimization**
   - Image layer efficiency
   - Unnecessary dependencies
   - Multi-stage build opportunities

4. **Security**
   - Hardcoded secrets
   - Unsafe dependencies
   - Insecure configurations

5. **Best Practices**
   - Error handling patterns
   - Logging consistency
   - Type hints coverage

### Example Report

```markdown
# Code Simplifier Report

## Summary
- Complexity Score: 7.2/10 (Good)
- Unused Functions: 3 found
- Docker Image Size: 1.2GB (Target: <800MB)

## Recommendations

### High Priority
1. Remove `agents/old_qa_agent.py` (unused)
2. Combine duplicate Ollama client initialization

### Medium Priority
3. Simplify error handling in main.py:245-312
4. Add type hints to qa_agent.py

### Docker Optimization
5. Multi-stage build can reduce size by 400MB
6. Remove dev dependencies from production image

## Auto-Fix Available
Run: `claude apply-fixes simplifier_report.md`
```

### Apply Fixes

Review suggestions and apply manually or use auto-fix:

```bash
# Apply automated fixes
claude apply-fixes simplifier_report.md

# Review changes
git diff

# Commit if satisfied
git add .
git commit -m "refactor: Apply code simplifier suggestions"
```

## Step 3: Deploy to QA Container

QA environment runs on port 8001 with faster models for quick iteration.

```bash
./deploy-qa.sh
```

**QA Environment Differences:**
- Port: 8001 (vs 8000 production)
- Model: qwen2.5:14b (same as production)
- Data: Separate `data_qa/` directory
- Faster startup for testing

### QA Service Endpoints

| Service | URL |
|---------|-----|
| App | http://localhost:8001 |
| Ollama | http://localhost:11435 |
| Whisper | http://localhost:9001 |
| Piper | http://localhost:10201 |

## Step 4: Run Automated Tests

Execute the test suite against QA environment:

```bash
./test.sh
```

### Test Categories

#### 1. Health Checks
- App responds on port 8001
- Ollama API accessible
- Whisper service running
- Piper service available

#### 2. Integration Tests
- Document upload workflow
- Summarization pipeline
- Q&A RAG system
- Audio transcription
- TTS generation

#### 3. API Endpoint Tests
- `/health` - Health check
- `/api/process-content` - Single upload
- `/api/upload-multiple-files` - Batch upload
- `/api/ask-question` - Q&A
- `/api/transcribe-audio` - Whisper
- `/api/generate-audio` - Piper TTS

### Test Output

```
🧪 MyAIGist Local - Test Suite
===============================

🏥 Health Checks
================
✅ App health check passed
✅ Ollama health check passed
✅ Whisper health check passed

🧪 Running Integration Tests
============================
Test 1: Homepage loads... ✅ PASS
Test 2: Health endpoint... ✅ PASS
Test 3: Ollama API... ✅ PASS

📊 Test Summary
===============
All tests passed (3/3)
```

### Manual Pytest (Optional)

For more comprehensive testing:

```bash
# Install test dependencies
pip install pytest pytest-cov

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=agents --cov=main

# Run specific test file
pytest tests/test_ollama.py
```

## Step 5: Manual Functional Testing

Open [http://localhost:8001](http://localhost:8001) and verify:

### Test Checklist

#### Document Processing
- [ ] Upload PDF - generates summary
- [ ] Upload DOCX - extracts text correctly
- [ ] Upload TXT - processes without errors
- [ ] Enter raw text - summarizes directly
- [ ] Process URL - crawls and extracts content

#### Summarization
- [ ] Quick summary - 2-3 points, fast
- [ ] Standard summary - balanced detail
- [ ] Detailed summary - comprehensive analysis
- [ ] Long document (>5000 words) - handles correctly

#### Q&A System
- [ ] Upload document - adds to knowledge base
- [ ] Ask factual question - accurate answer
- [ ] Ask inferential question - reasonable response
- [ ] Multiple documents - searches across all
- [ ] No documents - appropriate error message

#### Audio Features
- [ ] Upload MP3 - transcribes correctly
- [ ] Upload video (MP4) - extracts audio, transcribes
- [ ] Record audio - voice input works
- [ ] Generate TTS - plays audio correctly
- [ ] Multiple voices - Piper voice selection

#### Batch Processing
- [ ] Upload 3 PDFs - processes all
- [ ] Mixed content (PDF + URL + text) - unified summary
- [ ] 5+ items - handles max batch size

#### UI/UX
- [ ] File shelf shows documents
- [ ] Delete document - removes from UI
- [ ] Clear all documents - resets knowledge base
- [ ] Error messages - user-friendly
- [ ] Loading indicators - show progress

### Performance Checks

- Summary generation: <10s
- Q&A response: <5s
- Audio transcription: Realtime to 2x
- TTS generation: <3s
- Page load: <1s

## Step 6: After Tests Pass

### A. Update Version

```bash
# Increment version
echo "1.0.1" > VERSION

# Tag in Git
git tag -a v1.0.1 -m "Release 1.0.1: Bug fixes and improvements"
```

### B. Build Production Image

```bash
VERSION=$(cat VERSION)
docker build -t myaigist-local:latest \
             -t myaigist-local:${VERSION} .
```

### C. Deploy to Production

```bash
# Deploy production environment
./deploy.sh

# Verify production
curl http://localhost:8000/health
```

### D. Push to GitHub

```bash
# Stage changes
git add .

# Commit with conventional commits format
git commit -m "feat: Add feature X

- Implemented Y
- Fixed Z
- Updated tests

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"

# Push to main
git push origin main

# Push version tag
git push origin v1.0.1
```

### E. Sync Docker Image (Optional)

Push to GitHub Container Registry:

```bash
# Login to GitHub Container Registry
echo $GITHUB_PAT | docker login ghcr.io -u USERNAME --password-stdin

# Tag for registry
docker tag myaigist-local:${VERSION} ghcr.io/schwim23/myaigist-local:${VERSION}
docker tag myaigist-local:latest ghcr.io/schwim23/myaigist-local:latest

# Push images
docker push ghcr.io/schwim23/myaigist-local:${VERSION}
docker push ghcr.io/schwim23/myaigist-local:latest
```

## Git Workflow

### Branch Strategy

- `main` - Production-ready code
- `dev` - Active development (optional)
- `feature/*` - Feature branches

### Commit Message Format

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>: <description>

[optional body]

[optional footer]
```

**Types:**
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `refactor:` - Code refactoring
- `test:` - Adding tests
- `chore:` - Maintenance

**Examples:**
```bash
feat: Add multi-language support for summaries
fix: Resolve transcription timeout for large files
docs: Update README with deployment instructions
refactor: Simplify qa_agent.py error handling
test: Add integration tests for batch processing
chore: Bump Docker base image to Python 3.11
```

## Troubleshooting Development

### QA Environment Issues

```bash
# View QA logs
docker-compose -f docker-compose.qa.yml logs -f

# Restart QA services
docker-compose -f docker-compose.qa.yml restart

# Clean QA data
rm -rf data_qa/ uploads_qa/
./deploy-qa.sh
```

### Docker Build Fails

```bash
# Clear Docker cache
docker builder prune

# Rebuild without cache
docker build --no-cache -t myaigist-local:latest .
```

### Model Not Found

```bash
# Pull model manually
docker exec myaigist-ollama-qa ollama pull qwen2.5:14b

# List available models
docker exec myaigist-ollama-qa ollama list
```

### Tests Fail

```bash
# Run tests in verbose mode
./test.sh --verbose

# Check specific service
curl -v http://localhost:8001/health
docker-compose -f docker-compose.qa.yml logs app
```

## CI/CD (Future)

GitHub Actions workflow for automated testing and deployment:

```yaml
# .github/workflows/test.yml
name: Test Suite

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Deploy QA
        run: ./deploy-qa.sh
      - name: Run Tests
        run: ./test.sh
```

## Code Review Checklist

Before submitting PR or deploying:

- [ ] Code simplifier ran, issues addressed
- [ ] All automated tests pass
- [ ] Manual testing completed
- [ ] No hardcoded secrets or API keys
- [ ] Error handling is comprehensive
- [ ] Logging is consistent
- [ ] Documentation updated (README, comments)
- [ ] Docker image size <800MB
- [ ] No unused dependencies in requirements.txt

## Performance Optimization

### Monitoring

```bash
# Check Docker resource usage
docker stats

# App memory usage
docker exec myaigist-app ps aux

# Ollama model memory
docker exec myaigist-ollama ollama ps
```

### Optimization Tips

1. **Model Selection**: Balance quality vs speed
2. **Caching**: Consider adding Redis for embeddings
3. **Async Processing**: Use Celery for long tasks
4. **Vector Store**: Migrate to Chroma or Weaviate for scale
5. **Frontend**: Implement progressive loading

## Security Best Practices

- Never commit `.env` files
- Use environment variables for all configuration
- Review dependencies regularly (`pip-audit`)
- Keep Docker images updated
- Limit container permissions
- Enable Docker content trust

---

## Quick Reference

```bash
# Development
python main.py                          # Dev server
./deploy-qa.sh                          # QA environment
./test.sh                               # Run tests

# Production
./deploy.sh                             # Production deploy
docker-compose logs -f app              # View logs
docker-compose restart app              # Restart app

# Docker
docker-compose ps                       # Status
docker-compose down                     # Stop all
docker system prune -a                  # Clean up

# Version Management
echo "1.0.1" > VERSION                  # Update version
git tag -a v1.0.1 -m "Release 1.0.1"   # Create tag
git push origin v1.0.1                  # Push tag
```

---

**For questions or issues, see the [main README](README.md) or open an issue on GitHub.**
