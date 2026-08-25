# 🧬 Elite Evolution - Quick Start

## Get Started in 2 Minutes

### 1. Install Dependencies (if not done)
```bash
cd autonomous-api
uv sync
```

### 2. Start Backend
```bash
uvicorn app.main:app --reload
```

### 3. Start Frontend
```bash
cd reasoning-ui
npm start
```

### 4. Run Elite Evolution
1. Open http://localhost:3000
2. Check **"🧠 Elite Mode"**
3. Click **"🧬 Start Elite Evolution"**
4. Watch it learn! 🎉

---

## What's New?

### ✨ Elite Features
- **Multi-Population**: 4 specialized groups evolving in parallel
- **Adaptive Mutation**: Learns which features work best
- **Persistent Memory**: Remembers successful patterns
- **Real Insights**: Generates actionable recommendations

### 📊 Dashboard Upgrades
- Orange elite mode button
- Group-specific progress tracking
- Learning insights panel
- Pattern analysis display

---

## API Quick Reference

### Start Elite Evolution
```bash
curl -X POST http://localhost:8000/evolve/elite/start \
  -H "Content-Type: application/json" \
  -d '{"generations": 10, "population_size": 8}'
```

### Get Insights
```bash
curl http://localhost:8000/evolve/elite/insights
```

### Clear Memory
```bash
curl -X POST http://localhost:8000/evolve/elite/clear-memory
```

---

## Key Concepts

### Multi-Population System
- **Performance**: Optimized for speed
- **Security**: Optimized for protection
- **Balanced**: General optimization
- **Minimal**: Lean architectures

### Adaptive Learning
- Tracks which auth methods work
- Learns best database choices
- Identifies successful feature combinations
- Biases mutation toward proven patterns

### Cross-Pollination
- Every 3 generations
- Groups exchange best genomes
- Spreads good traits
- Maintains diversity

---

## Expected Output

```
🚀 Elite evolution started: 10 generations
✅ [performance] Gen 1: Best=0.723
✅ [security] Gen 1: Best=0.698
✅ [balanced] Gen 1: Best=0.745
✅ [minimal] Gen 1: Best=0.512
🏆 New global best! Fitness: 0.745
🔄 Cross-pollination at generation 3
...
🎉 Elite evolution complete! Best fitness: 0.867

📊 Insights:
- Best Auth: JWT (score: 0.823)
- Best Database: PostgreSQL (score: 0.845)
- Cache Impact: +15.6%
- Rate Limiting Impact: +12.3%
```

---

## Troubleshooting

### Elite mode not showing?
- Refresh the page
- Check console for errors
- Ensure backend is running

### No insights appearing?
- Run at least one evolution first
- Click "Load Insights" button
- Check backend logs

### Slow performance?
- Reduce population size to 6
- Reduce generations to 5
- Disable Docker testing

---

**Ready to evolve with intelligence! 🧬✨**
