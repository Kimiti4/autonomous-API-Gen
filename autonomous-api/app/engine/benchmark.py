import time
import httpx
from typing import Optional
from app.core.logger import logger


async def benchmark_api_performance(port: int, num_requests: int = 5) -> dict:
    """
    Benchmark API performance by sending multiple requests and measuring latency.
    
    Returns:
        Dictionary with performance metrics
    """
    base_url = f"http://localhost:{port}"
    
    try:
        latencies = []
        status_codes = []
        errors = 0
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            for i in range(num_requests):
                try:
                    start_time = time.time()
                    response = await client.get(f"{base_url}/")
                    elapsed = time.time() - start_time
                    
                    latencies.append(elapsed)
                    status_codes.append(response.status_code)
                    
                    # Small delay between requests
                    if i < num_requests - 1:
                        await asyncio.sleep(0.1)
                        
                except Exception as e:
                    logger.warning(f"Benchmark request {i+1} failed: {e}")
                    errors += 1
        
        if not latencies:
            return {
                "success": False,
                "error": "No successful requests"
            }
        
        # Calculate metrics
        avg_latency = sum(latencies) / len(latencies)
        min_latency = min(latencies)
        max_latency = max(latencies)
        
        # Calculate throughput (requests per second)
        total_time = sum(latencies)
        throughput = num_requests / total_time if total_time > 0 else 0
        
        # Success rate
        success_rate = (num_requests - errors) / num_requests
        
        # Performance score (0-1, higher is better)
        # Lower latency = higher score
        latency_score = max(0, 1.0 - (avg_latency * 2))  # Penalize high latency
        
        return {
            "success": True,
            "avg_latency_ms": round(avg_latency * 1000, 2),
            "min_latency_ms": round(min_latency * 1000, 2),
            "max_latency_ms": round(max_latency * 1000, 2),
            "throughput_rps": round(throughput, 2),
            "success_rate": round(success_rate, 3),
            "performance_score": round(latency_score, 3),
            "total_requests": num_requests,
            "errors": errors
        }
        
    except Exception as e:
        logger.error(f"Benchmark failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def calculate_performance_fitness(performance_metrics: dict) -> float:
    """
    Convert performance metrics to fitness score component.
    
    Args:
        performance_metrics: Output from benchmark_api_performance
    
    Returns:
        Fitness score between 0.0 and 1.0
    """
    if not performance_metrics.get("success"):
        return 0.0
    
    # Weight different factors
    latency_score = performance_metrics.get("performance_score", 0)
    success_rate = performance_metrics.get("success_rate", 0)
    throughput = performance_metrics.get("throughput_rps", 0)
    
    # Normalize throughput (assume 100 rps is excellent)
    throughput_score = min(throughput / 100.0, 1.0)
    
    # Combined performance fitness
    fitness = (
        latency_score * 0.5 +      # 50% weight on latency
        success_rate * 0.3 +        # 30% weight on reliability
        throughput_score * 0.2      # 20% weight on throughput
    )
    
    return round(fitness, 3)


# Import asyncio at module level
import asyncio
