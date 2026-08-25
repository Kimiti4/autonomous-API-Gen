import json
import os
from typing import List, Dict, Any
from datetime import datetime
from app.core.logger import logger


class EvolutionMemory:
    """
    Persistent memory system that learns from evolution runs.
    Tracks best/worst genomes and identifies successful patterns.
    """
    
    def __init__(self, path: str = "data/memory.json"):
        self.path = path
        self.data = {
            "best_genomes": [],
            "worst_genomes": [],
            "successful_patterns": {},
            "failed_patterns": {},
            "run_history": [],
            "statistics": {
                "total_runs": 0,
                "avg_best_fitness": 0.0,
                "improvement_trend": []
            }
        }
        
        # Load existing memory if available
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    loaded_data = json.load(f)
                    self.data.update(loaded_data)
                    logger.info(f"Loaded memory from {path}")
            except Exception as e:
                logger.warning(f"Failed to load memory: {e}, starting fresh")
    
    def record_run(self, best_genome: Dict[str, Any], best_score: float, 
                   worst_score: float, generation: int, run_id: str):
        """Record a complete evolution run"""
        
        entry = {
            "run_id": run_id,
            "timestamp": datetime.utcnow().isoformat(),
            "best_genome": best_genome,
            "best_score": best_score,
            "worst_score": worst_score,
            "generation": generation
        }
        
        self.data["run_history"].append(entry)
        self.data["statistics"]["total_runs"] += 1
        
        # Track best genomes (keep top 20)
        if len(self.data["best_genomes"]) < 20 or best_score > self.data["best_genomes"][-1]["score"]:
            self.data["best_genomes"].append({
                "genome": best_genome,
                "score": best_score,
                "timestamp": entry["timestamp"]
            })
            self.data["best_genomes"].sort(key=lambda x: x["score"], reverse=True)
            self.data["best_genomes"] = self.data["best_genomes"][:20]
        
        # Update statistics
        self._update_statistics(best_score)
        
        # Extract patterns
        self._extract_patterns(best_genome, best_score)
        
        self._save()
        logger.info(f"Recorded run {run_id}: best_score={best_score:.3f}")
    
    def _update_statistics(self, best_score: float):
        """Update running statistics"""
        total = self.data["statistics"]["total_runs"]
        current_avg = self.data["statistics"]["avg_best_fitness"]
        
        # Running average
        new_avg = ((current_avg * (total - 1)) + best_score) / total
        self.data["statistics"]["avg_best_fitness"] = new_avg
        
        # Track trend
        self.data["statistics"]["improvement_trend"].append(best_score)
        if len(self.data["statistics"]["improvement_trend"]) > 100:
            self.data["statistics"]["improvement_trend"] = \
                self.data["statistics"]["improvement_trend"][-100:]
    
    def _extract_patterns(self, genome: Dict[str, Any], score: float):
        """Extract successful/failed patterns from genome"""
        
        # Define pattern keys
        patterns = {
            "auth_method": genome.get("auth", "unknown"),
            "database": genome.get("database", "unknown"),
            "has_cache": genome.get("cache_enabled", False),
            "has_rate_limiting": genome.get("rate_limiting", False),
            "has_cors": genome.get("cors_enabled", False),
            "logging_level": genome.get("logging_level", "INFO"),
            "num_services": len(genome.get("services", []))
        }
        
        # Determine if this is a successful pattern (score > 0.7)
        is_successful = score > 0.7
        
        target_dict = self.data["successful_patterns"] if is_successful else self.data["failed_patterns"]
        
        for key, value in patterns.items():
            if key not in target_dict:
                target_dict[key] = {}
            
            value_key = str(value)
            if value_key not in target_dict[key]:
                target_dict[key][value_key] = {"count": 0, "avg_score": 0.0}
            
            # Update count and running average
            entry = target_dict[key][value_key]
            entry["count"] += 1
            entry["avg_score"] = ((entry["avg_score"] * (entry["count"] - 1)) + score) / entry["count"]
    
    def get_best_patterns(self, top_n: int = 5) -> List[Dict[str, Any]]:
        """Get top N best performing genome patterns"""
        return self.data["best_genomes"][:top_n]
    
    def get_pattern_insights(self) -> Dict[str, Any]:
        """Get insights about which patterns perform best"""
        insights = {
            "best_auth": None,
            "best_database": None,
            "cache_impact": 0.0,
            "rate_limiting_impact": 0.0
        }
        
        if "auth_method" in self.data["successful_patterns"]:
            auth_patterns = self.data["successful_patterns"]["auth_method"]
            if auth_patterns:
                best_auth = max(auth_patterns.items(), key=lambda x: x[1]["avg_score"])
                insights["best_auth"] = {
                    "method": best_auth[0],
                    "avg_score": best_auth[1]["avg_score"],
                    "occurrences": best_auth[1]["count"]
                }
        
        if "database" in self.data["successful_patterns"]:
            db_patterns = self.data["successful_patterns"]["database"]
            if db_patterns:
                best_db = max(db_patterns.items(), key=lambda x: x[1]["avg_score"])
                insights["best_database"] = {
                    "type": best_db[0],
                    "avg_score": best_db[1]["avg_score"],
                    "occurrences": best_db[1]["count"]
                }
        
        # Calculate feature impacts
        if "has_cache" in self.data["successful_patterns"]:
            cache_data = self.data["successful_patterns"]["has_cache"]
            with_cache = cache_data.get("True", {"avg_score": 0})["avg_score"]
            without_cache = cache_data.get("False", {"avg_score": 0})["avg_score"]
            insights["cache_impact"] = with_cache - without_cache
        
        if "has_rate_limiting" in self.data["successful_patterns"]:
            rl_data = self.data["successful_patterns"]["has_rate_limiting"]
            with_rl = rl_data.get("True", {"avg_score": 0})["avg_score"]
            without_rl = rl_data.get("False", {"avg_score": 0})["avg_score"]
            insights["rate_limiting_impact"] = with_rl - without_rl
        
        return insights
    
    def get_suggested_genome(self) -> Dict[str, Any]:
        """Generate a genome suggestion based on learned patterns"""
        insights = self.get_pattern_insights()
        
        suggested = {
            "auth": "jwt",  # Default
            "database": "postgres",  # Default
            "cache_enabled": True,
            "rate_limiting": True,
            "cors_enabled": True,
            "logging_level": "INFO",
            "api_version": "v2"
        }
        
        # Apply learned preferences
        if insights["best_auth"]:
            suggested["auth"] = insights["best_auth"]["method"]
        
        if insights["best_database"]:
            suggested["database"] = insights["best_database"]["type"]
        
        # If cache has positive impact, enable it
        if insights["cache_impact"] > 0.05:
            suggested["cache_enabled"] = True
        
        # If rate limiting has positive impact, enable it
        if insights["rate_limiting_impact"] > 0.05:
            suggested["rate_limiting"] = True
        
        return suggested
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get overall memory statistics"""
        return {
            **self.data["statistics"],
            "best_genomes_count": len(self.data["best_genomes"]),
            "pattern_insights": self.get_pattern_insights()
        }
    
    def _save(self):
        """Save memory to disk"""
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, "w") as f:
                json.dump(self.data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save memory: {e}")
    
    def clear(self):
        """Clear all memory"""
        self.data = {
            "best_genomes": [],
            "worst_genomes": [],
            "successful_patterns": {},
            "failed_patterns": {},
            "run_history": [],
            "statistics": {
                "total_runs": 0,
                "avg_best_fitness": 0.0,
                "improvement_trend": []
            }
        }
        self._save()
        logger.info("Memory cleared")
