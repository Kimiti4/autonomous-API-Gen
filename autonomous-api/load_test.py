"""
Locust load testing script for Autonomous Evolution Engine.
Tests API performance under various load conditions.

Usage:
    locust -f load_test.py --host=http://localhost:8000
"""

from locust import HttpUser, task, between
import random
import json


class APIUser(HttpUser):
    """Simulates typical API user behavior"""
    
    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks
    
    @task(3)
    def health_check(self):
        """Frequent health checks (weight: 3)"""
        self.client.get("/health")
    
    @task(2)
    def get_evolution_runs(self):
        """Get evolution run history (weight: 2)"""
        self.client.get("/evolve/runs")
    
    @task(1)
    def start_standard_evolution(self):
        """Start standard evolution (weight: 1)"""
        payload = {
            "generations": random.choice([5, 10, 15]),
            "population_size": random.choice([6, 8, 10]),
            "use_docker": False
        }
        self.client.post(
            "/evolve/start",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
    
    @task(1)
    def get_insights(self):
        """Get elite insights (weight: 1)"""
        self.client.get("/evolve/elite/insights")


class HeavyUser(HttpUser):
    """Simulates heavy user running many evolutions"""
    
    wait_time = between(0.5, 1.5)  # Faster requests
    
    @task(5)
    def start_elite_evolution(self):
        """Start elite evolution frequently (weight: 5)"""
        payload = {
            "generations": random.choice([5, 10]),
            "population_size": random.choice([6, 8]),
            "use_multi_population": True,
            "enable_adaptive_mutation": True,
            "use_docker": False
        }
        self.client.post(
            "/evolve/elite/start",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
    
    @task(2)
    def check_health(self):
        """Check system health (weight: 2)"""
        self.client.get("/health")


class StressTestUser(HttpUser):
    """Aggressive user for stress testing"""
    
    wait_time = between(0.1, 0.5)  # Very fast requests
    
    @task(10)
    def rapid_health_checks(self):
        """Rapid health check requests"""
        self.client.get("/health")
    
    @task(5)
    def rapid_run_list(self):
        """Rapidly fetch run lists"""
        self.client.get("/evolve/runs")
