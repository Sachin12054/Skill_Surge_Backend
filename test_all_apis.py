"""
Comprehensive API Test Suite
Tests all available endpoints without authentication
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_endpoint(name, endpoint, method="GET", data=None):
    """Test a single endpoint"""
    url = f"{BASE_URL}{endpoint}"
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print(f"Endpoint: {method} {endpoint}")
    
    print(f"{'='*60}")
    
    try:
        if method == "GET":
            response = requests.get(url, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=30)
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ SUCCESS")
            try:
                result = response.json()
                print(f"Response: {json.dumps(result, indent=2)[:500]}...")
            except:
                print(f"Response: {response.text[:200]}...")
        elif response.status_code == 401:
            print("⚠️  REQUIRES AUTHENTICATION")
        elif response.status_code == 422:
            print("⚠️  VALIDATION ERROR")
            print(f"Details: {response.json()}")
        else:
            print(f"❌ FAILED: {response.status_code}")
            print(f"Response: {response.text[:200]}...")
            
        return response.status_code == 200
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def main():
    """Run all API tests"""
    print("\n" + "="*80)
    print("COMPREHENSIVE API TEST SUITE")
    print("="*80)
    print(f"Server: {BASE_URL}")
    print("="*80)
    
    results = {}
    
    # Test 1: Health check
    results['health'] = test_endpoint(
        "Health Check",
        "/health",
        "GET"
    )
    
    # Test 2: Root endpoint  
    results['root'] = test_endpoint(
        "Root Endpoint",
        "/",
        "GET"
    )
    
    # Test 3: OpenAPI docs
    results['docs'] = test_endpoint(
        "API Documentation",
        "/openapi.json",
        "GET"
    )
    
    # Test 4: Podcast generation (simple test)
    results['podcast'] = test_endpoint(
        "Podcast Generation",
        "/api/v1/podcast/generate",
        "POST",
        {
            "title": "Introduction to Machine Learning",
            "content": "Machine learning is a subset of AI that enables systems to learn from data.",
            "duration": "short"
        }
    )
    
    # Test 5: Study timer
    results['study_timer'] = test_endpoint(
        "Study Timer - Get Sessions",
        "/api/v1/study-timer/sessions?user_id=test_user",
        "GET"
    )
    
    # Test 6: Graph endpoints
    results['graph'] = test_endpoint(
        "Knowledge Graph - Get Graph",
        "/api/v1/graph?user_id=test_user",
        "GET"
    )
    
    # Test 7: Space endpoints
    results['spaces'] = test_endpoint(
        "Spaces - List Spaces",
        "/api/v1/space/spaces?user_id=test_user",
        "GET"
    )
    
    # Test 8: Quiz endpoints  
    results['quiz'] = test_endpoint(
        "Quiz - Get Quizzes",
        "/api/v1/quiz/quizzes?user_id=test_user",
        "GET"
    )
    
    # Test 9: Flashcards
    results['flashcards'] = test_endpoint(
        "Flashcards - Get Decks",
        "/api/v1/flashcards/decks?user_id=test_user",
        "GET"
    )
    
    # Print Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, status in results.items():
        symbol = "✅" if status else "❌"
        print(f"{symbol} {name}")
    
    print(f"\n{'='*80}")
    print(f"Results: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    print(f"{'='*80}\n")
    
    if passed == total:
        print("🎉 All tests passed! API is fully operational!")
    elif passed > 0:
        print("⚠️  Some endpoints working, some require authentication or have errors")
    else:
        print("❌ No tests passed - server may have issues")

if __name__ == "__main__":
    main()
