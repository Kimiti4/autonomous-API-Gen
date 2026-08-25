# 🚀 Production Deployment Guide

Complete guide for deploying the Autonomous Evolution Engine to production.

---

## 📋 Prerequisites

- Python 3.10+
- Docker (optional, for containerized API testing)
- PostgreSQL or SQLite database
- SSL certificate (for HTTPS)
- Domain name (recommended)

---

## 🔧 Installation

### 1. Clone Repository

```bash
git clone <your-repo-url>
cd autonomous-api
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
# or if using uv
uv sync
```

### 4. Configure Environment Variables

Create `.env` file in project root:

```env
# Application Settings
APP_NAME=Autonomous Evolution Engine
APP_VERSION=3.1.0
DEBUG=false

# Database
DATABASE_URL=sqlite:///./evolution.db
# For production use PostgreSQL:
# DATABASE_URL=postgresql://user:password@localhost:5432/evolution_db

# Ollama Configuration
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2

# CORS Configuration (comma-separated origins)
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# Security
SECRET_KEY=your-super-secret-key-change-in-production
API_KEY_HEADER=X-API-Key
ADMIN_API_KEY=change-this-to-random-string

# Rate Limiting
RATE_LIMIT_GENERAL=100
RATE_LIMIT_EVOLUTION=20
RATE_LIMIT_WINDOW=60

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/app.log
```

### 5. Initialize Database

```bash
python -c "from app.storage.db import init_db; init_db()"
```

---

## 🏃 Running in Production

### Option 1: Using Uvicorn (Recommended)

```bash
uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 4 \
    --log-level info \
    --access-log
```

### Option 2: Using Gunicorn + Uvicorn Workers

```bash
pip install gunicorn

gunicorn app.main:app \
    -w 4 \
    -k uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --access-logfile - \
    --error-logfile logs/error.log
```

### Option 3: Docker Container

Create `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# Copy application
COPY . .

# Create non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:

```bash
docker build -t evolution-engine .
docker run -d \
    --name evolution-engine \
    -p 8000:8000 \
    -v ./data:/app/data \
    -e DATABASE_URL=sqlite:///./data/evolution.db \
    evolution-engine
```

---

## 🔐 Security Hardening

### 1. Enable HTTPS

Use Nginx as reverse proxy with SSL:

```nginx
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### 2. Add API Key Authentication

Create middleware in `app/middleware/auth.py`:

```python
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
import os

class APIKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Skip auth for health checks and docs
        if request.url.path in ["/health", "/docs", "/openapi.json"]:
            return await call_next(request)
        
        api_key = request.headers.get("X-API-Key")
        expected_key = os.getenv("ADMIN_API_KEY")
        
        if not api_key or api_key != expected_key:
            raise HTTPException(status_code=401, detail="Invalid API key")
        
        return await call_next(request)
```

Add to `main.py`:

```python
from app.middleware.auth import APIKeyMiddleware
app.add_middleware(APIKeyMiddleware)
```

### 3. Configure Firewall

```bash
# Allow only necessary ports
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
```

---

## 📊 Monitoring & Observability

### 1. Health Check Endpoint

Monitor `/health` endpoint:

```bash
curl https://yourdomain.com/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "3.1.0",
  "timestamp": "2024-01-15T10:30:00",
  "components": {
    "database": "healthy",
    "memory": "healthy",
    "disk": "healthy"
  },
  "memory_usage": {
    "rss_mb": 125.45,
    "vms_mb": 450.23,
    "percent": 12.5
  }
}
```

### 2. Set Up Monitoring Alerts

**Prometheus Metrics** (optional):

Install `prometheus-fastapi-instrumentator`:

```bash
pip install prometheus-fastapi-instrumentator
```

Add to `main.py`:

```python
from prometheus_fastapi_instrumentator import Instrumentator

Instrumentator().instrument(app).expose(app)
```

Access metrics at `/metrics`.

### 3. Log Aggregation

Configure logging to file:

```python
# In app/core/logger.py
from loguru import logger
import sys

logger.remove()
logger.add(
    "logs/app_{time}.log",
    rotation="500 MB",
    retention="10 days",
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
)
logger.add(sys.stderr, level="INFO")
```

Send logs to centralized system (ELK, Datadog, etc.).

---

