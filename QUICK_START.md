# 🚀 Quick Start Guide - One-Command Startup

Start your entire EvoAPI system (Backend + Frontend + LLM) with a single command!

---

## 📋 Prerequisites

Before using the startup scripts, ensure you have:

1. **Python 3.10+** installed
2. **Node.js 16+** and npm installed
3. **Ollama** installed ([Download here](https://ollama.com))
4. All dependencies installed:
   ```bash
   # Backend
   cd autonomous-api
   pip install -r requirements.txt
   
   # Frontend
   cd reasoning-ui
   npm install
   ```

---

## 🎯 Usage

### Windows Users

#### Option 1: Double-Click (Easiest)
Simply double-click one of these files:
- `START_ALL.bat` - Traditional batch script
- `START_ALL.ps1` - PowerShell script (recommended)

#### Option 2: Command Line
```bash
# Using Batch
START_ALL.bat

# Using PowerShell
.\START_ALL.ps1
```

---

### Linux/Mac Users

Make the script executable first:
```bash
chmod +x start_all.sh
```

Then run:
```bash
./start_all.sh
```

---

## 🌟 What Happens When You Run It?

The script automatically:

1. **Checks & Starts Ollama** (LLM Service)
   - Verifies Ollama is installed
   - Starts Ollama service if not running
   - Downloads `llama3.2` model if missing
   - Runs on port 11434

2. **Starts Backend** (FastAPI API)
   - Launches Python FastAPI server
   - Enables auto-reload for development
   - Runs on port 8000
   - Opens in separate terminal window

3. **Starts Frontend** (React UI)
   - Launches React development server
   - Runs on port 3001 (to avoid conflicts)
   - Opens in separate terminal window

---

## 🌐 Access Points

Once started, access your services at:

| Service | URL | Description |
|---------|-----|-------------|
| **Frontend UI** | http://localhost:3001 | Main application interface |
| **Backend API** | http://localhost:8000 | REST API endpoints |
| **API Docs** | http://localhost:8000/docs | Interactive Swagger UI |
| **Health Check** | http://localhost:8000/health | System status |
| **WebSocket** | ws://localhost:8000/ws/evolution | Real-time evolution updates |
| **Metrics** | http://localhost:8000/metrics | Prometheus metrics |

---

## 🛑 Stopping Services

### Windows
- Close all terminal windows that opened
- Or press `Ctrl+C` in each window

### Linux/Mac
- Press `Ctrl+C` in the terminal where you ran the script
- Or manually kill processes:
  ```bash
  kill <PID>  # PIDs are shown when services start
  ```

---

## 🔧 Troubleshooting

### Port Already in Use

**Error:** "Port 8000 already in use" or "Port 3001 already in use"

**Solution:**
```bash
# Windows - Find and kill process
netstat -ano | findstr :8000
taskkill /F /PID <PID>

# Linux/Mac
lsof -ti:8000 | xargs kill -9
```

### Ollama Not Found

**Error:** "Ollama not found in PATH"

**Solution:**
1. Install Ollama from https://ollama.com
2. Restart your terminal
3. Run the startup script again

### Model Download Takes Forever

**Issue:** First-time llama3.2 download is slow

**Solution:**
- Be patient (model is ~2GB)
- Ensure stable internet connection
- Once downloaded, it's cached for future use

### Frontend Won't Start

**Error:** npm errors or module not found

**Solution:**
```bash
cd reasoning-ui
rm -rf node_modules package-lock.json
npm install
npm start
```

### Backend Import Errors

**Error:** ModuleNotFoundError

**Solution:**
```bash
cd autonomous-api
pip install -r requirements.txt
# Or install individually:
pip install fastapi uvicorn sqlalchemy ollama openai
```

---

## 📝 Script Features

### ✅ Automatic Checks
- Verifies Ollama installation
- Checks if services are already running
- Validates required models exist

### ✅ Smart Behavior
- Doesn't restart already-running services
- Downloads missing models automatically
- Uses different ports to avoid conflicts

### ✅ Clean Shutdown
- Properly stops all services on Ctrl+C
- No orphaned processes
- Safe to interrupt anytime

### ✅ Visual Feedback
- Color-coded output (PowerShell)
- Progress indicators
- Clear status messages
- PID tracking

---

## 🎨 Customization

### Change Ports

Edit the startup scripts:

**Backend Port:**
```bash
# In START_ALL.bat, START_ALL.ps1, or start_all.sh
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 9000
```

**Frontend Port:**
```bash
# In start_all.sh or START_ALL.ps1
PORT=3002 npm start
```

### Disable Ollama Auto-Start

If you want to manage Ollama separately, comment out the Ollama section in the scripts.

### Add More Services

You can extend the scripts to start additional services like:
- PostgreSQL database
- Redis cache
- Prometheus monitoring
- Grafana dashboards

---

## 🚀 Advanced Usage

### Run in Background (Linux/Mac)

```bash
# Start in background
nohup ./start_all.sh > evoapi.log 2>&1 &

# View logs
tail -f evoapi.log

# Stop all
pkill -f "uvicorn|npm start|ollama"
```

### Check Service Status

```bash
# Windows
tasklist | findstr "python npm ollama"

# Linux/Mac
ps aux | grep -E "uvicorn|npm|ollama"
```

### Docker Alternative

For containerized deployment, see `docker-compose.yml`:
```bash
docker-compose up -d
```

---

## 💡 Tips

1. **First Run:** The first startup will be slower due to model download
2. **Subsequent Runs:** Much faster as everything is cached
3. **Development:** Scripts enable hot-reload for both backend and frontend
4. **Production:** Consider using Docker Compose instead
5. **Logs:** Check individual terminal windows for detailed logs

---

## 📞 Need Help?

If you encounter issues:

1. Check the troubleshooting section above
2. Verify all prerequisites are installed
3. Check individual service logs
4. Ensure ports 8000 and 3001 are available
5. Try restarting your computer

---

## 🎉 Success Indicators

You'll know everything is working when you see:

```
========================================
  All Services Started!
========================================

Access Points:
  - Frontend UI:  http://localhost:3001
  - Backend API:  http://localhost:8000
  ...
```

Then open http://localhost:3001 in your browser and start evolving APIs! 🧬
