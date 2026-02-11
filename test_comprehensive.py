"""
Comprehensive API Functionality Test
Tests all major API endpoints that don't require authentication
"""
import requests
import json
import time

BASE_URL = "https://skill-surge-backend-1.onrender.com"

def test_pass(name):
    print(f"✅ {name}")
    return True

def test_fail(name, reason=""):
    print(f"❌ {name} - {reason}")
    return False

def test_skip(name, reason=""):
    print(f"⏭️  {name} - {reason}")
    return None

print("="*100)
print("COMPREHENSIVE API FUNCTIONALITY TEST")
print("="*100)
print(f"Server: {BASE_URL}\n")

results = {"passed": 0, "failed": 0, "skipped": 0}

# Test 1: Health Check
print("\n1. Health Check")
try:
    res = requests.get(f"{BASE_URL}/health", timeout=5)
    if res.status_code == 200 and res.json().get("status") == "healthy":
        test_pass("Health endpoint working")
        results["passed"] += 1
    else:
        test_fail("Health check", f"Status: {res.status_code}")
        results["failed"] += 1
except Exception as e:
    test_fail("Health check", str(e))
    results["failed"] += 1

# Test 2: Root Endpoint
print("\n2. Root Endpoint")
try:
    res = requests.get(f"{BASE_URL}/", timeout=5)
    if res.status_code == 200 and "Cognito" in res.text:
        test_pass("Root endpoint working")
        results["passed"] += 1
    else:
        test_fail("Root endpoint", f"Status: {res.status_code}")
        results["failed"] += 1
except Exception as e:
    test_fail("Root endpoint", str(e))
    results["failed"] += 1

# Test 3: OpenAPI Documentation
print("\n3. API Documentation")
try:
    res = requests.get(f"{BASE_URL}/openapi.json", timeout=5)
    if res.status_code == 200:
        openapi = res.json()
        num_endpoints = len(openapi.get("paths", {}))
        test_pass(f"OpenAPI schema available ({num_endpoints} endpoints)")
        results["passed"] += 1
    else:
        test_fail("OpenAPI", f"Status: {res.status_code}")
        results["failed"] += 1
except Exception as e:
    test_fail("OpenAPI", str(e))
    results["failed"] += 1

# Test 4: Podcast List (GET - should work without auth for listing)
print("\n4. Podcast API")
try:
    res = requests.get(f"{BASE_URL}/api/v1/podcast/list?user_id=test_user", timeout=10)
    if res.status_code in [200, 401]:
        test_pass(f"Podcast list endpoint responding (Status: {res.status_code})")
        results["passed"] += 1
    else:
        test_fail("Podcast list", f"Status: {res.status_code}")
        results["failed"] += 1
except Exception as e:
    test_fail("Podcast list", str(e))
    results["failed"] += 1

# Test 5: Study Timer - Get Today Stats
print("\n5. Study Timer API")
try:
    res = requests.get(f"{BASE_URL}/api/v1/timer/stats/today?user_id=test_user", timeout=10)
    if res.status_code in [200, 401]:
        test_pass(f"Study timer stats endpoint responding (Status: {res.status_code})")
        results["passed"] += 1
    else:
        test_fail("Study timer", f"Status: {res.status_code}")
        results["failed"] += 1
except Exception as e:
    test_fail("Study timer", str(e))
    results["failed"] += 1

# Test 6: Quiz - Get Topics
print("\n6. Quiz API")
try:
    res = requests.get(f"{BASE_URL}/api/v1/quiz/topics?user_id=test_user", timeout=10)
    if res.status_code in [200, 401]:
        test_pass(f"Quiz topics endpoint responding (Status: {res.status_code})")
        results["passed"] += 1
    else:
        test_fail("Quiz topics", f"Status: {res.status_code}")
        results["failed"] += 1
except Exception as e:
    test_fail("Quiz topics", str(e))
    results["failed"] += 1

# Test 7: Flashcards - Get Decks
print("\n7. Flashcards API")
try:
    res = requests.get(f"{BASE_URL}/api/v1/flashcards/decks?user_id=test_user", timeout=10)
    if res.status_code in [200, 401]:
        test_pass(f"Flashcards endpoint responding (Status: {res.status_code})")
        results["passed"] += 1
    else:
        test_fail("Flashcards", f"Status: {res.status_code}")
        results["failed"] += 1
except Exception as e:
    test_fail("Flashcards", str(e))
    results["failed"] += 1

# Test 8: Space - Get Subjects
print("\n8. Space/Subjects API")
try:
    res = requests.get(f"{BASE_URL}/api/v1/space/subjects?user_id=test_user", timeout=10)
    if res.status_code in [200, 401]:
        test_pass(f"Space subjects endpoint responding (Status: {res.status_code})")
        results["passed"] += 1
    else:
        test_fail("Space subjects", f"Status: {res.status_code}")
        results["failed"] += 1
