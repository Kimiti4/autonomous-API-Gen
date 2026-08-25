#!/usr/bin/env python3
"""
Backend Performance Test Script
Tests response times and validates optimizations
"""
import requests
import time
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"

def test_endpoint(name, url, method="GET", expected_status=200):
    """Test an endpoint and report performance"""
    print(f"\n🧪 Testing: {name}")
    print(f"   URL: {url}")
    
    start_time = time.time()
    try:
        if method == "GET":
            response = requests.get(url)
        elif method == "POST":
            response = requests.post(url, json={})
        
        elapsed = time.time() - start_time
        
        status = "✅ PASS" if response.status_code == expected_status else "❌ FAIL"
        print(f"   Status: {status} ({response.status_code})")
        print(f"   Response Time: {elapsed*1000:.2f}ms")
        
        if elapsed > 1.0:
            print(f"   ⚠️  WARNING: Slow response (>1s)")
        elif elapsed > 0.5:
            print(f"   ⚡ Good response time")
        else:
            print(f"   🚀 Excellent response time!")
            
        return response.status_code == expected_status, elapsed
        
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"   ❌ ERROR: {str(e)}")
        print(f"   Time: {elapsed*1000:.2f}ms")
        return False, elapsed

def main():
    print("=" * 70)
    print("🔬 Backend Performance Test Suite")
    print("=" * 70)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Target: {BASE_URL}")
    print("=" * 70)
    
    results = []
    
    # Test 1: Root endpoint
    success, time_taken = test_endpoint(
        "Root Endpoint",
        f"{BASE_URL}/"
    )
    results.append(("Root", success, time_taken))
    
    # Test 2: Health check
    success, time_taken = test_endpoint(
        "Health Check",
        f"{BASE_URL}/health"
    )
    results.append(("Health Check", success, time_taken))
    
    # Test 3: API Docs
    success, time_taken = test_endpoint(
        "API Documentation",
        f"{BASE_URL}/docs"
    )
    results.append(("API Docs", success, time_taken))
    
    # Test 4: Get evolution runs (should be fast with LIMIT)
    success, time_taken = test_endpoint(
        "Get Evolution Runs",
        f"{BASE_URL}/evolve/runs"
    )
    results.append(("Evolution Runs", success, time_taken))
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 TEST SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for _, success, _ in results if success)
    total = len(results)
    
    print(f"\nTotal Tests: {total}")
    print(f"Passed: {passed} ✅")
    print(f"Failed: {total - passed} ❌")
    
    avg_time = sum(t for _, _, t in results) / len(results) if results else 0
    print(f"\nAverage Response Time: {avg_time*1000:.2f}ms")
    
    if avg_time < 0.2:
        print("Performance Rating: 🚀 EXCELLENT")
    elif avg_time < 0.5:
        print("Performance Rating: ⚡ GOOD")
    elif avg_time < 1.0:
        print("Performance Rating: ⚠️  ACCEPTABLE")
    else:
        print("Performance Rating: ❌ NEEDS OPTIMIZATION")
    
    print("\n" + "=" * 70)
    print("✨ Optimization Highlights:")
    print("  • Database connection pooling enabled")
    print("  • Batch operations for genome storage")
    print("  • Dependency injection for session management")
    print("  • Query limits on list endpoints")
    print("  • Optimized health check calculations")
    print("=" * 70)
    
    return passed == total

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
