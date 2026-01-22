# MyAIGist Local

**Fully local AI-powered content analysis and Q&A platform** - No cloud APIs required!

MyAIGist Local runs entirely on your machine using free, open-source AI models via Ollama, Whisper.cpp, and Piper. Process documents, analyze content, and ask questions - all while keeping your data completely private.

## Features

- **Document Processing**: PDF, DOCX, and TXT files
- **AI Summarization**: 3 detail levels (Quick, Standard, Detailed)
- **RAG Q&A**: Question-answering using your uploaded documents
- **Batch Processing**: Handle multiple files at once
- **100% Local**: No data sent to cloud services
- **Privacy-First**: All processing happens on your machine

## Quick Start

### Prerequisites

- **Docker Desktop**: [Download here](https://www.docker.com/products/docker-desktop)
- **16GB+ RAM** recommended (works with 8GB using smaller models)
- **20GB free disk space** for models and data
- **macOS, Linux, or Windows** with WSL2

### One-Click Deployment

```bash
# Clone the repository
git clone https://github.com/schwim23/myaigist_local.git
cd myaigist_local

# Deploy (downloads models and starts all services)
./deploy.sh
```

That's it! The script will:
1. Check prerequisites
2. Pull Docker images
3. Download AI models (~10GB)
4. Start all services
5. Run health checks

**Access your app at**: [http://localhost:8000](http://localhost:8000)

## What's Running

MyAIGist Local consists of 4 Docker containers:

| Service | Purpose | Port | Model |
|---------|---------|------|-------|
| **App** | Flask web application | 8000 | - |
| **Ollama** | LLM & embeddings | 11434 | tinyllama, nomic-embed-text |

## Usage

### Processing Content

1. **Upload Documents**: Drag & drop PDF, DOCX, or TXT files
2. **Enter Text**: Paste text directly for analysis

### Summarization Levels

- **Quick**: 2-3 key points (fast)
- **Standard**: Balanced summary with main topics
- **Detailed**: Comprehensive analysis with context

### Q&A System

After uploading documents, ask questions like:
- "What are the main findings?"
- "Summarize the conclusions"
- "What does it say about [topic]?"

The system uses RAG (Retrieval-Augmented Generation) to provide accurate answers based on your documents.

## Configuration

### Environment Variables

Edit `.env` to customize:

```bash
# Model Selection
OLLAMA_MODEL=qwen2.5:14b          # Or llama3.3:70b for better quality
OLLAMA_EMBED_MODEL=nomic-embed-text

# Service Endpoints (defaults work in Docker)
OLLAMA_HOST=http://ollama:11434
WHISPER_HOST=http://whisper:9000
PIPER_HOST=http://piper:10200

# Application
MAX_CONTENT_LENGTH=52428800       # 50MB upload limit
```

### Model Tiers

**Balanced (Default - 16GB RAM)**
```bash
OLLAMA_MODEL=qwen2.5:14b
```
- Fast and accurate
- 16GB RAM required
- ~8s for summaries

**High Performance (32GB+ RAM)**
```bash
OLLAMA_MODEL=llama3.3:70b
```
- Excellent quality
- 48GB RAM required
- ~5s for summaries

**Budget (8GB RAM)**
```bash
OLLAMA_MODEL=llama3.2:3b
```
- Fast testing
- 8GB RAM sufficient
- ~2s for summaries

To switch models:
```bash
docker exec myaigist-ollama ollama pull llama3.3:70b
# Update .env with new model name
docker-compose restart app
```

## Management Commands

### Start/Stop

```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# Restart a service
docker-compose restart app

# View logs
docker-compose logs -f app
```

### Status & Health

```bash
# Check running containers
docker-compose ps

# App health
curl http://localhost:8000/health

# Ollama models
docker exec myaigist-ollama ollama list
```

### Data Management

```bash
# Backup your data
cp -r data/ data_backup/

# Clear vector store (reset Q&A knowledge)
rm data/vector_store.pkl

# View disk usage
docker system df
```

## Troubleshooting

### Services Won't Start

```bash
# Check Docker is running
docker ps

# View detailed logs
docker-compose logs

# Restart everything
docker-compose down
docker-compose up -d
```

### Model Download Fails

```bash
# Manual download
docker exec -it myaigist-ollama ollama pull qwen2.5:14b

# Check available space
df -h
```

### Out of Memory

If you see OOM errors:
1. Switch to smaller model (see Configuration)
2. Reduce Docker memory limit
3. Close other applications

### Slow Performance

- Use SSD for Docker storage
- Increase Docker memory allocation
- Switch to smaller model for faster responses
- Close resource-heavy applications

## Development

See [CLAUDE.md](CLAUDE.md) for complete development workflow including:
- QA environment setup
- Code simplifier agent usage
- Testing procedures
- Git workflow
- Docker image versioning

### QA Environment

```bash
# Deploy QA (port 8001)
./deploy-qa.sh

# Run automated tests
./test.sh
```

## Architecture

```
┌─────────────────────────────────────────┐
│           Browser (localhost:8000)       │
└────────────────┬────────────────────────┘
                 │
┌────────────────▼────────────────────────┐
│       Flask App (myaigist-app)          │
│   - Document processing                 │
│   - API endpoints                       │
│   - Vector store management             │
└─┬──────────┬──────────┬─────────────────┘
  │          │          │
  │ Ollama   │ Whisper  │ Piper
  │ (LLM)    │ (ASR)    │ (TTS)
  │          │          │
┌─▼──────┐ ┌─▼──────┐ ┌─▼──────┐
│Ollama  │ │Whisper │ │Piper   │
│Service │ │Service │ │Service │
│:11434  │ │:9000   │ │:10200  │
└────────┘ └────────┘ └────────┘
```

## Tech Stack

- **Backend**: Flask, Python 3.11
- **Frontend**: Vanilla JavaScript
- **LLM**: Ollama (qwen2.5:14b)
- **Embeddings**: nomic-embed-text (768 dims)
- **Transcription**: Whisper.cpp (medium model)
- **TTS**: Piper (lessac voice)
- **Vector Store**: NumPy + pickle
- **Deployment**: Docker Compose

## Privacy & Security

- **100% Local**: All processing on your machine
- **No Telemetry**: No analytics or tracking
- **No API Keys**: No cloud service credentials needed
- **Data Ownership**: Your documents never leave your computer

## Performance

Typical response times on MacBook Pro (16GB RAM):
- Document upload: <1s
- Summarization: 5-10s
- Q&A answer: 3-5s
- Audio transcription: Real-time to 2x speed
- TTS generation: <2s

## Known Limitations

- **Single User**: Designed for personal use, not multi-user
- **Local Resources**: Performance depends on your hardware
- **Model Size**: Quality vs speed tradeoffs
- **No GPU Acceleration**: Uses CPU (M-series Macs are fast)

## Roadmap

- [ ] Multi-language support
- [ ] Advanced vector search (hybrid search, reranking)
- [ ] Model caching for faster responses
- [ ] Docker image publishing to GitHub Container Registry
- [ ] One-click installer for non-technical users

## Contributing

This is a personal project, but suggestions and bug reports are welcome!

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

MIT License - see [LICENSE](LICENSE) file

## Acknowledgments

- **Ollama** - Local LLM runtime
- **Whisper.cpp** - Fast speech recognition
- **Piper** - Neural text-to-speech
- **Original MyAIGist** - Cloud version with OpenAI integration

## Links

- **GitHub**: https://github.com/schwim23/myaigist_local
- **Cloud Version**: https://github.com/schwim23/myaigist
- **MCP Server**: https://github.com/schwim23/myaigist_mcp
- **Issues**: https://github.com/schwim23/myaigist_local/issues

---

**Made with ❤️ for privacy-conscious AI enthusiasts**
