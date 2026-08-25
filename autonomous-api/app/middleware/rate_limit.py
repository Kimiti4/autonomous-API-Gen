"""
Rate limiting middleware to prevent API abuse.
Uses simple in-memory tracking with sliding window.
"""

import time
from typing import Dict, Tuple
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.logger import logger


class RateLimiter:
    """Simple rate limiter using sliding window algorithm"""
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        """
        Initialize rate limiter.
        
        Args:
            max_requests: Maximum requests allowed per window
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, list] = {}
    
    def is_rate_limited(self, client_ip: str) -> Tuple[bool, dict]:
        """
        Check if a client is rate limited.
        
        Returns:
            Tuple of (is_limited, rate_limit_info)
        """
        current_time = time.time()
        
        # Clean old entries
        if client_ip not in self.requests:
            self.requests[client_ip] = []
        
        # Remove requests outside the window
        self.requests[client_ip] = [
            req_time for req_time in self.requests[client_ip]
            if current_time - req_time < self.window_seconds
        ]
        
        # Check if limit exceeded
        if len(self.requests[client_ip]) >= self.max_requests:
            # Calculate retry-after time
            oldest_request = min(self.requests[client_ip])
            retry_after = int(self.window_seconds - (current_time - oldest_request)) + 1
            
            return True, {
                "limit": self.max_requests,
                "remaining": 0,
                "retry_after": retry_after,
                "window_seconds": self.window_seconds
            }
        
        # Record this request
        self.requests[client_ip].append(current_time)
        
        remaining = self.max_requests - len(self.requests[client_ip])
        
        return False, {
            "limit": self.max_requests,
            "remaining": remaining,
            "retry_after": 0,
            "window_seconds": self.window_seconds
        }
    
    def cleanup(self):
        """Remove stale entries to prevent memory leaks"""
        current_time = time.time()
        stale_ips = []
        
        for ip, timestamps in self.requests.items():
            # Remove old timestamps
            self.requests[ip] = [
                ts for ts in timestamps
                if current_time - ts < self.window_seconds
            ]
            
            # Mark for removal if empty
            if not self.requests[ip]:
                stale_ips.append(ip)
        
        # Remove empty entries
        for ip in stale_ips:
            del self.requests[ip]

    def _cleanup_stale_entries(self):
        """Backward-compatible alias for older tests and callers."""
        self.cleanup()


# Global rate limiters for different endpoint types
evolution_limiter = RateLimiter(max_requests=20, window_seconds=60)  # 20 req/min for evolution
general_limiter = RateLimiter(max_requests=100, window_seconds=60)   # 100 req/min for general


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for rate limiting"""
    
    async def dispatch(self, request: Request, call_next):
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        
        # Determine which limiter to use based on path
        path = request.url.path
        
        if "/evolve" in path:
            limiter = evolution_limiter
        else:
            limiter = general_limiter
        
        # Check rate limit
        is_limited, info = limiter.is_rate_limited(client_ip)
        
        if is_limited:
            logger.warning(f"Rate limit exceeded for {client_ip} on {path}")
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "rate_limit_exceeded",
                    "message": f"Too many requests. Try again in {info['retry_after']} seconds.",
                    "retry_after": info['retry_after'],
                    "limit": info['limit'],
                    "window_seconds": info['window_seconds']
                },
                headers={
                    "Retry-After": str(info['retry_after']),
                    "X-RateLimit-Limit": str(info['limit']),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time()) + info['retry_after'])
                }
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers to response
        response.headers["X-RateLimit-Limit"] = str(info['limit'])
        response.headers["X-RateLimit-Remaining"] = str(info['remaining'])
        response.headers["X-RateLimit-Window"] = str(info['window_seconds'])
        
        return response
    
    @staticmethod
    def cleanup_old_entries():
        """Periodic cleanup of stale rate limit entries"""
        evolution_limiter.cleanup()
        general_limiter.cleanup()