## 🔄 CI/CD Pipeline

### GitHub Actions Example

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest
      
      - name: Run tests
        run: pytest tests/
  
  deploy:
    needs: test
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Build Docker image
        run: docker build -t evolution-engine .
      
      - name: Deploy to server
        uses: appleboy/scp-action@master
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SSH_KEY }}
          source: "."
          target: "/opt/evolution-engine"
      
      - name: Restart service
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SSH_KEY }}
          script: |
            cd /opt/evolution-engine
            docker-compose down
            docker-compose up -d
```

---

## 🛡️ Backup Strategy

### 1. Database Backups

Create backup script `backup.sh`:

```bash
#!/bin/bash
BACKUP_DIR="/backups/evolution-db"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup SQLite
cp data/evolution.db $BACKUP_DIR/evolution_$TIMESTAMP.db

# Or backup PostgreSQL
# pg_dump evolution_db > $BACKUP_DIR/evolution_$TIMESTAMP.sql

# Keep only last 7 days
find $BACKUP_DIR -type f -mtime +7 -delete

echo "Backup completed: evolution_$TIMESTAMP.db"
```

Schedule with cron:

```cron
0 2 * * * /path/to/backup.sh >> /var/log/backup.log 2>&1
```

### 2. Memory Backup

The elite memory system stores data in `memory.json`. Include this in backups:

```bash
cp app/engine/memory.json $BACKUP_DIR/memory_$TIMESTAMP.json
```

---

## 📈 Performance Tuning

### 1. Database Optimization

For PostgreSQL:

```sql
-- Add indexes
CREATE INDEX idx_evolution_run_id ON evolution_runs(run_id);
CREATE INDEX idx_evolution_started_at ON evolution_runs(started_at);

-- Analyze tables
ANALYZE evolution_runs;
```

### 2. Worker Configuration

Adjust based on CPU cores:

```bash
# Formula: (2 × CPU_CORES) + 1
# For 4-core machine: 9 workers
gunicorn app.main:app -w 9 -k uvicorn.workers.UvicornWorker
```

### 3. Memory Limits

Set memory limits in systemd service:

```ini
[Unit]
Description=Evolution Engine
After=network.target

[Service]
Type=simple
User=appuser
WorkingDirectory=/opt/evolution-engine
ExecStart=/opt/evolution-engine/venv/bin/gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
MemoryLimit=2G
Restart=always

[Install]
WantedBy=multi-user.target
```

---

## 🧪 Pre-Deployment Checklist

- [ ] All environment variables configured
- [ ] Database initialized and backed up
- [ ] SSL certificate installed
- [ ] Firewall rules configured
- [ ] Rate limiting tested
- [ ] Health check endpoint responding
- [ ] Logging configured and rotating
- [ ] Backup scripts tested
- [ ] Monitoring alerts set up
- [ ] API authentication enabled
- [ ] CORS origins restricted
- [ ] Error tracking configured (Sentry, etc.)
- [ ] Load testing completed
- [ ] Documentation updated

---

## 🆘 Troubleshooting

### Server Won't Start

```bash
# Check logs
tail -f logs/error.log

# Verify port is free
sudo lsof -i :8000

# Test configuration
python -c "from app.main import app; print('Config OK')"
```

### High Memory Usage

```bash
# Monitor memory
watch -n 5 'ps aux | grep uvicorn'

# Check for memory leaks
pip install tracemalloc
```

### Database Connection Issues

```bash
# Test connection
python -c "from app.storage.db import SessionLocal; db = SessionLocal(); db.execute('SELECT 1'); print('DB OK')"

# Check database file permissions
ls -la data/evolution.db
```

### Rate Limiting Too Strict

Adjust in `app/middleware/rate_limit.py`:

```python
evolution_limiter = RateLimiter(max_requests=50, window_seconds=60)
```

---

## 📞 Support

- **Documentation:** See `PRODUCTION_HARDENING.md`
- **Issues:** Report on GitHub
- **Emergency:** Check health endpoint first: `/health`

---

## ✅ Post-Deployment Verification

Run the test suite:

```bash
python test_production.py
```

All tests should pass. If any fail, review the specific section in the output.

---

*Version: 3.1.0 - Production Ready*  
*Last Updated: Security & Resilience Upgrade*
