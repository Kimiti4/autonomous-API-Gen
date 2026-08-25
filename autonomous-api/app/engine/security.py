from app.engine.genome import Genome


def calculate_security_score(genome: Genome) -> float:
    """
    Calculate security score based on genome configuration.
    Returns a score between 0.0 (insecure) and 1.0 (secure).
    """
    score = 1.0
    
    # Auth method scoring
    auth_scores = {
        "jwt": 0.0,      # No penalty - JWT is secure
        "oauth2": 0.0,   # No penalty - OAuth2 is secure
        "api_key": -0.2, # Slight penalty
        "basic": -0.6    # Heavy penalty for basic auth
    }
    score += auth_scores.get(genome.auth, -0.3)
    
    # Critical services require strong auth
    critical_services = ["payments", "admin", "users"]
    has_critical = any(s in genome.services for s in critical_services)
    
    if has_critical and genome.auth in ["basic", "api_key"]:
        score -= 0.4  # Penalize weak auth for critical services
    
    # Rate limiting bonus
    if genome.rate_limiting:
        score += 0.1
    
    # CORS configuration
    if not genome.cors_enabled:
        score -= 0.1  # Missing CORS can be a security issue
    
    # Ensure score stays in valid range
    return max(0.0, min(1.0, score))
