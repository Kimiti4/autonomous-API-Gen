# 🧬 Autonomous Evolution Engine v3

## Production-Grade Genetic API Architecture Generator

A sophisticated autonomous system that uses genetic algorithms to evolve optimal microservice API architectures. Features real-time evolution tracking, security-aware fitness evaluation, Docker containerization, and live WebSocket streaming dashboard.

---

## 🚀 Features

### Core Capabilities
- **🧬 Genetic Algorithm Engine**: Evolves API architectures through selection, crossover, and mutation
- **🔐 Security-Aware Fitness**: Penalizes insecure configurations (weak auth, missing rate limiting)
- **🏗️ Microservice Builder**: Generates complete FastAPI applications with multiple services
- **🐳 Docker Integration**: Automatically builds and tests generated APIs in containers
- **📊 Real-Time Dashboard**: Live WebSocket streaming of evolution progress
- **💾 Persistent Storage**: SQLite database tracks all evolution runs and genomes
- **⚡ Async Background Workers**: Non-blocking evolution with live updates

### Genome DNA
Each genome encodes architectural decisions:
- **Services**: Auth, Users, Payments, Analytics, Notifications, Search, Files, Admin
- **Authentication**: JWT, OAuth2, API Key, Basic
- **Database**: PostgreSQL, MySQL, SQLite
- **Features**: Caching, Rate Limiting, CORS
- **Configuration**: Logging levels, API versions

### Fitness Evaluation
Multi-objective scoring (0.0 - 1.0):
- **Security (30%)**: Auth strength, critical service protection
- **Architecture (25%)**: Service composition complexity
- **Performance (20%)**: Caching enabled
- **Best Practices (15%)**: Rate limiting, CORS, logging
- **Database (10%)**: Production-ready database choice

---

## 📁 Project Structure

```
autonomous-api/
├── app/
│   ├── api/
│   │   ├── routes.py          # REST API endpoints
│   │   └── ws.py              # WebSocket server
│   ├── engine/
│   │   ├── genome.py          # Genome encoding
│   │   ├── evolution.py       # Main evolution engine
│   │   ├── fitness.py         # Fitness evaluation
│   │   ├── security.py        # Security scoring
│   │   ├── builder.py         # Code generation
│   │   └── docker_runner.py   # Docker management
│   ├── core/
│   │   ├── population.py      # Population management
│   │   ├── crossover.py       # Genetic crossover
│   │   └── mutation.py        # Genetic mutation
│   ├── storage/
│   │   ├── db.py              # Database setup
│   │   └── models.py          # SQLAlchemy models
│   ├── core/
│   │   ├── config.py          # Configuration
│   │   └── logger.py          # Logging setup
│   └── main.py                # FastAPI application
├── data/
│   └── evolution.db           # SQLite database
├── output/
│   └── generated_api/         # Generated API code
└── reasoning-ui/
    └── src/
        ├── EvolutionDashboard.js  # React dashboard
        └── App.js

```

---

## 🛠️ Installation

### Prerequisites
- Python 3.10+
- Node.js 16+ and npm
- Docker (optional, for container testing)
- Ollama (optional, for LLM-based reasoning)

### Backend Setup

1. **Navigate to backend directory**:
```bash
cd autonomous-api
```

2. **Install dependencies**:
```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install -e .
```

3. **Configure environment**:
```bash
cp .env.example .env
# Edit .env with your settings
```

4. **Initialize database** (automatic on first run):
```bash
# Database is created automatically when you start the server
```

5. **Start the backend**:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

### Frontend Setup

1. **Navigate to frontend directory**:
```bash
cd reasoning-ui
```

2. **Install dependencies**:
```bash
npm install
```

3. **Configure environment** (optional):
```bash
echo "REACT_APP_API_URL=http://127.0.0.1:8000" > .env
```

4. **Start the development server**:
```bash
npm start
```

The dashboard will open at `http://localhost:3000`

---

## 🎮 Usage

### Web Dashboard (Recommended)

1. Start both backend and frontend
2. Open `http://localhost:3000`
3. Configure evolution parameters:
   - **Generations**: Number of evolution cycles (1-100)
   - **Population Size**: Individuals per generation (4-50)
   - **Use Docker**: Enable container building/testing
4. Click **"🚀 Start Evolution"** for async mode with live updates
5. Watch real-time progress via WebSocket stream

### API Endpoints

#### Start Async Evolution
```bash
curl -X POST "http://localhost:8000/evolve/start" \
  -H "Content-Type: application/json" \
  -d '{"generations": 10, "population_size": 10, "use_docker": false}'
```

Returns immediately with run_id. Connect to WebSocket for updates.

#### Run Sync Evolution (Testing)
```bash
curl -X POST "http://localhost:8000/evolve/sync" \
  -H "Content-Type: application/json" \
  -d '{"generations": 5, "population_size": 8}'
```

Blocks until completion. Returns full results.

#### Get Evolution Runs
```bash
curl http://localhost:8000/evolve/runs
```

#### Get Specific Run
```bash
curl http://localhost:8000/evolve/run/{run_id}
```

