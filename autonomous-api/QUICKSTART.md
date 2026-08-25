# 🚀 Quick Start Guide

## Get Running in 5 Minutes

### Step 1: Install Backend Dependencies

```bash
cd autonomous-api
uv sync
```

Or with pip:
```bash
pip install -e .
```

### Step 2: Start Backend Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

You should see:
```
INFO:     Starting Autonomous Evolution Engine v0.1.0
INFO:     Database initialized
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Step 3: Install Frontend Dependencies

Open a new terminal:
```bash
cd reasoning-ui
npm install
```

### Step 4: Start Frontend Dashboard

```bash
npm start
```

Your browser will open to `http://localhost:3000`

### Step 5: Run Your First Evolution

1. In the dashboard, set:
   - Generations: **5**
   - Population Size: **8**
   - Use Docker: **Unchecked** (for first test)

2. Click **"🚀 Start Evolution"**

3. Watch real-time progress!

---

## Alternative: Quick Test via API

Test without the UI:

```bash
# Start evolution (async)
curl -X POST "http://localhost:8000/evolve/start" \
  -H "Content-Type: application/json" \
  -d '{"generations": 5, "population_size": 8}'

# Or run synchronously (blocks until done)
curl -X POST "http://localhost:8000/evolve/sync" \
  -H "Content-Type: application/json" \
  -d '{"generations": 3, "population_size": 6}'
```

---

## Verify Installation

Run the test suite:

```bash
cd autonomous-api
python test_system.py
```

Expected output:
```
🧬 Autonomous Evolution Engine - Test Suite
============================================================
🧪 Testing imports...
  ✓ Genome module
  ✓ Population module
  ...
🎉 All tests passed! System is ready.
```

---

## What Happens Next?

1. **Evolution starts**: Population of random API architectures created
2. **Generations progress**: Each generation improves fitness
3. **Best genome selected**: Highest-scoring architecture wins
4. **Code generated**: Complete FastAPI application built
5. **Output saved**: In `output/generated_api/` directory

---

## Check Generated Output

After evolution completes:

```bash
ls output/generated_api/
# You'll see:
# main.py
# requirements.txt
# Dockerfile
# README.md
# services/
```

View the generated API:
```bash
cat output/generated_api/main.py
```

---

## Enable Docker Testing (Optional)

If you have Docker installed:

1. Ensure Docker Desktop is running
2. In dashboard, check **"Use Docker"**
3. Start evolution

System will:
- Build Docker image from generated code
- Run container
- Test API health endpoint
- Report results

---

## Troubleshooting

### Backend won't start
```bash
# Check Python version (need 3.10+)
python --version

# Reinstall dependencies
pip install -e .
```

### Frontend shows connection error
- Ensure backend is running on port 8000
- Check browser console for errors
- Verify CORS settings in `.env`

### WebSocket disconnects
- Normal during development (auto-reconnects)
- Check network tab in browser DevTools

### Database errors
```bash
# Reset database
rm data/evolution.db
# Restart backend (will recreate)
```

---

## Next Steps

✅ **Experiment**: Try different generation/population sizes  
✅ **Analyze**: Study best genomes and fitness scores  
✅ **Customize**: Modify fitness weights in `engine/fitness.py`  
✅ **Extend**: Add new services or genes  

---

**Happy Evolving! 🧬**
