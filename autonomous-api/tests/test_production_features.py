"""
Comprehensive unit tests for production hardening features.
Tests validation, rate limiting, security headers, error handling, and health checks.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.schemas.evolution import EvolutionRequest, EliteEvolutionRequest
from app.core.error_handler import AppError, EvolutionError, retry_with_backoff
from app.middleware.rate_limit import RateLimiter
import asyncio


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def rate_limiter():
    """Create rate limiter for testing"""
    return RateLimiter(max_requests=5, window_seconds=60)


# ==================== VALIDATION TESTS ====================

class TestInputValidation:
    """Test Pydantic input validation"""
    
    def test_valid_evolution_request(self):
        """Test valid evolution request passes validation"""
        request = EvolutionRequest(
            generations=10,
            population_size=10,
            use_docker=False
        )
        assert request.generations == 10
        assert request.population_size == 10
        assert request.use_docker is False
    
    def test_invalid_generations_too_high(self):
        """Test generations > 100 raises validation error"""
        with pytest.raises(ValueError):
            EvolutionRequest(generations=200, population_size=10)
    
    def test_invalid_generations_too_low(self):
        """Test generations < 1 raises validation error"""
        with pytest.raises(ValueError):
            EvolutionRequest(generations=0, population_size=10)
    
    def test_invalid_population_size_too_small(self):
        """Test population_size < 4 raises validation error"""
        with pytest.raises(ValueError):
            EvolutionRequest(generations=5, population_size=2)
    
    def test_invalid_population_size_too_large(self):
        """Test population_size > 50 raises validation error"""
        with pytest.raises(ValueError):
            EvolutionRequest(generations=5, population_size=100)
    
    def test_elite_evolution_request(self):
        """Test elite evolution request with all fields"""
        request = EliteEvolutionRequest(
            generations=10,
            population_size=8,
            use_multi_population=True,
            enable_adaptive_mutation=True,
            use_docker=False
        )
        assert request.use_multi_population is True
        assert request.enable_adaptive_mutation is True


# ==================== HEALTH CHECK TESTS ====================

class TestHealthCheck:
    """Test health check endpoint"""
    
    def test_health_check_returns_200(self, client):
        """Test health check endpoint returns 200 OK"""
        response = client.get("/health")
        assert response.status_code == 200
    
    def test_health_check_has_required_fields(self, client):
        """Test health check response has all required fields"""
        response = client.get("/health")
        data = response.json()
        
        assert "status" in data
        assert "version" in data
        assert "timestamp" in data
        assert "components" in data
    
    def test_health_check_components(self, client):
        """Test health check reports component status"""
        response = client.get("/health")
        data = response.json()
        
        assert "database" in data["components"]
        assert "memory" in data["components"]
        assert "disk" in data["components"]
    
    def test_health_check_memory_usage(self, client):
        """Test health check includes memory usage"""
        response = client.get("/health")
        data = response.json()
        
        if data.get("memory_usage"):
            assert "rss_mb" in data["memory_usage"]
            assert "vms_mb" in data["memory_usage"]
            assert "percent" in data["memory_usage"]


# ==================== SECURITY HEADERS TESTS ====================

class TestSecurityHeaders:
    """Test security headers are present"""
    
    def test_x_content_type_options(self, client):
        """Test X-Content-Type-Options header"""
        response = client.get("/")
        assert response.headers["X-Content-Type-Options"] == "nosniff"
    
    def test_x_frame_options(self, client):
        """Test X-Frame-Options header"""
        response = client.get("/")
        assert response.headers["X-Frame-Options"] == "DENY"
    
    def test_x_xss_protection(self, client):
        """Test X-XSS-Protection header"""
        response = client.get("/")
        assert response.headers["X-XSS-Protection"] == "1; mode=block"
    
    def test_strict_transport_security(self, client):
        """Test Strict-Transport-Security header"""
        response = client.get("/")
        assert "Strict-Transport-Security" in response.headers
    
    def test_content_security_policy(self, client):
        """Test Content-Security-Policy header"""
        response = client.get("/")
        assert "Content-Security-Policy" in response.headers
    
    def test_cache_control(self, client):
        """Test Cache-Control header"""
        response = client.get("/")
        assert response.headers["Cache-Control"] == "no-store, no-cache, must-revalidate"
    
    def test_server_header_removed(self, client):
        """Test server header is removed"""
        response = client.get("/")
        assert "server" not in response.headers


# ==================== RATE LIMITING TESTS ====================

class TestRateLimiting:
    """Test rate limiting functionality"""
    
    def test_rate_limiter_allows_within_limit(self, rate_limiter):
        """Test requests within limit are allowed"""
        for i in range(5):
            limited, info = rate_limiter.is_rate_limited("127.0.0.1")
            assert limited is False
    
    def test_rate_limiter_blocks_over_limit(self, rate_limiter):
        """Test requests over limit are blocked"""
        # Use up all allowed requests
        for i in range(5):
            rate_limiter.is_rate_limited("127.0.0.1")
        
        # Next request should be blocked
        limited, info = rate_limiter.is_rate_limited("127.0.0.1")
        assert limited is True
        assert "retry_after" in info
    
    def test_rate_limiter_different_ips(self, rate_limiter):
        """Test rate limiting is per-IP"""
        # IP1 uses all requests
        for i in range(5):
            rate_limiter.is_rate_limited("192.168.1.1")
        
        # IP2 should still be allowed
        limited, info = rate_limiter.is_rate_limited("192.168.1.2")
        assert limited is False
    
    def test_rate_limiter_cleanup(self, rate_limiter):
        """Test stale entries are cleaned up"""
        # Add some requests
        rate_limiter.is_rate_limited("10.0.0.1")
        
        # Manually trigger cleanup
        rate_limiter._cleanup_stale_entries()
        
        # Should still work
        limited, _ = rate_limiter.is_rate_limited("10.0.0.1")
        assert limited is False


# ==================== ERROR HANDLING TESTS ====================

class TestErrorHandling:
    """Test error handling utilities"""
    
    def test_app_error_creation(self):
        """Test AppError can be created"""
        error = AppError("Test error", "test_code", {"detail": "test"})
        assert error.message == "Test error"
        assert error.error_code == "test_code"
        assert error.details == {"detail": "test"}
    
    def test_evolution_error(self):
        """Test EvolutionError inherits from AppError"""
        error = EvolutionError("Evolution failed", {"gen": 5})
        assert isinstance(error, AppError)
        assert error.error_code == "evolution_error"
    
    @pytest.mark.asyncio
    async def test_retry_with_backoff_success(self):
        """Test retry succeeds on first try"""
        call_count = 0
        
        async def successful_func():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = await retry_with_backoff(
            func=successful_func,
            max_retries=3,
            base_delay=0.1,
            operation_name="test"
        )
        
        assert result == "success"
        assert call_count == 1
    
    @pytest.mark.asyncio
    async def test_retry_with_backoff_retries(self):
        """Test retry attempts multiple times before failing"""
        call_count = 0
        
        async def failing_func():
            nonlocal call_count
            call_count += 1
            raise Exception("Temporary failure")
        
        with pytest.raises(Exception):
            await retry_with_backoff(
                func=failing_func,
                max_retries=3,
                base_delay=0.01,  # Fast for testing
                operation_name="test"
            )
        
        assert call_count == 4  # Initial + 3 retries


# ==================== API ENDPOINT TESTS ====================

class TestAPIEndpoints:
    """Test API endpoints"""
    
    def test_root_endpoint(self, client):
        """Test root endpoint returns welcome message"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Autonomous Evolution Engine" in data["message"]
    
    def test_docs_endpoint_accessible(self, client):
        """Test Swagger docs are accessible"""
        response = client.get("/docs")
        assert response.status_code == 200
    
    def test_openapi_json_accessible(self, client):
        """Test OpenAPI schema is accessible"""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "info" in data
    
    def test_evolve_start_validation_error(self, client):
        """Test evolution endpoint validates input"""
        response = client.post(
            "/evolve/start",
            json={"generations": 200, "population_size": 10}  # Invalid
        )
        assert response.status_code == 422  # Validation error
    
    def test_elite_start_validation_error(self, client):
        """Test elite evolution endpoint validates input"""
        response = client.post(
            "/evolve/elite/start",
            json={"generations": 0, "population_size": 2}  # Invalid
        )
        assert response.status_code == 422  # Validation error


# ==================== CONFIGURATION TESTS ====================

class TestConfiguration:
    """Test configuration management"""
    
    def test_settings_loaded(self):
        """Test settings can be loaded"""
        from app.core.config import get_settings
        settings = get_settings()
        
        assert settings.APP_NAME is not None
        assert settings.APP_VERSION is not None
        assert settings.DATABASE_URL is not None
    
    def test_default_values(self):
        """Test default configuration values"""
        from app.core.config import get_settings
        settings = get_settings()
        
        assert settings.DEBUG is False
        assert settings.LOG_LEVEL == "INFO"
        assert settings.RATE_LIMIT_EVOLUTION == 20


# ==================== LOGGER TESTS ====================

class TestLogger:
    """Test logging configuration"""
    
    def test_logger_importable(self):
        """Test logger can be imported"""
        from app.core.logger import logger
        assert logger is not None
    
    def test_logger_has_methods(self):
        """Test logger has standard methods"""
        from app.core.logger import logger
        
        assert hasattr(logger, "info")
        assert hasattr(logger, "warning")
        assert hasattr(logger, "error")
        assert hasattr(logger, "debug")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
