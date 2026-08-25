"""
Comprehensive error handling utilities with retry logic.
Provides standardized error responses and resilient operations.
"""

import asyncio
import time
import uuid
from typing import Callable, TypeVar, Optional, Any
from functools import wraps
from app.core.logger import logger
from app.schemas.evolution import ErrorResponse


T = TypeVar('T')


class AppError(Exception):
    """Base application error"""
    def __init__(self, message: str, error_code: str = "app_error", details: Any = None):
        self.message = message
        self.error_code = error_code
        self.details = details
        super().__init__(self.message)


class EvolutionError(AppError):
    """Evolution-specific errors"""
    def __init__(self, message: str, details: Any = None):
        super().__init__(message, "evolution_error", details)


class DockerError(AppError):
    """Docker operation errors"""
    def __init__(self, message: str, details: Any = None):
        super().__init__(message, "docker_error", details)


class DatabaseError(AppError):
    """Database operation errors"""
    def __init__(self, message: str, details: Any = None):
        super().__init__(message, "database_error", details)


class ValidationError(AppError):
    """Input validation errors"""
    def __init__(self, message: str, field_errors: list = None):
        super().__init__(message, "validation_error", {"field_errors": field_errors or []})


async def retry_with_backoff(
    func: Callable,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 10.0,
    exponential_base: float = 2.0,
    retryable_exceptions: tuple = (Exception,),
    operation_name: str = "operation"
) -> Any:
    """
    Execute a function with exponential backoff retry logic.
    
    Args:
        func: Async function to execute
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay between retries (seconds)
        max_delay: Maximum delay between retries (seconds)
        exponential_base: Base for exponential backoff calculation
        retryable_exceptions: Tuple of exceptions that trigger retry
        operation_name: Name of operation for logging
    
    Returns:
        Result from successful function execution
    
    Raises:
        Last exception if all retries exhausted
    """
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            result = await func()
            
            if attempt > 0:
                logger.info(f"{operation_name} succeeded after {attempt} retries")
            
            return result
            
        except retryable_exceptions as e:
            last_exception = e
            
            if attempt < max_retries:
                # Calculate delay with exponential backoff and jitter
                delay = min(base_delay * (exponential_base ** attempt), max_delay)
                jitter = delay * 0.1 * (hash(str(time.time())) % 100) / 100
                final_delay = delay + jitter
                
                logger.warning(
                    f"{operation_name} failed (attempt {attempt + 1}/{max_retries + 1}): {str(e)}. "
                    f"Retrying in {final_delay:.2f}s..."
                )
                
                await asyncio.sleep(final_delay)
            else:
                logger.error(
                    f"{operation_name} failed after {max_retries + 1} attempts. "
                    f"Last error: {str(e)}"
                )
    
    raise last_exception


def handle_app_error(func: Callable) -> Callable:
    """
    Decorator to standardize error handling in async functions.
    Catches AppError instances and converts them to proper HTTP responses.
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        request_id = str(uuid.uuid4())[:8]
        
        try:
            return await func(*args, **kwargs)
            
        except ValidationError as e:
            logger.warning(f"Validation error [{request_id}]: {e.message}")
            from fastapi import HTTPException
            raise HTTPException(
                status_code=422,
                detail=ErrorResponse(
                    error="validation_error",
                    message=e.message,
                    details=e.details,
                    request_id=request_id
                ).dict()
            )
            
        except EvolutionError as e:
            logger.error(f"Evolution error [{request_id}]: {e.message}", exc_info=True)
            from fastapi import HTTPException
            raise HTTPException(
                status_code=500,
                detail=ErrorResponse(
                    error="evolution_error",
                    message=e.message,
                    details=e.details,
                    request_id=request_id
                ).dict()
            )
            
        except DockerError as e:
            logger.error(f"Docker error [{request_id}]: {e.message}", exc_info=True)
            from fastapi import HTTPException
            raise HTTPException(
                status_code=503,
                detail=ErrorResponse(
                    error="docker_error",
                    message=e.message,
                    details=e.details,
                    request_id=request_id
                ).dict()
            )
            
        except DatabaseError as e:
            logger.error(f"Database error [{request_id}]: {e.message}", exc_info=True)
            from fastapi import HTTPException
            raise HTTPException(
                status_code=503,
                detail=ErrorResponse(
                    error="database_error",
                    message=e.message,
                    details=e.details,
                    request_id=request_id
                ).dict()
            )
            
        except Exception as e:
            logger.error(f"Unexpected error [{request_id}]: {str(e)}", exc_info=True)
            from fastapi import HTTPException
            raise HTTPException(
                status_code=500,
                detail=ErrorResponse(
                    error="internal_error",
                    message="An unexpected error occurred",
                    details={"type": type(e).__name__},
                    request_id=request_id
                ).dict()
            )
    
    return wrapper


def create_error_response(
    error: str,
    message: str,
    status_code: int = 500,
    details: Any = None,
    request_id: str = None
) -> dict:
    """
    Create a standardized error response dictionary.
    
    Args:
        error: Error code/type
        message: Human-readable error message
        status_code: HTTP status code
        details: Additional error details
        request_id: Request identifier for tracking
    
    Returns:
        Dictionary formatted for API response
    """
    return ErrorResponse(
        error=error,
        message=message,
        details=details,
        request_id=request_id or str(uuid.uuid4())[:8]
    ).dict()


class CircuitBreaker:
    """
    Simple circuit breaker pattern implementation.
    Prevents repeated failures by stopping requests after threshold.
    """
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = "closed"  # closed, open, half-open
    
    def can_execute(self) -> bool:
        """Check if operation can be executed"""
        if self.state == "closed":
            return True
        
        if self.state == "open":
            # Check if recovery timeout has passed
            if self.last_failure_time and \
               (time.time() - self.last_failure_time) > self.recovery_timeout:
                self.state = "half-open"
                logger.info("Circuit breaker transitioning to half-open")
                return True
            return False
        
        # half-open state allows one test request
        return True
    
    def record_success(self):
        """Record successful operation"""
        self.failure_count = 0
        self.state = "closed"
        logger.debug("Circuit breaker reset to closed state")
    
    def record_failure(self):
        """Record failed operation"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.warning(
                f"Circuit breaker opened after {self.failure_count} failures"
            )
