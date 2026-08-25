# ✅ Pre-Launch Checklist

Use this checklist to verify everything is ready before running the system.

---

## 📋 System Requirements

### Backend (Python)
- [ ] Python 3.10+ installed
- [ ] pip or uv package manager available
- [ ] Docker Desktop installed (optional, for container testing)

### Frontend (Node.js)
- [ ] Node.js 16+ installed
- [ ] npm available

---

## 🔧 Installation Checklist

### Backend Setup
- [ ] Navigate to `autonomous-api` directory
- [ ] Run `uv sync` or `pip install -e .`
- [ ] Copy `.env.example` to `.env`
- [ ] Verify dependencies installed without errors

### Frontend Setup
- [ ] Navigate to `reasoning-ui` directory
- [ ] Run `npm install`
- [ ] Verify no dependency conflicts

---

## 🧪 Testing Checklist

### Run Test Suite
```bash
cd autonomous-api
python test_system.py
```

Expected results:
- [ ] All imports successful
- [ ] Genome creation works
- [ ] Fitness evaluation works
- [ ] Code generation works
- [ ] Evolution run completes
- [ ] All tests pass (5/5)

### Manual API Test
```bash
# Start backend
uvicorn app.main:app --reload

# Test root endpoint
curl http://localhost:8000/

# Expected: JSON with "Autonomous Evolution Engine"
```

- [ ] Backend starts without errors
- [ ] Root endpoint returns correct response
- [ ] No import errors in console

### Database Check
- [ ] `data/evolution.db` created after first run
- [ ] No database errors in logs

---

## 🚀 Launch Checklist

### Start Backend
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Verify:
- [ ] Server starts on port 8000
- [ ] "Database initialized" message appears
- [ ] No error messages in console
- [ ] Can access http://localhost:8000/docs (Swagger UI)

### Start Frontend
```bash
cd reasoning-ui
npm start
```

Verify:
- [ ] Browser opens automatically to localhost:3000
- [ ] Dashboard loads without errors
- [ ] WebSocket connection indicator shows "Connected"
- [ ] No console errors in browser DevTools

---

## 🎯 Functional Checklist

### Dashboard Features
- [ ] Connection status shows green (connected)
- [ ] Can adjust generations slider
- [ ] Can adjust population size
- [ ] Can toggle Docker option
- [ ] "Start Evolution" button is enabled

### Evolution Test (Quick)
1. Set generations to 3
2. Set population size to 6
3. Uncheck "Use Docker"
4. Click "Start Evolution"

Verify:
- [ ] Evolution starts immediately
- [ ] Event log shows "Evolution started"
- [ ] Generation progress updates in real-time
- [ ] Fitness scores appear
- [ ] Best genome displayed when complete
- [ ] Final "Evolution complete" message appears

### Check Generated Output
```bash
ls output/generated_api/
```

Verify:
- [ ] `main.py` exists
- [ ] `requirements.txt` exists
- [ ] `Dockerfile` exists
- [ ] `README.md` exists
- [ ] `services/` directory exists
- [ ] Service files present (e.g., `auth.py`, `users.py`)

### View Generated Code
```bash
cat output/generated_api/main.py
```

Verify:
- [ ] Valid Python code
- [ ] FastAPI imports present
- [ ] Services imported correctly
- [ ] Routes defined

---

## 🔌 API Endpoint Checklist

Test all endpoints:

### POST /evolve/start
```bash
curl -X POST http://localhost:8000/evolve/start \
  -H "Content-Type: application/json" \
  -d '{"generations": 3, "population_size": 6}'
```
- [ ] Returns success message
- [ ] Includes note about WebSocket

### POST /evolve/sync
```bash
curl -X POST http://localhost:8000/evolve/sync \
  -H "Content-Type: application/json" \
  -d '{"generations": 2, "population_size": 4}'
```
- [ ] Blocks until completion
- [ ] Returns full results
- [ ] Includes best_genome, history, output_path

### GET /evolve/runs
```bash
curl http://localhost:8000/evolve/runs
```
- [ ] Returns list of runs
- [ ] Shows total count

### GET /evolve/run/{run_id}
```bash
# Use run_id from previous responses
curl http://localhost:8000/evolve/run/{your-run-id}
```
- [ ] Returns specific run details
- [ ] Includes history and best genome

### WebSocket /ws/evolution
- [ ] Can connect via browser or ws client
- [ ] Receives evolution events
- [ ] Auto-reconnects on disconnect

---

## 🐳 Docker Integration Checklist (Optional)

If testing with Docker:

- [ ] Docker Desktop is running
- [ ] Can run `docker --version` successfully
- [ ] Test evolution with "Use Docker" checked
- [ ] Docker build completes
- [ ] Container starts on random port
- [ ] API health check passes
- [ ] Results show in dashboard

---

## 📊 Performance Checklist

### Quick Test (< 10 seconds)
- [ ] 5 generations, 8 population
- [ ] Completes without errors
- [ ] Fitness improves over generations

### Standard Test (< 30 seconds)
- [ ] 10 generations, 10 population
- [ ] Smooth WebSocket updates
- [ ] No memory issues

### Stress Test (optional)
- [ ] 20 generations, 15 population
- [ ] System remains stable
- [ ] Database handles load

---

## 🐛 Error Handling Checklist

### Test Error Scenarios

1. **Stop backend while frontend running**
   - [ ] Frontend shows disconnected
   - [ ] Auto-reconnection attempts visible

2. **Invalid API parameters**
   ```bash
   curl -X POST http://localhost:8000/evolve/sync \
     -H "Content-Type: application/json" \
     -d '{"generations": -5}'
   ```
   - [ ] Returns appropriate error

3. **Database locked**
   - [ ] Handles concurrent access gracefully
   - [ ] No crashes

---

## 📝 Documentation Checklist

- [ ] README.md is comprehensive
- [ ] QUICKSTART.md provides clear steps
- [ ] PROJECT_UPGRADE_SUMMARY.md explains features
- [ ] Code has inline comments
- [ ] API docs available at /docs

---

## ✨ Polish Checklist

### User Experience
- [ ] Dashboard looks professional
- [ ] Colors are consistent
- [ ] Loading states visible
- [ ] Error messages helpful
- [ ] Responsive layout

### Code Quality
- [ ] No console warnings
- [ ] No TODO comments in production code
- [ ] Proper error handling
- [ ] Logging informative
- [ ] Code formatted consistently

---

## 🎉 Final Verification

Before declaring launch-ready:

1. **Fresh Install Test**
   - [ ] Delete `node_modules`, reinstall
   - [ ] Delete `.venv`, reinstall
   - [ ] Delete `data/evolution.db`
   - [ ] Run full workflow from scratch
   - [ ] Everything works

2. **Documentation Review**
   - [ ] All commands in docs work
   - [ ] Screenshots match current UI (if added)
   - [ ] Links are valid

3. **Demo Preparation**
   - [ ] Can run live demo smoothly
   - [ ] Have example outputs ready
   - [ ] Can explain architecture clearly

---

## 🚦 Launch Decision

If all critical items checked:
- ✅ Installation works
- ✅ Tests pass
- ✅ Evolution runs successfully
- ✅ Dashboard functional
- ✅ API endpoints working
- ✅ Documentation complete

**You're ready to launch! 🚀**

---

## 📞 Support Resources

If issues arise:
1. Check troubleshooting section in README
2. Review test suite output
3. Inspect browser console (frontend)
4. Check terminal logs (backend)
5. Verify environment configuration

---

**Last Updated**: v3.0 - Production-Grade Release
