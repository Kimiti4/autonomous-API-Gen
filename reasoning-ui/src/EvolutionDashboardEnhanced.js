import { useState, useEffect, useRef } from "react";
import { Line, Bar } from "react-chartjs-2";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from "chart.js";

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

const API_BASE = process.env.REACT_APP_API_URL || "http://127.0.0.1:8000";
const WS_BASE = API_BASE.replace("http", "ws").replace("https", "wss");

export default function EvolutionDashboardEnhanced() {
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
  
  // UI State
  const [darkMode, setDarkMode] = useState(true);
  const [activeTab, setActiveTab] = useState("dashboard");
  const [showLogs, setShowLogs] = useState(false);
  
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

  // Chart data preparation
  const fitnessChartData = {
    labels: fitnessHistory.map(h => `Gen ${h.generation}`),
    datasets: [
      {
        label: 'Best Fitness',
        data: fitnessHistory.map(h => h.best),
        borderColor: darkMode ? '#10b981' : '#059669',
        backgroundColor: darkMode ? 'rgba(16, 185, 129, 0.1)' : 'rgba(5, 150, 105, 0.1)',
        tension: 0.4,
        fill: true,
      },
      {
        label: 'Average Fitness',
        data: fitnessHistory.map(h => h.avg),
        borderColor: darkMode ? '#3b82f6' : '#2563eb',
        backgroundColor: darkMode ? 'rgba(59, 130, 246, 0.1)' : 'rgba(37, 99, 235, 0.1)',
        tension: 0.4,
        fill: true,
      },
    ],
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top',
        labels: {
          color: darkMode ? '#e5e7eb' : '#374151',
        },
      },
      title: {
        display: true,
        text: 'Fitness Progression Over Generations',
        color: darkMode ? '#f3f4f6' : '#111827',
        font: {
          size: 16,
          weight: 'bold',
        },
      },
    },
    scales: {
      x: {
        grid: {
          color: darkMode ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)',
        },
        ticks: {
          color: darkMode ? '#9ca3af' : '#6b7280',
        },
      },
      y: {
        grid: {
          color: darkMode ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)',
        },
        ticks: {
          color: darkMode ? '#9ca3af' : '#6b7280',
        },
      },
    },
  };

  const themeClasses = darkMode 
    ? 'bg-gray-900 text-white' 
    : 'bg-gray-50 text-gray-900';

  const cardClasses = darkMode
    ? 'bg-gray-800 border-gray-700'
    : 'bg-white border-gray-200';

  return (
    <div className={`min-h-screen ${themeClasses} transition-colors duration-300`}>
      {/* Header */}
      <header className={`${darkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'} border-b shadow-lg`}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-500 to-purple-600 bg-clip-text text-transparent">
                🧬 EvoAPI: Autonomous Architecture Engine
              </h1>
              <p className={`mt-2 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                Production-grade API architecture discovery using genetic algorithms
              </p>
            </div>
            <div className="flex items-center space-x-4">
              <button
                onClick={() => setDarkMode(!darkMode)}
                className={`p-2 rounded-lg transition-all ${
                  darkMode ? 'bg-gray-700 hover:bg-gray-600' : 'bg-gray-200 hover:bg-gray-300'
                }`}
              >
                {darkMode ? '☀️' : '🌙'}
              </button>
              <div className={`px-4 py-2 rounded-lg ${
                isConnected 
                  ? 'bg-green-500/20 text-green-500 border border-green-500/50' 
                  : 'bg-red-500/20 text-red-500 border border-red-500/50'
              }`}>
                {isConnected ? '● Connected' : '○ Disconnected'}
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Navigation Tabs */}
      <nav className={`${darkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'} border-b`}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex space-x-8">
            {[
              { id: 'dashboard', label: '📊 Dashboard', icon: '📊' },
              { id: 'configuration', label: '⚙️ Configuration', icon: '⚙️' },
              { id: 'genome', label: '🏆 Best Genome', icon: '🏆' },
              { id: 'insights', label: '💡 Insights', icon: '💡' },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`py-4 px-2 border-b-2 font-medium text-sm transition-all ${
                  activeTab === tab.id
                    ? 'border-blue-500 text-blue-500'
                    : `border-transparent ${darkMode ? 'text-gray-400 hover:text-gray-300' : 'text-gray-500 hover:text-gray-700'}`
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Dashboard Tab */}
        {activeTab === 'dashboard' && (
          <div className="space-y-6">
            {/* Stats Cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
              <div className={`${cardClasses} p-6 rounded-xl border shadow-lg`}>
                <div className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>Total Generations</div>
                <div className="text-3xl font-bold mt-2">{fitnessHistory.length}</div>
              </div>
              <div className={`${cardClasses} p-6 rounded-xl border shadow-lg`}>
                <div className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>Current Best</div>
                <div className="text-3xl font-bold mt-2 text-green-500">
                  {fitnessHistory.length > 0 ? fitnessHistory[fitnessHistory.length - 1].best.toFixed(3) : 'N/A'}
                </div>
              </div>
              <div className={`${cardClasses} p-6 rounded-xl border shadow-lg`}>
                <div className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>Population Size</div>
                <div className="text-3xl font-bold mt-2">{populationSize}</div>
              </div>
              <div className={`${cardClasses} p-6 rounded-xl border shadow-lg`}>
                <div className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>Status</div>
                <div className={`text-lg font-semibold mt-2 ${evolutionStarted ? 'text-yellow-500' : 'text-gray-500'}`}>
                  {evolutionStarted ? '🔄 Evolving' : '✓ Ready'}
                </div>
              </div>
            </div>

            {/* Fitness Chart */}
            {fitnessHistory.length > 0 && (
              <div className={`${cardClasses} p-6 rounded-xl border shadow-lg`}>
                <div className="h-96">
                  <Line data={fitnessChartData} options={chartOptions} />
                </div>
              </div>
            )}

            {/* Multi-Population Charts */}
            {eliteMode && Object.keys(groupHistory).length > 0 && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {Object.entries(groupHistory).map(([group, history]) => (
                  <div key={group} className={`${cardClasses} p-6 rounded-xl border shadow-lg`}>
                    <h3 className={`text-lg font-semibold mb-4 ${darkMode ? 'text-gray-200' : 'text-gray-800'}`}>
                      {group} Population
                    </h3>
                    <div className="h-64">
                      <Line
                        data={{
                          labels: history.map(h => `Gen ${h.generation}`),
                          datasets: [{
                            label: 'Best Fitness',
                            data: history.map(h => h.best),
                            borderColor: '#10b981',
                            backgroundColor: 'rgba(16, 185, 129, 0.1)',
                            tension: 0.4,
                            fill: true,
                          }],
                        }}
                        options={{
                          ...chartOptions,
                          plugins: { ...chartOptions.plugins, title: { display: false } },
                        }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Logs Toggle */}
            <div className="flex justify-end">
              <button
                onClick={() => setShowLogs(!showLogs)}
                className={`px-4 py-2 rounded-lg font-medium transition-all ${
                  darkMode 
                    ? 'bg-gray-700 hover:bg-gray-600 text-gray-300' 
                    : 'bg-gray-200 hover:bg-gray-300 text-gray-700'
                }`}
              >
                {showLogs ? '📝 Hide Logs' : '📝 Show Logs'}
              </button>
            </div>

            {/* Event Logs */}
            {showLogs && (
              <div className={`${cardClasses} p-6 rounded-xl border shadow-lg max-h-96 overflow-y-auto`}>
                <h3 className={`text-lg font-semibold mb-4 ${darkMode ? 'text-gray-200' : 'text-gray-800'}`}>
                  Event Log
                </h3>
                <div className="space-y-2">
                  {messages.slice(-50).map((msg, idx) => (
                    <div
                      key={idx}
                      className={`p-3 rounded-lg text-sm font-mono ${
                        msg.type === 'error' ? 'bg-red-500/20 text-red-400' :
                        msg.type === 'success' ? 'bg-green-500/20 text-green-400' :
                        msg.type === 'highlight' ? 'bg-yellow-500/20 text-yellow-400' :
                        darkMode ? 'bg-gray-700 text-gray-300' : 'bg-gray-100 text-gray-700'
                      }`}
                    >
                      <span className="opacity-50 mr-2">
                        {msg.timestamp.toLocaleTimeString()}
                      </span>
                      {msg.content}
                    </div>
                  ))}
                  <div ref={messagesEndRef} />
                </div>
              </div>
            )}
          </div>
        )}

        {/* Configuration Tab */}
        {activeTab === 'configuration' && (
          <div className={`${cardClasses} p-8 rounded-xl border shadow-lg max-w-2xl`}>
            <h2 className={`text-2xl font-bold mb-6 ${darkMode ? 'text-gray-200' : 'text-gray-800'}`}>
              ⚙️ Evolution Configuration
            </h2>

            <div className="space-y-6">
              <div>
                <label className={`block text-sm font-medium mb-2 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                  Generations
                </label>
                <input
                  type="number"
                  value={generations}
                  onChange={(e) => setGenerations(parseInt(e.target.value))}
                  min="1"
                  max="100"
                  disabled={evolutionStarted}
                  className={`w-full px-4 py-2 rounded-lg border focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                    darkMode 
                      ? 'bg-gray-700 border-gray-600 text-white' 
                      : 'bg-white border-gray-300 text-gray-900'
                  } ${evolutionStarted ? 'opacity-50 cursor-not-allowed' : ''}`}
                />
              </div>

              <div>
                <label className={`block text-sm font-medium mb-2 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                  Population Size
                </label>
                <input
                  type="number"
                  value={populationSize}
                  onChange={(e) => setPopulationSize(parseInt(e.target.value))}
                  min="4"
                  max="50"
                  disabled={evolutionStarted}
                  className={`w-full px-4 py-2 rounded-lg border focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                    darkMode 
                      ? 'bg-gray-700 border-gray-600 text-white' 
                      : 'bg-white border-gray-300 text-gray-900'
                  } ${evolutionStarted ? 'opacity-50 cursor-not-allowed' : ''}`}
                />
              </div>

              <div className="flex items-center space-x-3">
                <input
                  type="checkbox"
                  checked={useDocker}
                  onChange={(e) => setUseDocker(e.target.checked)}
                  disabled={evolutionStarted}
                  className="w-5 h-5 text-blue-500 rounded focus:ring-blue-500"
                />
                <label className={`text-sm ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                  Use Docker (build & test generated APIs)
                </label>
              </div>

              <div className={`pt-6 border-t-2 ${darkMode ? 'border-gray-700' : 'border-gray-200'}`}>
                <div className="flex items-center space-x-3 mb-4">
                  <input
                    type="checkbox"
                    checked={eliteMode}
                    onChange={(e) => setEliteMode(e.target.checked)}
                    disabled={evolutionStarted}
                    className="w-5 h-5 text-purple-500 rounded focus:ring-purple-500"
                  />
                  <label className={`text-sm font-bold text-purple-500`}>
                    🧠 Elite Mode (Multi-population + Adaptive Learning)
                  </label>
                </div>

                {eliteMode && (
                  <div className="space-y-3 ml-8">
                    <div className="flex items-center space-x-3">
                      <input
                        type="checkbox"
                        checked={useMultiPopulation}
                        onChange={(e) => setUseMultiPopulation(e.target.checked)}
                        disabled={evolutionStarted}
                        className="w-5 h-5 text-blue-500 rounded focus:ring-blue-500"
                      />
                      <label className={`text-sm ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                        Multi-Population System (4 specialized groups)
                      </label>
                    </div>

                    <div className="flex items-center space-x-3">
                      <input
                        type="checkbox"
                        checked={enableAdaptiveMutation}
                        onChange={(e) => setEnableAdaptiveMutation(e.target.checked)}
                        disabled={evolutionStarted}
                        className="w-5 h-5 text-blue-500 rounded focus:ring-blue-500"
                      />
                      <label className={`text-sm ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                        Adaptive Mutation (learns from success)
                      </label>
                    </div>
                  </div>
                )}
              </div>

              <div className="flex flex-wrap gap-4 pt-4">
                <button
                  onClick={eliteMode ? startEliteEvolution : startEvolution}
                  disabled={evolutionStarted || !isConnected}
                  className={`flex-1 px-6 py-3 rounded-lg font-semibold text-white transition-all transform hover:scale-105 ${
                    eliteMode
                      ? 'bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700'
                      : 'bg-gradient-to-r from-blue-600 to-green-600 hover:from-blue-700 hover:to-green-700'
                  } ${(evolutionStarted || !isConnected) ? 'opacity-50 cursor-not-allowed' : 'shadow-lg'}`}
                >
                  {evolutionStarted ? 'Evolving...' : eliteMode ? '🧬 Start Elite Evolution' : '🚀 Start Evolution'}
                </button>

                <button
                  onClick={runSyncEvolution}
                  disabled={evolutionStarted || !isConnected}
                  className={`px-6 py-3 rounded-lg font-semibold transition-all ${
                    darkMode
                      ? 'bg-gray-700 hover:bg-gray-600 text-gray-300'
                      : 'bg-gray-200 hover:bg-gray-300 text-gray-700'
                  } ${(evolutionStarted || !isConnected) ? 'opacity-50 cursor-not-allowed' : ''}`}
                >
                  ⚡ Quick Test
                </button>

                {eliteMode && (
                  <button
                    onClick={loadInsights}
                    disabled={!isConnected}
                    className={`px-6 py-3 rounded-lg font-semibold text-white transition-all ${
                      !isConnected ? 'opacity-50 cursor-not-allowed' : 'hover:scale-105'
                    } bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 shadow-lg`}
                  >
                    📊 Load Insights
                  </button>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Best Genome Tab */}
        {activeTab === 'genome' && (
          <div className={`${cardClasses} p-8 rounded-xl border shadow-lg`}>
            <h2 className={`text-2xl font-bold mb-6 ${darkMode ? 'text-gray-200' : 'text-gray-800'}`}>
              🏆 Best Genome Found
            </h2>
            
            {bestGenome ? (
              <div className="space-y-4">
                <div className={`p-4 rounded-lg ${darkMode ? 'bg-green-500/20 border border-green-500/50' : 'bg-green-50 border border-green-200'}`}>
                  <div className={`text-sm ${darkMode ? 'text-green-400' : 'text-green-700'}`}>Fitness Score</div>
                  <div className="text-4xl font-bold text-green-500 mt-1">
                    {bestGenome.fitness?.toFixed(3) || 'N/A'}
                  </div>
                </div>
                
                <pre className={`p-6 rounded-lg overflow-x-auto text-sm font-mono ${
                  darkMode ? 'bg-gray-900 text-green-400' : 'bg-gray-100 text-gray-800'
                }`}>
                  {JSON.stringify(bestGenome, null, 2)}
                </pre>
              </div>
            ) : (
              <div className={`text-center py-12 ${darkMode ? 'text-gray-500' : 'text-gray-400'}`}>
                <div className="text-6xl mb-4">🧬</div>
                <p className="text-lg">No genome evolved yet. Start an evolution run to discover optimal architectures!</p>
              </div>
            )}
          </div>
        )}

        {/* Insights Tab */}
        {activeTab === 'insights' && (
          <div className={`${cardClasses} p-8 rounded-xl border shadow-lg`}>
            <h2 className={`text-2xl font-bold mb-6 ${darkMode ? 'text-gray-200' : 'text-gray-800'}`}>
              💡 Evolution Insights
            </h2>
            
            {insights ? (
              <div className="space-y-6">
                {Object.entries(insights).map(([key, value]) => (
                  <div key={key} className={`p-4 rounded-lg ${darkMode ? 'bg-gray-700' : 'bg-gray-100'}`}>
                    <h3 className={`font-semibold mb-2 capitalize ${darkMode ? 'text-blue-400' : 'text-blue-600'}`}>
                      {key.replace(/_/g, ' ')}
                    </h3>
                    <pre className={`text-sm overflow-x-auto ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                      {typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value)}
                    </pre>
                  </div>
                ))}
              </div>
            ) : (
              <div className={`text-center py-12 ${darkMode ? 'text-gray-500' : 'text-gray-400'}`}>
                <div className="text-6xl mb-4">💡</div>
                <p className="text-lg">Complete an elite evolution run to see insights about successful patterns!</p>
                <button
                  onClick={loadInsights}
                  className="mt-4 px-6 py-3 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-semibold transition-all"
                >
                  Load Latest Insights
                </button>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
