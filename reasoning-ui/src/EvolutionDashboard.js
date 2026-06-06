import { useState, useEffect, useRef } from "react";

const API_BASE = process.env.REACT_APP_API_URL || "http://127.0.0.1:8000";
const WS_BASE = API_BASE.replace("http", "ws").replace("https", "wss");

export default function EvolutionDashboard() {
  const [isConnected, setIsConnected] = useState(false);
  const [evolutionStarted, setEvolutionStarted] = useState(false);
  const [currentRun, setCurrentRun] = useState(null);
  const [messages, setMessages] = useState([]);
  const [generations, setGenerations] = useState(10);
  const [populationSize, setPopulationSize] = useState(10);
  const [useDocker, setUseDocker] = useState(false);
  const [bestGenome, setBestGenome] = useState(null);
  const [fitnessHistory, setFitnessHistory] = useState([]);
  
  // Elite evolution state
  const [eliteMode, setEliteMode] = useState(false);
  const [useMultiPopulation, setUseMultiPopulation] = useState(true);
  const [enableAdaptiveMutation, setEnableAdaptiveMutation] = useState(true);
  const [insights, setInsights] = useState(null);
  const [groupHistory, setGroupHistory] = useState({});
  
  const wsRef = useRef(null);
  const messagesEndRef = useRef(null);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // WebSocket connection
  useEffect(() => {
    const connectWebSocket = () => {
      const ws = new WebSocket(`${WS_BASE}/ws/evolution`);

      ws.onopen = () => {
        console.log("WebSocket connected");
        setIsConnected(true);
        addMessage("system", "Connected to evolution server");
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          handleWebSocketMessage(data);
        } catch (error) {
          console.error("Error parsing WebSocket message:", error);
        }
      };

      ws.onclose = () => {
        console.log("WebSocket disconnected");
        setIsConnected(false);
        addMessage("system", "Disconnected from server");
        
        // Try to reconnect after 3 seconds
        setTimeout(connectWebSocket, 3000);
      };

      ws.onerror = (error) => {
        console.error("WebSocket error:", error);
        addMessage("error", "WebSocket connection error");
      };

      wsRef.current = ws;
    };

    connectWebSocket();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  const addMessage = (type, content) => {
    setMessages((prev) => [...prev, { type, content, timestamp: new Date() }]);
  };

  const handleWebSocketMessage = (data) => {
    console.log("Received:", data);

    switch (data.type) {
      case "evolution_start":
        addMessage("info", `🚀 Evolution started: ${data.generations} generations`);
        setCurrentRun(data.run_id);
        setEvolutionStarted(true);
        setFitnessHistory([]);
        break;

      case "generation_start":
        addMessage("info", `⏳ Generation ${data.generation}/${data.total_generations}`);
        break;

      case "generation_complete":
        addMessage("success", `✅ Gen ${data.generation}: Best=${data.best_score.toFixed(3)}, Avg=${data.avg_score.toFixed(3)}`);
        setFitnessHistory((prev) => [
          ...prev,
          {
            generation: data.generation,
            best: data.best_score,
            avg: data.avg_score,
          },
        ]);
        break;

      case "new_best":
        addMessage("highlight", `🏆 New best genome! Fitness: ${data.fitness.toFixed(3)}`);
        setBestGenome(data.genome);
        break;

      case "building_best":
        addMessage("info", `🔨 Building best genome at: ${data.output_path}`);
        break;

      case "docker_test":
        if (data.result.success) {
          addMessage("success", `🐳 Docker test PASSED on port ${data.result.port}`);
        } else {
          addMessage("error", `🐳 Docker test FAILED: ${data.result.error}`);
        }
        break;

      case "evolution_complete":
        addMessage("success", `🎉 Evolution complete! Run ID: ${data.run_id}`);
        setEvolutionStarted(false);
        break;

      // Elite evolution events
      case "elite_evolution_start":
        addMessage("info", `🚀 Elite evolution started: ${data.generations} generations, Groups: ${data.groups.join(", ")}`);
        setCurrentRun(data.run_id);
        setEvolutionStarted(true);
        setFitnessHistory([]);
        setGroupHistory({});
        break;

      case "new_global_best":
        addMessage("highlight", `🏆 New global best! Group: ${data.group}, Fitness: ${data.fitness.toFixed(3)}`);
        setBestGenome(data.genome);
        break;

      case "group_complete":
        addMessage("success", `✅ [${data.group}] Gen ${data.generation}: Best=${data.best_score.toFixed(3)}, Avg=${data.avg_score.toFixed(3)}`);
        
        // Update group-specific history
        setGroupHistory((prev) => {
          const updated = { ...prev };
          if (!updated[data.group]) {
            updated[data.group] = [];
          }
          updated[data.group].push({
            generation: data.generation,
            best: data.best_score,
            avg: data.avg_score,
          });
          return updated;
        });
        break;

      case "cross_pollination":
        addMessage("info", `🔄 Cross-pollination at generation ${data.generation}`);
        break;

      case "building_complete":
        addMessage("success", `🔨 Building complete! Output: ${data.output_path}`);
        break;

      case "elite_evolution_complete":
        addMessage("success", `🎉 Elite evolution complete! Best fitness: ${data.result.best_fitness.toFixed(3)}`);
        setEvolutionStarted(false);
        // Auto-load insights
        loadInsights();
        break;

      default:
        addMessage("info", JSON.stringify(data));
    }
  };

  const startEvolution = async () => {
    try {
      const response = await fetch(`${API_BASE}/evolve/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          generations,
          population_size: populationSize,
          use_docker: useDocker,
        }),
      });

      const data = await response.json();
      addMessage("system", data.message);
    } catch (error) {
      addMessage("error", `Failed to start evolution: ${error.message}`);
    }
  };

  const runSyncEvolution = async () => {
    try {
      addMessage("info", "Running synchronous evolution...");
      const response = await fetch(`${API_BASE}/evolve/sync`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          generations,
          population_size: populationSize,
        }),
      });

      const data = await response.json();
      addMessage("success", `Synchronous evolution complete!`);
      setBestGenome(data.best_genome);
      setFitnessHistory(
        data.history.map((h) => ({
          generation: h.generation,
          best: h.best_score,
          avg: h.avg_score,
        }))
      );
    } catch (error) {
      addMessage("error", `Sync evolution failed: ${error.message}`);
    }
  };

  const startEliteEvolution = async () => {
    try {
      const response = await fetch(`${API_BASE}/evolve/elite/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          generations,
          population_size: populationSize,
          use_multi_population: useMultiPopulation,
          enable_adaptive_mutation: enableAdaptiveMutation,
          use_docker: useDocker,
        }),
      });

      const data = await response.json();
      addMessage("system", data.message);
      addMessage("info", `Features: Multi-pop=${data.features.multi_population}, Adaptive=${data.features.adaptive_mutation}`);
    } catch (error) {
      addMessage("error", `Failed to start elite evolution: ${error.message}`);
    }
  };

  const loadInsights = async () => {
    try {
      const response = await fetch(`${API_BASE}/evolve/elite/insights`);
      const data = await response.json();
      setInsights(data);
      addMessage("success", "Insights loaded");
    } catch (error) {
      addMessage("error", `Failed to load insights: ${error.message}`);
    }
  };

  return (
    <div style={styles.container}>
      <header style={styles.header}>
        <h1 style={styles.title}>🧬 Autonomous Evolution Engine</h1>
        <div style={styles.status}>
          <span style={{ color: isConnected ? "#22c55e" : "#ef4444" }}>
            {isConnected ? "● Connected" : "○ Disconnected"}
          </span>
        </div>
      </header>

      <div style={styles.mainContent}>
        {/* Control Panel */}
        <div style={styles.controlPanel}>
          <h2 style={styles.sectionTitle}>⚙️ Configuration</h2>

          <div style={styles.formGroup}>
            <label style={styles.label}>Generations:</label>
            <input
              type="number"
              value={generations}
              onChange={(e) => setGenerations(parseInt(e.target.value))}
              min="1"
              max="100"
              style={styles.input}
              disabled={evolutionStarted}
            />
          </div>

          <div style={styles.formGroup}>
            <label style={styles.label}>Population Size:</label>
            <input
              type="number"
              value={populationSize}
              onChange={(e) => setPopulationSize(parseInt(e.target.value))}
              min="4"
              max="50"
              style={styles.input}
              disabled={evolutionStarted}
            />
          </div>

          <div style={styles.formGroup}>
            <label style={styles.checkboxLabel}>
              <input
                type="checkbox"
                checked={useDocker}
                onChange={(e) => setUseDocker(e.target.checked)}
                disabled={evolutionStarted}
              />
              Use Docker (build & test generated APIs)
            </label>
          </div>

          <div style={{ ...styles.formGroup, marginTop: 20, paddingTop: 15, borderTop: "2px solid #334155" }}>
            <label style={{ ...styles.checkboxLabel, fontWeight: "bold", color: "#f59e0b" }}>
              <input
                type="checkbox"
                checked={eliteMode}
                onChange={(e) => setEliteMode(e.target.checked)}
                disabled={evolutionStarted}
              />
              🧠 Elite Mode (Multi-population + Adaptive Learning)
            </label>
          </div>

          {eliteMode && (
            <>
              <div style={styles.formGroup}>
                <label style={styles.checkboxLabel}>
                  <input
                    type="checkbox"
                    checked={useMultiPopulation}
                    onChange={(e) => setUseMultiPopulation(e.target.checked)}
                    disabled={evolutionStarted}
                  />
                  Multi-Population System (4 specialized groups)
                </label>
              </div>

              <div style={styles.formGroup}>
                <label style={styles.checkboxLabel}>
                  <input
                    type="checkbox"
                    checked={enableAdaptiveMutation}
                    onChange={(e) => setEnableAdaptiveMutation(e.target.checked)}
                    disabled={evolutionStarted}
                  />
                  Adaptive Mutation (learns from success)
                </label>
              </div>
            </>
          )}

          <div style={styles.buttonGroup}>
            <button
              onClick={eliteMode ? startEliteEvolution : startEvolution}
              disabled={evolutionStarted || !isConnected}
              style={{
                ...styles.button,
                ...(eliteMode ? styles.eliteButton : styles.primaryButton),
                opacity: evolutionStarted || !isConnected ? 0.5 : 1,
              }}
            >
              {evolutionStarted ? "Evolving..." : eliteMode ? "🧬 Start Elite Evolution" : "🚀 Start Evolution"}
            </button>

            <button
              onClick={runSyncEvolution}
              disabled={evolutionStarted || !isConnected}
              style={{
                ...styles.button,
                opacity: evolutionStarted || !isConnected ? 0.5 : 1,
              }}
            >
              ⚡ Quick Test (Sync)
            </button>

            {eliteMode && (
              <button
                onClick={loadInsights}
                disabled={!isConnected}
                style={{
                  ...styles.button,
                  background: "#8b5cf6",
                  opacity: !isConnected ? 0.5 : 1,
                }}
              >
                📊 Load Insights
              </button>
            )}
          </div>
        </div>

        {/* Best Genome Display */}
        {bestGenome && (
          <div style={styles.genomePanel}>
            <h2 style={styles.sectionTitle}>🏆 Best Genome</h2>
            <pre style={styles.genomeCode}>{JSON.stringify(bestGenome, null, 2)}</pre>
          </div>
        )}

        {/* Insights Panel (Elite Mode) */}
        {insights && eliteMode && (
          <div style={styles.insightsPanel}>
            <h2 style={styles.sectionTitle}>🧠 Learning Insights</h2>
            
            {insights.pattern_insights && (
              <div style={styles.insightSection}>
                <h3 style={styles.insightTitle}>Pattern Analysis</h3>
                {insights.pattern_insights.best_auth && (
                  <div style={styles.insightItem}>
                    <strong>Best Auth:</strong> {insights.pattern_insights.best_auth.method} 
                    (score: {insights.pattern_insights.best_auth.avg_score.toFixed(3)})
                  </div>
                )}
                {insights.pattern_insights.best_database && (
                  <div style={styles.insightItem}>
                    <strong>Best Database:</strong> {insights.pattern_insights.best_database.type}
                    (score: {insights.pattern_insights.best_database.avg_score.toFixed(3)})
                  </div>
                )}
                <div style={styles.insightItem}>
                  <strong>Cache Impact:</strong> {(insights.pattern_insights.cache_impact * 100).toFixed(1)}%
                </div>
                <div style={styles.insightItem}>
                  <strong>Rate Limiting Impact:</strong> {(insights.pattern_insights.rate_limiting_impact * 100).toFixed(1)}%
                </div>
              </div>
            )}

            {insights.suggested_genome && (
              <div style={styles.insightSection}>
                <h3 style={styles.insightTitle}>Suggested Configuration</h3>
                <pre style={styles.suggestionCode}>
                  {JSON.stringify(insights.suggested_genome, null, 2)}
                </pre>
              </div>
            )}

            {insights.statistics && (
              <div style={styles.insightSection}>
                <h3 style={styles.insightTitle}>Statistics</h3>
                <div style={styles.insightItem}>
                  <strong>Total Runs:</strong> {insights.statistics.total_runs}
                </div>
                <div style={styles.insightItem}>
                  <strong>Average Best Fitness:</strong> {insights.statistics.avg_best_fitness.toFixed(3)}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Fitness History Chart */}
        {fitnessHistory.length > 0 && (
          <div style={styles.chartPanel}>
            <h2 style={styles.sectionTitle}>📊 Fitness History</h2>
            <div style={styles.chart}>
              {fitnessHistory.map((h, idx) => (
                <div key={idx} style={styles.chartRow}>
                  <span style={styles.chartLabel}>Gen {h.generation}</span>
                  <div style={styles.chartBars}>
                    <div
                      style={{
                        ...styles.chartBar,
                        width: `${h.best * 100}%`,
                        background: "#22c55e",
                      }}
                    >
                      Best: {h.best.toFixed(3)}
                    </div>
                    <div
                      style={{
                        ...styles.chartBar,
                        width: `${h.avg * 100}%`,
                        background: "#3b82f6",
                        marginTop: 4,
                      }}
                    >
                      Avg: {h.avg.toFixed(3)}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Message Log */}
        <div style={styles.logPanel}>
          <h2 style={styles.sectionTitle}>📜 Event Log</h2>
          <div style={styles.log}>
            {messages.map((msg, idx) => (
              <div
                key={idx}
                style={{
                  ...styles.logEntry,
                  borderLeft: `3px solid ${getMessageColor(msg.type)}`,
                }}
              >
                <span style={styles.logTime}>
                  {msg.timestamp.toLocaleTimeString()}
                </span>
                <span style={styles.logContent}>{msg.content}</span>
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>
        </div>
      </div>
    </div>
  );
}

function getMessageColor(type) {
  switch (type) {
    case "success":
      return "#22c55e";
    case "error":
      return "#ef4444";
    case "highlight":
      return "#f59e0b";
    case "info":
      return "#3b82f6";
    default:
      return "#6b7280";
  }
}

const styles = {
  container: {
    minHeight: "100vh",
    background: "linear-gradient(135deg, #0f172a 0%, #1e293b 100%)",
    padding: 20,
    fontFamily: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
  },
  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 30,
    paddingBottom: 20,
    borderBottom: "2px solid #334155",
  },
  title: {
    color: "white",
    margin: 0,
    fontSize: 32,
  },
  status: {
    fontSize: 16,
    fontWeight: "bold",
  },
  mainContent: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: 20,
    maxWidth: 1400,
    margin: "0 auto",
  },
  controlPanel: {
    background: "#1e293b",
    padding: 20,
    borderRadius: 12,
    gridColumn: "1 / -1",
  },
  genomePanel: {
    background: "#1e293b",
    padding: 20,
    borderRadius: 12,
  },
  insightsPanel: {
    background: "#1e293b",
    padding: 20,
    borderRadius: 12,
    border: "2px solid #f59e0b",
  },
  insightSection: {
    marginBottom: 20,
    paddingBottom: 15,
    borderBottom: "1px solid #334155",
  },
  insightTitle: {
    color: "#f59e0b",
    fontSize: 16,
    marginTop: 0,
    marginBottom: 10,
  },
  insightItem: {
    color: "#e2e8f0",
    fontSize: 14,
    marginBottom: 8,
    paddingLeft: 10,
  },
  suggestionCode: {
    background: "#0f172a",
    padding: 12,
    borderRadius: 6,
    color: "#22c55e",
    fontSize: 12,
    overflow: "auto",
  },
  chartPanel: {
    background: "#1e293b",
    padding: 20,
    borderRadius: 12,
  },
  logPanel: {
    background: "#1e293b",
    padding: 20,
    borderRadius: 12,
    gridColumn: "1 / -1",
  },
  sectionTitle: {
    color: "white",
    marginTop: 0,
    marginBottom: 20,
    fontSize: 20,
  },
  formGroup: {
    marginBottom: 15,
  },
  label: {
    display: "block",
    color: "#94a3b8",
    marginBottom: 5,
    fontSize: 14,
  },
  checkboxLabel: {
    color: "#94a3b8",
    display: "flex",
    alignItems: "center",
    gap: 8,
    cursor: "pointer",
  },
  input: {
    width: "100%",
    padding: 10,
    borderRadius: 6,
    border: "1px solid #334155",
    background: "#0f172a",
    color: "white",
    fontSize: 14,
  },
  buttonGroup: {
    display: "flex",
    gap: 10,
    marginTop: 20,
  },
  button: {
    flex: 1,
    padding: "12px 24px",
    borderRadius: 8,
    border: "none",
    fontSize: 16,
    fontWeight: "bold",
    cursor: "pointer",
    transition: "all 0.2s",
  },
  primaryButton: {
    background: "#22c55e",
    color: "white",
  },
  eliteButton: {
    background: "linear-gradient(135deg, #f59e0b 0%, #d97706 100%)",
    color: "white",
  },
  genomeCode: {
    background: "#0f172a",
    padding: 15,
    borderRadius: 8,
    color: "#22c55e",
    fontSize: 13,
    overflow: "auto",
    maxHeight: 400,
  },
  chart: {
    maxHeight: 400,
    overflowY: "auto",
  },
  chartRow: {
    marginBottom: 10,
  },
  chartLabel: {
    color: "#94a3b8",
    fontSize: 12,
    display: "block",
    marginBottom: 4,
  },
  chartBars: {
    display: "flex",
    flexDirection: "column",
  },
  chartBar: {
    padding: "6px 10px",
    borderRadius: 4,
    color: "white",
    fontSize: 11,
    whiteSpace: "nowrap",
    overflow: "hidden",
    textOverflow: "ellipsis",
    transition: "width 0.3s",
  },
  log: {
    height: 400,
    overflowY: "auto",
    background: "#0f172a",
    padding: 15,
    borderRadius: 8,
  },
  logEntry: {
    padding: "8px 12px",
    marginBottom: 8,
    background: "#1e293b",
    borderRadius: 6,
    display: "flex",
    gap: 10,
    alignItems: "flex-start",
  },
  logTime: {
    color: "#64748b",
    fontSize: 11,
    minWidth: 70,
  },
  logContent: {
    color: "#e2e8f0",
    fontSize: 13,
    flex: 1,
  },
};