#### WebSocket Connection
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/evolution');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Evolution update:', data);
};
```

---

## 📊 WebSocket Events

The system streams real-time events:

| Event Type | Description |
|------------|-------------|
| `evolution_start` | Evolution run started |
| `generation_start` | New generation beginning |
| `generation_complete` | Generation finished with scores |
| `new_best` | New best genome discovered |
| `building_best` | Building output from best genome |
| `docker_test` | Docker build/test results |
| `evolution_complete` | Entire evolution finished |

---

## 🧪 Example Output

### Best Genome
```json
{
  "services": ["auth", "users", "payments", "analytics"],
  "auth": "jwt",
  "database": "postgres",
  "cache_enabled": true,
  "rate_limiting": true,
  "cors_enabled": true,
  "logging_level": "INFO",
  "api_version": "v2",
  "security_score": 1.0
}
```

### Generated API Structure
```
output/generated_api/
├── main.py                 # FastAPI application
├── requirements.txt        # Python dependencies
├── Dockerfile             # Container definition
├── README.md              # API documentation
└── services/
    ├── __init__.py
    ├── auth.py            # Authentication service
    ├── users.py           # User management
    ├── payments.py        # Payment processing
    └── analytics.py       # Analytics service
```

Each service includes:
- CRUD endpoints
- Pydantic models
- In-memory storage (replaceable with database)
- Optional JWT middleware

---

## 🔧 Configuration

### Environment Variables (.env)

```env
# Application
APP_NAME=Autonomous Evolution Engine
APP_VERSION=0.1.0
DEBUG=false

# LLM (Optional)
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3

# API
API_HOST=0.0.0.0
API_PORT=8000

# CORS
CORS_ORIGINS=["http://localhost:3000","http://127.0.0.1:3000"]
```

### Evolution Parameters

| Parameter | Range | Default | Description |
|-----------|-------|---------|-------------|
| generations | 1-100 | 10 | Evolution cycles |
| population_size | 4-50 | 10 | Individuals per gen |
| mutation_rate | 0.0-1.0 | 0.2 | Mutation probability |
| use_docker | bool | false | Build/test containers |

---

## 🧬 Evolution Algorithm

### Process Flow

1. **Initialization**: Create random population of genomes
2. **Evaluation**: Calculate fitness for each genome
3. **Selection**: Choose top performers as parents
4. **Crossover**: Combine parent genes to create children
5. **Mutation**: Randomly modify child genes
6. **Replacement**: New generation replaces old
7. **Repeat**: Continue for N generations
8. **Output**: Build best genome into runnable API

### Fitness Function Weights

```
Security:       ████████████████████░░░░ 30%
Architecture:   ████████████████░░░░░░░░ 25%
Performance:    ████████████░░░░░░░░░░░░ 20%
Best Practices: █████████░░░░░░░░░░░░░░░ 15%
Database:       ██████░░░░░░░░░░░░░░░░░░ 10%
```

---

## 🐳 Docker Integration

When `use_docker=true`:

1. System generates complete API code
2. Builds Docker image from generated Dockerfile
3. Runs container on random port (8001-9000)
4. Tests API health endpoint
5. Reports success/failure
6. Cleans up container after test

**Note**: Requires Docker Desktop running locally.

---

## 💾 Database Schema

### Genomes Table
- `id`: Primary key
- `genome_data`: JSON (full genome configuration)
- `fitness_score`: Float (0.0-1.0)
- `generation`: Integer (which generation)
- `created_at`: Timestamp

### Evolution Runs Table
- `id`: Primary key
- `run_id`: UUID (unique run identifier)
- `status`: String (running/completed/failed)
- `total_generations`: Integer
- `best_fitness`: Float
- `best_genome`: JSON
- `history`: JSON (fitness history)
- `started_at`: Timestamp
- `completed_at`: Timestamp

---

## 🔍 Troubleshooting

### WebSocket Connection Issues
- Ensure backend is running on port 8000
- Check browser console for connection errors
- Verify CORS settings include frontend URL

### Docker Build Failures
- Ensure Docker Desktop is running
- Check Docker has sufficient resources
- Review generated Dockerfile in output directory

### Database Errors
- Delete `data/evolution.db` to reset
- Check write permissions on data directory

### Slow Evolution
- Reduce population size (8-10 is good for testing)
- Reduce generations (5-10 for quick tests)
- Disable Docker testing for faster runs

---

## 📈 Performance Tips

### Quick Testing
```bash
# Fast test: 5 generations, 8 individuals, no Docker
POST /evolve/sync
{
  "generations": 5,
  "population_size": 8
}
```

### Production-Quality Evolution
```bash
# Thorough evolution: 20 generations, 15 individuals
POST /evolve/start
{
  "generations": 20,
  "population_size": 15,
  "use_docker": true
}
```

---

## 🎯 Use Cases

### 1. API Architecture Research
- Study how different configurations affect fitness
- Analyze trade-offs between security and complexity

### 2. Rapid Prototyping
- Generate working API scaffolds instantly
- Customize by adjusting fitness weights

### 3. Educational Tool
- Visualize genetic algorithms in action
- Understand multi-objective optimization

### 4. Portfolio Project
- Demonstrates advanced software engineering
- Shows full-stack development skills

---

## 🚧 Future Enhancements

Potential upgrades:
- [ ] Kubernetes deployment per genome
- [ ] Real database integration testing
- [ ] Load testing generated APIs
- [ ] AI-assisted mutation strategies
- [ ] Multi-objective Pareto front visualization
- [ ] Export to Terraform/CloudFormation
- [ ] Collaborative evolution (distributed)

---

## 📝 License

MIT License - Feel free to use for personal or commercial projects.

---

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create feature branch
3. Make changes
4. Submit pull request

---

## 🙏 Acknowledgments

Built with:
- **FastAPI**: Modern Python web framework
- **SQLAlchemy**: Database ORM
- **React**: Frontend UI library
- **WebSockets**: Real-time communication
- **Docker**: Containerization

---

## 📞 Support

For issues or questions:
1. Check troubleshooting section
2. Review API docs at `/docs`
3. Inspect browser console for frontend errors
4. Check backend logs in terminal

---

**Built with ❤️ for autonomous systems research**

*Version 3.0 - Production-Grade Evolution Engine*
