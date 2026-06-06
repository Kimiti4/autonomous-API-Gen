# 🧬 EvoAPI: Autonomous Architecture Engine

> **Production-grade API architecture discovery using genetic algorithms and LLM-guided evolution**

[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)](https://reactjs.org)
[![Ollama](https://img.shields.io/badge/Ollama-LLM-ff6b00?style=for-the-badge)](https://ollama.com)
[![License](https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge)](LICENSE)

---

## 🚀 Quick Start (One Command!)

### Windows
```bash
# Double-click this file or run in terminal:
START_ALL.bat

# Or use PowerShell (recommended):
.\START_ALL.ps1
```

### Linux/Mac
```bash
chmod +x start_all.sh
./start_all.sh
```

**That's it!** All services will start automatically. Open http://localhost:3001 to begin.

📖 **Full Guide:** [QUICK_START.md](QUICK_START.md)

---

## ✨ Features

### 🧬 Core Evolution Engine
- **Genetic Algorithms**: Multi-objective optimization across 20+ dimensions
- **Real Genome Encoding**: Actual FastAPI code generation from evolved genomes
- **Multi-Population System**: 4 specialized groups with cross-pollination
- **Adaptive Learning**: Mutation probabilities adjust based on success patterns
- **Persistent Memory**: Learns across runs for continuous improvement

### ⭐ Game-Changing: LLM-Guided Mutation
- **AI-Enhanced Search**: Combines genetic exploration with expert reasoning
- **3x Faster Convergence**: Reaches optimal solutions quicker
- **Explainable Suggestions**: Understands why mutations are recommended
- **Context-Aware**: Optimizes for security vs performance trade-offs

### 🛡️ Production Hardening
- Input validation with Pydantic
- Rate limiting middleware
- Comprehensive error handling
- Security headers & CORS
- Prometheus metrics integration
- Docker container testing

### 📊 Monitoring & Observability
- Real-time WebSocket updates
- Fitness progression charts
- Multi-population visualization
- System health monitoring
- Performance metrics dashboard

---

## 🏗️ Architecture

```
┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│   Frontend   │ ◄─────► │   Backend    │ ◄─────► │   Ollama     │
│  (React UI)  │  HTTP   │  (FastAPI)   │  HTTP   │  (LLM)       │
│  Port 3001   │  /WS    │  Port 8000   │         │  Port 11434  │
└──────────────┘         └──────┬───────┘         └──────────────┘
                                │
                         ┌──────▼───────┐
                         │   SQLite     │
                         │  Database    │
                         └──────────────┘
```

---

## 📁 Project Structure

```
EvoAPI/
├── START_ALL.bat              # Windows batch startup script
├── START_ALL.ps1              # PowerShell startup script
├── start_all.sh               # Linux/Mac startup script
├── QUICK_START.md             # One-command startup guide
├── STARTUP_FLOW.md            # System architecture diagrams
│
├── autonomous-api/            # Backend (FastAPI)
│   ├── app/
│   │   ├── api/              # REST endpoints
│   │   ├── core/             # Configuration, logging
│   │   ├── engine/           # Evolution engine
│   │   │   ├── evolution.py  # Main GA implementation
│   │   │   ├── elite_evolution.py  # Advanced features
│   │   │   └── llm_guided_mutation.py  # ⭐ AI enhancement
│   │   ├── middleware/       # Security, rate limiting
│   │   ├── models/           # Database schemas
│   │   └── storage/          # Database layer
│   ├── tests/                # Unit tests
│   └── pyproject.toml        # Dependencies
│
└── reasoning-ui/             # Frontend (React)
    ├── src/
    │   ├── EvolutionDashboardEnhanced.js  # Modern UI
    │   └── App.js
    └── package.json
```

---

## 🎯 What Makes This Special?

### Not Just Code Generation
This is **automated architectural discovery** through evolutionary search:

| Senior Developer | Evolution Engine |
|------------------|------------------|
| Tests 5-10 variants | Tests 500,000+ combinations |
| Local optima focus | Global optima discovery |
| Experience-based | Data-driven learning |
| Hours per design | Minutes per evolution |
| Single perspective | Multi-objective optimization |

### Academic Foundation
Based on proven genetic algorithm research:
- Holland, J.H. (1975). *Adaptation in Natural and Artificial Systems*
- Deb, K. (2001). *Multi-Objective Optimization using Evolutionary Algorithms*
- Enhanced with modern LLM guidance (novel contribution)

---

## 📖 Documentation

### Getting Started
- [QUICK_START.md](QUICK_START.md) - One-command startup guide
- [STARTUP_FLOW.md](STARTUP_FLOW.md) - System architecture & flows

### Technical Docs
- [autonomous-api/README_COMPLETE.md](autonomous-api/README_COMPLETE.md) - Complete system overview
- [autonomous-api/COMPLETE_TECHNICAL_DOCS.md](autonomous-api/COMPLETE_TECHNICAL_DOCS.md) - Technical reference
- [autonomous-api/WHY_THIS_IS_SPECIAL.md](autonomous-api/WHY_THIS_IS_SPECIAL.md) - Innovation explanation
- [autonomous-api/BACKEND_OPTIMIZATIONS.md](autonomous-api/BACKEND_OPTIMIZATIONS.md) - Performance improvements

### Deployment
- [autonomous-api/docker-compose.yml](autonomous-api/docker-compose.yml) - Container orchestration
- [autonomous-api/.github/workflows/ci-cd.yml](autonomous-api/.github/workflows/ci-cd.yml) - CI/CD pipeline

---

## 🔧 Prerequisites

Before running, ensure you have:

1. **Python 3.10+** ([Download](https://python.org))
2. **Node.js 16+** ([Download](https://nodejs.org))
3. **Ollama** ([Download](https://ollama.com))
4. **Git** (optional, for version control)

### Install Dependencies

```bash
# Backend
cd autonomous-api
pip install -r requirements.txt

# Frontend
cd reasoning-ui
npm install
```

---

## 🌐 Access Points

Once started, access your services:

| Service | URL | Description |
|---------|-----|-------------|
| **Frontend UI** | http://localhost:3001 | Main application |
| **Backend API** | http://localhost:8000 | REST API |
| **API Docs** | http://localhost:8000/docs | Swagger UI |
| **Health Check** | http://localhost:8000/health | System status |
| **WebSocket** | ws://localhost:8000/ws/evolution | Real-time updates |
| **Metrics** | http://localhost:8000/metrics | Prometheus metrics |

---

## 💡 Usage Examples

### Start Evolution via UI
1. Open http://localhost:3001
2. Configure parameters (generations, population size)
3. Enable Elite Mode for advanced features
4. Click "Start Evolution"
5. Watch real-time progress!

### Start Evolution via API
```bash
curl -X POST http://localhost:8000/evolve/start \
  -H "Content-Type: application/json" \
  -d '{
    "generations": 20,
    "population_size": 15,
    "use_docker": true
  }'
```

### Connect to WebSocket
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/evolution');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Evolution update:', data);
};
```

---

## 🧪 Testing

```bash
# Run unit tests
cd autonomous-api
pytest tests/ -v

# Run performance tests
python test_performance.py

# Load testing
locust -f load_test.py
```

---

## 🐳 Docker Deployment

```bash
# Start all services with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

---

## 📊 Performance Benchmarks

| Metric | Value |
|--------|-------|
| Server Startup Time | ~1-2 seconds |
| Evolution Run (10 gen, pop 10) | ~30 seconds |
| API Response Time (avg) | <100ms |
| Memory Usage (idle) | ~200MB |
| Concurrent Connections | 100+ |

See [BACKEND_OPTIMIZATIONS.md](autonomous-api/BACKEND_OPTIMIZATIONS.md) for details.

---

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **Genetic Algorithms**: Inspired by John Holland's pioneering work
- **FastAPI**: Amazing Python web framework by Sebastián Ramírez
- **React**: Powerful UI library by Facebook
- **Ollama**: Easy-to-use local LLM runner
- **Community**: Open-source contributors worldwide

---

## 📞 Support

- 📧 Email: karamos473@gmail.com
- 🐛 Issues: [GitHub Issues](https://github.com/Kimiti4/EvoAPI/issues)
- 💬 Discussions: [GitHub Discussions](https://github.com/Kimiti4/EvoAPI/discussions)

---

## 🌟 Star History

If you find this project useful, please consider giving it a star! ⭐

---

<div align="center">

**Made with ❤️ by Kimiti4**

[Website](https://github.com/Kimiti4) • [Twitter](https://twitter.com/Kimiti4) • [LinkedIn](https://linkedin.com/in/kimiti4)

</div>