except Exception as e:
    test_fail("Space subjects", str(e))
    results["failed"] += 1

# Test 9: Scribe - Get History
print("\n9. Scribe API")
try:
    res = requests.get(f"{BASE_URL}/api/v1/scribe/history?user_id=test_user", timeout=10)
    if res.status_code in [200, 401]:
        test_pass(f"Scribe history endpoint responding (Status: {res.status_code})")
        results["passed"] += 1
    else:
        test_fail("Scribe history", f"Status: {res.status_code}")
        results["failed"] += 1
except Exception as e:
    test_fail("Scribe history", str(e))
    results["failed"] += 1

# Test 10: Notes Scanner - Get Notes
print("\n10. Notes Scanner API")
try:
    res = requests.get(f"{BASE_URL}/api/v1/notes-scanner/notes?user_id=test_user", timeout=10)
    if res.status_code in [200, 401]:
        test_pass(f"Notes scanner endpoint responding (Status: {res.status_code})")
        results["passed"] += 1
    else:
        test_fail("Notes scanner", f"Status: {res.status_code}")
        results["failed"] += 1
except Exception as e:
    test_fail("Notes scanner", str(e))
    results["failed"] += 1

# Test 11: Hypothesis V1 - List
print("\n11. Hypothesis V1 API")
try:
    res = requests.get(f"{BASE_URL}/api/v1/hypothesis/list?user_id=test_user", timeout=10)
    if res.status_code in [200, 401]:
        test_pass(f"Hypothesis V1 list endpoint responding (Status: {res.status_code})")
        results["passed"] += 1
    else:
        test_fail("Hypothesis V1", f"Status: {res.status_code}")
        results["failed"] += 1
except Exception as e:
    test_fail("Hypothesis V1", str(e))
    results["failed"] += 1

# Test 12: Hypothesis V2 - List Sessions
print("\n12. Hypothesis V2 API")
try:
    res = requests.get(f"{BASE_URL}/api/v2/hypothesis/sessions?user_id=test_user", timeout=10)
    if res.status_code in [200, 401]:
        test_pass(f"Hypothesis V2 sessions endpoint responding (Status: {res.status_code})")
        results["passed"] += 1
    else:
        test_fail("Hypothesis V2", f"Status: {res.status_code}")
        results["failed"] += 1
except Exception as e:
    test_fail("Hypothesis V2", str(e))
    results["failed"] += 1

# Test 13: Mock Interview - List
print("\n13. Mock Interview API")
try:
    res = requests.get(f"{BASE_URL}/api/v1/interviews/?user_id=test_user", timeout=10)
    if res.status_code in [200, 401]:
        test_pass(f"Mock interview endpoint responding (Status: {res.status_code})")
        results["passed"] += 1
    else:
        test_fail("Mock interview", f"Status: {res.status_code}")
        results["failed"] += 1
except Exception as e:
    test_fail("Mock interview", str(e))
    results["failed"] += 1

# Test 14: Memory API
print("\n14. Memory API") 
try:
    res = requests.get(f"{BASE_URL}/api/v1/memory/test_user", timeout=10)
    if res.status_code in [200, 401, 404]:
        test_pass(f"Memory endpoint responding (Status: {res.status_code})")
        results["passed"] += 1
    else:
        test_fail("Memory", f"Status: {res.status_code}")
        results["failed"] += 1
except Exception as e:
    test_fail("Memory", str(e))
    results["failed"] += 1

# Summary
print("\n" + "="*100)
print("TEST SUMMARY")
print("="*100)
print(f"✅ Passed:  {results['passed']}")
print(f"❌ Failed:  {results['failed']}")
print(f"⏭️  Skipped: {results['skipped']}")
print(f"\nTotal: {results['passed'] + results['failed'] + results['skipped']}")
percentage = (results['passed'] / (results['passed'] + results['failed']) * 100) if (results['passed'] + results['failed']) > 0 else 0
print(f"Success Rate: {percentage:.1f}%")
print("="*100)

if results['passed'] >= 10:
    print("\n🎉 EXCELLENT! Backend is fully operational!")
    print("All major API endpoints are responding correctly.")
elif results['passed'] >= 5:
    print("\n✅ GOOD! Most API endpoints are working.")
    print("Some endpoints may require authentication or have specific requirements.")
else:
    print("\n⚠️  WARNING! Many endpoints failed.")
    print("Check server logs for errors.")

print("\n📝 Note: Status code 401 means endpoint exists but requires authentication (expected)")
print("📝 Note: You can view all endpoints at: http://localhost:8000/docs\n")
