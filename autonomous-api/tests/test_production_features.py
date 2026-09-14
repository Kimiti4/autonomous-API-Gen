"""Production-hardening tests for validation, security, rate limiting, and errors."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.evolution import EvolutionRequest, EliteEvolutionRequest
from app.core.error_handler import AppError, EvolutionError, retry_with_backoff
from app.middleware.rate_limit import RateLimiter


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def rate_limiter():
    return RateLimiter(max_requests=5, window_seconds=60)


class TestInputValidation:
    def test_valid_evolution_request(self):
        request = EvolutionRequest(generations=10, population_size=10, use_docker=False)
        assert request.generations == 10
        assert request.population_size == 10
        assert request.use_docker is False

    def test_invalid_generations_too_high(self):
        with pytest.raises(ValueError):
            EvolutionRequest(generations=200, population_size=10)

    def test_invalid_generations_too_low(self):
        with pytest.raises(ValueError):
            EvolutionRequest(generations=0, population_size=10)

    def test_invalid_population_size_too_small(self):
        with pytest.raises(ValueError):
            EvolutionRequest(generations=5, population_size=2)

    def test_invalid_population_size_too_large(self):
        with pytest.raises(ValueError):
            EvolutionRequest(generations=5, population_size=100)

    def test_elite_evolution_request(self):
        request = EliteEvolutionRequest(
            generations=10,
            population_size=8,
            use_multi_population=True,
            enable_adaptive_mutation=True,
            use_docker=False,
        )
        assert request.use_multi_population is True
        assert request.enable_adaptive_mutation is True


class TestHealthCheck:
    def test_health_check_returns_200(self, client):
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_check_has_required_fields(self, client):
        data = client.get("/health").json()
        assert {"status", "version", "timestamp", "components"}.issubset(data)

    def test_health_check_components(self, client):
        data = client.get("/health").json()
        assert {"database", "memory", "disk"}.issubset(data["components"])

    def test_health_check_memory_usage(self, client):
        data = client.get("/health").json()
        if data.get("memory_usage"):
            assert {"rss_mb", "vms_mb", "percent"}.issubset(data["memory_usage"])


class TestSecurityHeaders:
    def test_x_content_type_options(self, client):
        assert client.get("/").headers["X-Content-Type-Options"] == "nosniff"

    def test_x_frame_options(self, client):
        assert client.get("/").headers["X-Frame-Options"] == "DENY"

    def test_x_xss_protection(self, client):
        assert client.get("/").headers["X-XSS-Protection"] == "1; mode=block"

    def test_strict_transport_security(self, client):
        assert "Strict-Transport-Security" in client.get("/").headers

    def test_content_security_policy(self, client):
        assert "Content-Security-Policy" in client.get("/").headers

    def test_cache_control(self, client):
        assert client.get("/").headers["Cache-Control"] == "no-store, no-cache, must-revalidate"

    def test_server_header_removed(self, client):
        assert "server" not in client.get("/").headers


class TestRateLimiting:
    def test_rate_limiter_allows_within_limit(self, rate_limiter):
        for _ in range(5):
            limited, _ = rate_limiter.is_rate_limited("127.0.0.1")
            assert limited is False

    def test_rate_limiter_blocks_over_limit(self, rate_limiter):
        for _ in range(5):
            rate_limiter.is_rate_limited("127.0.0.1")
        limited, info = rate_limiter.is_rate_limited("127.0.0.1")
        assert limited is True
        assert "retry_after" in info

    def test_rate_limiter_different_ips(self, rate_limiter):
        for _ in range(5):
            rate_limiter.is_rate_limited("192.168.1.1")
        limited, _ = rate_limiter.is_rate_limited("192.168.1.2")
        assert limited is False

    def test_rate_limiter_cleanup(self, rate_limiter):
        rate_limiter.is_rate_limited("10.0.0.1")
        rate_limiter._cleanup_stale_entries()
        limited, _ = rate_limiter.is_rate_limited("10.0.0.1")
        assert limited is False


class TestErrorHandling:
    def test_app_error_creation(self):
        error = AppError("Test error", "test_code", {"detail": "test"})
        assert error.message == "Test error"
        assert error.error_code == "test_code"
        assert error.details == {"detail": "test"}

    def test_evolution_error(self):
        error = EvolutionError("Evolution failed", {"gen": 5})
        assert isinstance(error, AppError)
        assert error.error_code == "evolution_error"

    @pytest.mark.asyncio
    async def test_retry_with_backoff_success(self):
        call_count = 0

        async def successful_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await retry_with_backoff(
            func=successful_func,
            max_retries=3,
            base_delay=0.1,
            operation_name="test",
        )
        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_with_backoff_retries(self):
        call_count = 0

        async def failing_func():
            nonlocal call_count
            call_count += 1
            raise Exception("Temporary failure")

        with pytest.raises(Exception):
            await retry_with_backoff(
                func=failing_func,
                max_retries=3,
                base_delay=0.01,
                operation_name="test",
            )
        assert call_count == 4


class TestAPIEndpoints:
    def test_root_endpoint(self, client):
        response = client.get("/")
        assert response.status_code == 200
        assert "Autonomous Evolution Engine" in response.json()["message"]

    def test_docs_endpoint_accessible(self, client):
        assert client.get("/docs").status_code == 200

    def test_openapi_json_accessible(self, client):
        response = client.get("/openapi.json")
        assert response.status_code == 200
        assert "info" in response.json()

    def test_evolve_start_is_protected(self, client):
        response = client.post(
            "/evolve/start",
            json={"generations": 200, "population_size": 10},
        )
        assert response.status_code == 401

    def test_elite_start_is_protected(self, client):
        response = client.post(
            "/evolve/elite/start",
            json={"generations": 0, "population_size": 2},
        )
        assert response.status_code == 401


class TestConfiguration:
    def test_settings_loaded(self):
        from app.core.config import get_settings

        settings = get_settings()
        assert settings.APP_NAME is not None
        assert settings.APP_VERSION is not None
        assert settings.DATABASE_URL is not None

    def test_default_values(self):
        from app.core.config import get_settings

        settings = get_settings()
        assert settings.DEBUG is False
        assert settings.LOG_LEVEL == "INFO"
        assert settings.RATE_LIMIT_EVOLUTION == 20


class TestLogger:
    def test_logger_importable(self):
        from app.core.logger import logger

        assert logger is not None

    def test_logger_has_methods(self):
        from app.core.logger import logger

        assert all(hasattr(logger, method) for method in ("info", "warning", "error", "debug"))
