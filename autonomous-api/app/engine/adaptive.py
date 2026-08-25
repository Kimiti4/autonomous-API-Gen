import random
from typing import Dict, Any
from app.core.logger import logger


class AdaptiveMutator:
    """
    Adaptive mutation system that learns which mutations lead to success.
    Adjusts mutation probabilities based on historical performance.
    """
    
    def __init__(self):
        # Success bias for different features (starts neutral at 0.5)
        self.success_bias = {
            "cache_enabled": 0.5,
            "rate_limiting": 0.5,
            "cors_enabled": 0.5,
            "auth_jwt": 0.5,
            "auth_oauth2": 0.5,
            "auth_api_key": 0.3,
            "auth_basic": 0.2,
            "database_postgres": 0.6,
            "database_mysql": 0.5,
            "database_sqlite": 0.3,
            "logging_INFO": 0.6,
            "logging_WARNING": 0.5,
            "logging_DEBUG": 0.4,
            "logging_ERROR": 0.3
        }
        
        # Track mutation history
        self.mutation_history = []
        self.learning_rate = 0.1
    
    def update(self, genome_data: Dict[str, Any], score: float):
        """
        Update success bias based on genome performance.
        Higher scores increase bias for that genome's features.
        """
        if score < 0.3:
            # Poor performance - decrease bias for these features
            adjustment = -self.learning_rate
        elif score > 0.7:
            # Good performance - increase bias for these features
            adjustment = self.learning_rate
        else:
            # Average performance - minimal adjustment
            adjustment = 0.0
        
        # Update biases based on genome features
        if genome_data.get("cache_enabled"):
            self._adjust_bias("cache_enabled", adjustment)
        
        if genome_data.get("rate_limiting"):
            self._adjust_bias("rate_limiting", adjustment)
        
        if genome_data.get("cors_enabled"):
            self._adjust_bias("cors_enabled", adjustment)
        
        # Auth method bias
        auth = genome_data.get("auth", "jwt")
        self._adjust_bias(f"auth_{auth}", adjustment)
        
        # Database bias
        database = genome_data.get("database", "postgres")
        self._adjust_bias(f"database_{database}", adjustment)
        
        # Logging level bias
        logging_level = genome_data.get("logging_level", "INFO")
        self._adjust_bias(f"logging_{logging_level}", adjustment)
        
        # Record mutation
        self.mutation_history.append({
            "genome": genome_data,
            "score": score,
            "adjustment": adjustment
        })
        
        # Keep history manageable
        if len(self.mutation_history) > 1000:
            self.mutation_history = self.mutation_history[-1000:]
    
    def _adjust_bias(self, key: str, adjustment: float):
        """Adjust a specific bias value, keeping it in [0.1, 0.9] range"""
        if key in self.success_bias:
            old_value = self.success_bias[key]
            new_value = old_value + adjustment
            # Clamp to valid range
            self.success_bias[key] = max(0.1, min(0.9, new_value))
    
    def mutate(self, genome_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply adaptive mutation to genome.
        Uses learned biases to guide mutation decisions.
        """
        mutated = genome_data.copy()
        
        # Mutate cache setting with adaptive probability
        if random.random() < 0.2:  # Base mutation rate
            # Use bias to decide whether to enable or disable
            if self.success_bias["cache_enabled"] > 0.5:
                mutated["cache_enabled"] = True  # Bias towards enabling
            else:
                mutated["cache_enabled"] = not mutated.get("cache_enabled", False)
        
        # Mutate rate limiting
        if random.random() < 0.2:
            if self.success_bias["rate_limiting"] > 0.5:
                mutated["rate_limiting"] = True
            else:
                mutated["rate_limiting"] = not mutated.get("rate_limiting", False)
        
        # Mutate CORS
        if random.random() < 0.15:
            if self.success_bias["cors_enabled"] > 0.5:
                mutated["cors_enabled"] = True
            else:
                mutated["cors_enabled"] = not mutated.get("cors_enabled", False)
        
        # Mutate auth method with bias
        if random.random() < 0.25:
            auth_options = ["jwt", "oauth2", "api_key", "basic"]
            # Weight selection by bias
            weights = [
                self.success_bias["auth_jwt"],
                self.success_bias["auth_oauth2"],
                self.success_bias["auth_api_key"],
                self.success_bias["auth_basic"]
            ]
            total_weight = sum(weights)
            normalized_weights = [w / total_weight for w in weights]
            mutated["auth"] = random.choices(auth_options, weights=normalized_weights, k=1)[0]
        
        # Mutate database with bias
        if random.random() < 0.2:
            db_options = ["postgres", "mysql", "sqlite"]
            weights = [
                self.success_bias["database_postgres"],
                self.success_bias["database_mysql"],
                self.success_bias["database_sqlite"]
            ]
            total_weight = sum(weights)
            normalized_weights = [w / total_weight for w in weights]
            mutated["database"] = random.choices(db_options, weights=normalized_weights, k=1)[0]
        
        # Mutate logging level with bias
        if random.random() < 0.15:
            log_options = ["DEBUG", "INFO", "WARNING", "ERROR"]
            weights = [
                self.success_bias["logging_DEBUG"],
                self.success_bias["logging_INFO"],
                self.success_bias["logging_WARNING"],
                self.success_bias["logging_ERROR"]
            ]
            total_weight = sum(weights)
            normalized_weights = [w / total_weight for w in weights]
            mutated["logging_level"] = random.choices(log_options, weights=normalized_weights, k=1)[0]
        
        return mutated
    
    def get_bias_report(self) -> Dict[str, float]:
        """Get current mutation bias values"""
        return self.success_bias.copy()
    
    def get_top_features(self, n: int = 5) -> list:
        """Get top N most favored features"""
        sorted_biases = sorted(
            self.success_bias.items(),
            key=lambda x: x[1],
            reverse=True
        )
        return sorted_biases[:n]
    
    def reset(self):
        """Reset all biases to neutral"""
        for key in self.success_bias:
            self.success_bias[key] = 0.5
        self.mutation_history.clear()
        logger.info("Adaptive mutator reset to neutral")
