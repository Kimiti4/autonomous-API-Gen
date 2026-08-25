"""
Test script for production hardening features.
Validates security, rate limiting, error handling, and health checks.
"""

import requests
import time
import json
from typing import List, Dict

BASE_URL = "http://localhost:8000"


def print_section(title: str):
    """Print formatted section header"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def test_health_check():
    """Test health check endpoint"""
    print_section("1. Testing Health Check Endpoint")
    
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        assert response.status_code == 200, "Health check should return 200"
        data = response.json()
        assert "status" in data, "Should have status field"
        assert "components" in data, "Should have components field"
        assert "version" in data, "Should have version field"
        
        print("✅ Health check passed!")
        return True
        
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False


def test_validation():
    """Test input validation with Pydantic models"""
    print_section("2. Testing Input Validation")
    
    # Test invalid generations (too high)
    print("\nTest A: Invalid generations (>100)")
    response = requests.post(
        f"{BASE_URL}/evolve/start",
        json={"generations": 200, "population_size": 10}
    )
    print(f"Status Code: {response.status_code}")
    if response.status_code == 422:
        print(f"Validation Error: {json.dumps(response.json(), indent=2)}")
        print("✅ Correctly rejected invalid generations")
    else:
        print(f"❌ Expected 422, got {response.status_code}")
    
    # Test invalid population size (too low)
    print("\nTest B: Invalid population size (<4)")
    response = requests.post(
        f"{BASE_URL}/evolve/start",
        json={"generations": 5, "population_size": 2}
    )
    print(f"Status Code: {response.status_code}")
    if response.status_code == 422:
        print("✅ Correctly rejected invalid population size")
    else:
        print(f"❌ Expected 422, got {response.status_code}")
    
    # Test valid request
    print("\nTest C: Valid request")
    response = requests.post(
        f"{BASE_URL}/evolve/start",
        json={"generations": 5, "population_size": 8}
    )
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        print("✅ Valid request accepted")
        return True
    else:
        print(f"❌ Expected 200, got {response.status_code}")
        return False


def test_rate_limiting():
    """Test rate limiting on evolution endpoints"""
    print_section("3. Testing Rate Limiting")
    
    print("Sending rapid requests to evolution endpoint...")
    print("(Limit: 20 requests per minute)\n")
    
    success_count = 0
    rate_limited_count = 0
    
    for i in range(25):
        response = requests.post(
            f"{BASE_URL}/evolve/start",
            json={"generations": 1, "population_size": 4}
        )
        
        if response.status_code == 200:
            success_count += 1
            print(f"Request {i+1}: ✅ Accepted (200)")
        elif response.status_code == 429:
            rate_limited_count += 1
            print(f"Request {i+1}: ❌ Rate Limited (429)")
            
            # Check rate limit headers
            if "X-RateLimit-Limit" in response.headers:
                print(f"   Headers: Limit={response.headers['X-RateLimit-Limit']}, "
                      f"Remaining={response.headers.get('X-RateLimit-Remaining', 'N/A')}")
            break
        else:
            print(f"Request {i+1}: ⚠️ Unexpected status {response.status_code}")
    
    print(f"\nSummary:")
    print(f"  Successful requests: {success_count}")
    print(f"  Rate limited requests: {rate_limited_count}")
    
    if rate_limited_count > 0:
        print("✅ Rate limiting is working!")
        return True
    else:
        print("⚠️ Rate limiting may not be active (or limit too high)")
        return False


def test_security_headers():
    """Test security headers are present"""
    print_section("4. Testing Security Headers")
    
    response = requests.get(f"{BASE_URL}/")
    
    required_headers = [
        "X-Content-Type-Options",
        "X-Frame-Options",
        "X-XSS-Protection",
        "Strict-Transport-Security",
        "Content-Security-Policy",
        "Referrer-Policy",
        "Cache-Control"
    ]
    
    print("Checking security headers:\n")
    all_present = True
    
    for header in required_headers:
        if header in response.headers:
            print(f"✅ {header}: {response.headers[header][:50]}...")
        else:
            print(f"❌ {header}: MISSING")
            all_present = False
    
    # Check server header is removed
    if "server" not in response.headers:
        print("✅ Server header removed (good!)")
    else:
        print(f"⚠️ Server header present: {response.headers['server']}")
    
    if all_present:
        print("\n✅ All security headers present!")
        return True
    else:
        print("\n❌ Some security headers missing")
        return False


def test_elite_evolution():
    """Test elite evolution endpoint"""
    print_section("5. Testing Elite Evolution")
    
    print("Starting elite evolution with multi-population...")
    response = requests.post(
        f"{BASE_URL}/evolve/elite/start",
        json={
            "generations": 3,
            "population_size": 6,
            "use_multi_population": True,
            "enable_adaptive_mutation": True
        }
    )
    
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)}")
        print("✅ Elite evolution started successfully")
        return True
    else:
        print(f"❌ Expected 200, got {response.status_code}")
        print(f"Error: {response.text}")
        return False


def test_insights_endpoint():
    """Test insights endpoint"""
    print_section("6. Testing Insights Endpoint")
    
    response = requests.get(f"{BASE_URL}/evolve/elite/insights")
    
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Insights: {json.dumps(data, indent=2)[:500]}...")
        print("✅ Insights endpoint working")
        return True
    else:
        print(f"❌ Expected 200, got {response.status_code}")
        return False


def test_cors_configuration():
    """Test CORS configuration"""
    print_section("7. Testing CORS Configuration")
    
    # Test preflight request
    response = requests.options(
        f"{BASE_URL}/evolve/start",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type"
        }
    )
    
    print(f"Preflight Status: {response.status_code}")
    
    cors_headers = [
        "Access-Control-Allow-Origin",
        "Access-Control-Allow-Methods",
        "Access-Control-Allow-Headers"
    ]
    
    for header in cors_headers:
        if header in response.headers:
            print(f"✅ {header}: {response.headers[header]}")
        else:
            print(f"❌ {header}: MISSING")
    
    if "Access-Control-Allow-Origin" in response.headers:
        print("\n✅ CORS configured correctly")
        return True
    else:
        print("\n❌ CORS not properly configured")
        return False


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("  PRODUCTION HARDENING TEST SUITE")
    print("="*60)
    print(f"\nTesting against: {BASE_URL}")
    print("Make sure the server is running: uvicorn app.main:app --reload\n")
    
    results = []
    
    # Run tests
    results.append(("Health Check", test_health_check()))
    results.append(("Input Validation", test_validation()))
    results.append(("Rate Limiting", test_rate_limiting()))
    results.append(("Security Headers", test_security_headers()))
    results.append(("Elite Evolution", test_elite_evolution()))
    results.append(("Insights Endpoint", test_insights_endpoint()))
    results.append(("CORS Configuration", test_cors_configuration()))
    
    # Print summary
    print_section("TEST SUMMARY")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! System is production-ready.")
    else:
        print(f"\n⚠️ {total - passed} test(s) failed. Review output above.")
    
    return passed == total


if __name__ == "__main__":
    try:
        success = main()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
        exit(1)
    except Exception as e:
        print(f"\n\n❌ Test suite error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
