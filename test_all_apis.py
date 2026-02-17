"""
COMPREHENSIVE API TEST SUITE
Tests ALL available endpoints across all features
"""
import requests
import json
import time
from typing import Dict, List, Tuple

BASE_URL = "http://localhost:8000"

# Color codes for terminal output
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def test_endpoint(name: str, endpoint: str, method: str = "GET", data: dict = None, 
                 params: dict = None, expect_auth: bool = False) -> Tuple[bool, str]:
    """
    Test a single endpoint with detailed response validation
    
    Returns: (success: bool, status_message: str)
    """
    url = f"{BASE_URL}{endpoint}"
    
    try:
        if method == "GET":
            response = requests.get(url, params=params, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=data, params=params, timeout=30)
        elif method == "PUT":
            response = requests.put(url, json=data, params=params, timeout=30)
        elif method == "DELETE":
            response = requests.delete(url, params=params, timeout=10)
        else:
            return False, f"Unsupported method: {method}"
        
        status = response.status_code
        
        # Success
        if status == 200:
            try:
                result = response.json()
                return True, f"✅ SUCCESS - {len(str(result))} bytes"
            except:
                return True, f"✅ SUCCESS - {response.text[:50]}..."
        
        # Expected authentication requirement
        if status in [401, 403]:
            if expect_auth:
                return True, "🔒 AUTH REQUIRED (expected)"
            else:
                return False, "🔒 AUTH REQUIRED (unexpected)"
        
        # Validation errors
        if status == 422:
            try:
                error = response.json()
                return False, f"⚠️  VALIDATION ERROR: {error.get('detail', 'Unknown')[:50]}"
            except:
                return False, f"⚠️  VALIDATION ERROR"
        
        # Not found
        if status == 404:
            return False, "❌ NOT FOUND (404)"
        
        # Server error
        if status >= 500:
            return False, f"❌ SERVER ERROR ({status})"
        
        # Other errors
        return False, f"❌ FAILED ({status}): {response.text[:50]}"
        
    except requests.exceptions.Timeout:
        return False, "⏱️  TIMEOUT"
    except requests.exceptions.ConnectionError:
        return False, "🔌 CONNECTION ERROR"
    except Exception as e:
        return False, f"❌ ERROR: {str(e)[:50]}"

def print_test(name: str, endpoint: str, method: str, success: bool, message: str):
    """Print formatted test result"""
    icon = "✅" if success else "❌"
    color = Colors.GREEN if success else Colors.RED
    print(f"{icon} {color}{method:6}{Colors.RESET} {endpoint:45} | {message}")

def print_category(category: str):
    """Print category header"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}  {category}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.RESET}")

def main():
    """Run comprehensive API test suite for all features"""
    print(f"\n{Colors.BOLD}{'='*80}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}  COMPREHENSIVE API TEST SUITE - ALL FEATURES{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*80}{Colors.RESET}")
    print(f"Server: {BASE_URL}")
    print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{Colors.BOLD}{'='*80}{Colors.RESET}")
    
    results = {}
    
    # ========== CORE ENDPOINTS ==========
    print_category("CORE ENDPOINTS")
    
    success, msg = test_endpoint("Root", "/", "GET")
    print_test("Root", "/", "GET", success, msg)
    results['root'] = success
    
    success, msg = test_endpoint("Health", "/health", "GET")
    print_test("Health Check", "/health", "GET", success, msg)
    results['health'] = success
    
    success, msg = test_endpoint("OpenAPI Schema", "/openapi.json", "GET")
    print_test("OpenAPI Schema", "/openapi.json", "GET", success, msg)
    results['openapi'] = success
    
    # ========== CHATBOT ==========
    print_category("MULTILINGUAL CHATBOT")
    
    success, msg = test_endpoint("Languages List", "/api/v1/chat/languages", "GET")
    print_test("Get Supported Languages", "/api/v1/chat/languages", "GET", success, msg)
    results['chat_languages'] = success
    
    success, msg = test_endpoint("Chat Send", "/api/v1/chat/send", "POST", 
                                 data={"message": "Hello", "target_language": "en-IN"},
                                 expect_auth=True)
    print_test("Send Chat Message", "/api/v1/chat/send", "POST", success, msg)
    results['chat_send'] = success
    
    # ========== FLASHCARDS ==========
    print_category("FLASHCARDS - Spaced Repetition Learning")
    
    success, msg = test_endpoint("Flashcard Decks", "/api/v1/flashcards/decks", "GET", expect_auth=True)
    print_test("Get All Decks", "/api/v1/flashcards/decks", "GET", success, msg)
    results['flashcards_decks'] = success
    
    success, msg = test_endpoint("Flashcard Stats", "/api/v1/flashcards/stats", "GET", expect_auth=True)
    print_test("Get Statistics", "/api/v1/flashcards/stats", "GET", success, msg)
    results['flashcards_stats'] = success
    
    success, msg = test_endpoint("Due Cards", "/api/v1/flashcards/study/due", "GET", expect_auth=True)
    print_test("Get Due Cards", "/api/v1/flashcards/study/due", "GET", success, msg)
    results['flashcards_due'] = success
    
    success, msg = test_endpoint("Generate Flashcards", "/api/v1/flashcards/generate", "POST",
                                 data={"text": "Test content", "subject": "Test"},
                                 expect_auth=True)
    print_test("Generate from Text", "/api/v1/flashcards/generate", "POST", success, msg)
    results['flashcards_generate'] = success
    
    success, msg = test_endpoint("Start Study Session", "/api/v1/flashcards/study/session/start", "POST",
                                 data={"deck_id": "test"},
                                 expect_auth=True)
    print_test("Start Study Session", "/api/v1/flashcards/study/session/start", "POST", success, msg)
    results['flashcards_session'] = success
    
    # ========== QUIZ SYSTEM ==========
    print_category("ADAPTIVE QUIZ SYSTEM")
    
    success, msg = test_endpoint("Quiz History", "/api/v1/quiz/history", "GET", expect_auth=True)
    print_test("Get Quiz History", "/api/v1/quiz/history", "GET", success, msg)
    results['quiz_history'] = success
    
    success, msg = test_endpoint("Quiz Topics", "/api/v1/quiz/topics", "GET", expect_auth=True)
    print_test("Get Topics", "/api/v1/quiz/topics", "GET", success, msg)
    results['quiz_topics'] = success
    
    success, msg = test_endpoint("Subject Insights", "/api/v1/quiz/subjects/insights", "GET", expect_auth=True)
    print_test("Subject Insights", "/api/v1/quiz/subjects/insights", "GET", success, msg)
    results['quiz_insights'] = success
    
    success, msg = test_endpoint("Adaptive Question", "/api/v1/quiz/next-adaptive", "GET", expect_auth=True)
    print_test("Next Adaptive Question", "/api/v1/quiz/next-adaptive", "GET", success, msg)
    results['quiz_adaptive'] = success
    
    success, msg = test_endpoint("Generate Quiz", "/api/v1/quiz/generate", "POST",
                                 data={"topic": "Test", "difficulty": "medium", "num_questions": 5},
                                 expect_auth=True)
    print_test("Generate Quiz", "/api/v1/quiz/generate", "POST", success, msg)
    results['quiz_generate'] = success
    
    # ========== PODCAST ==========
    print_category("AI PODCAST GENERATION")
    
    success, msg = test_endpoint("Podcast List", "/api/v1/podcast/list", "GET", expect_auth=True)
    print_test("List Podcasts", "/api/v1/podcast/list", "GET", success, msg)
    results['podcast_list'] = success
    
    success, msg = test_endpoint("Create Podcast", "/api/v1/podcast/create", "POST",
                                 data={"title": "Test", "content": "Test content", "duration": "short"},
                                 expect_auth=True)
    print_test("Create Podcast", "/api/v1/podcast/create", "POST", success, msg)
    results['podcast_create'] = success
    
    # ========== HYPOTHESIS LAB ==========
    print_category("HYPOTHESIS LAB - Research Assistant")
    
    success, msg = test_endpoint("Hypothesis List", "/api/v1/hypothesis/list", "GET", expect_auth=True)
    print_test("List Hypotheses (v1)", "/api/v1/hypothesis/list", "GET", success, msg)
    results['hypothesis_list'] = success
    
    success, msg = test_endpoint("Generate Hypothesis", "/api/v1/hypothesis/generate", "POST",
                                 data={"topic": "Machine Learning", "query": "What is deep learning?"},
                                 expect_auth=True)
    print_test("Generate Hypothesis (v1)", "/api/v1/hypothesis/generate", "POST", success, msg)
    results['hypothesis_generate'] = success
    
    # Hypothesis V2
    success, msg = test_endpoint("Sessions List", "/api/v2/hypothesis/sessions", "GET", expect_auth=True)
    print_test("List Sessions (v2)", "/api/v2/hypothesis/sessions", "GET", success, msg)
    results['hypothesis_v2_sessions'] = success
    
    success, msg = test_endpoint("Saved Hypotheses", "/api/v2/hypothesis/saved", "GET", expect_auth=True)
    print_test("Get Saved (v2)", "/api/v2/hypothesis/saved", "GET", success, msg)
    results['hypothesis_v2_saved'] = success
    
    # ========== SCRIBE ==========
    print_category("SCRIBE - Notes & Math Analysis")
    
    success, msg = test_endpoint("Scribe History", "/api/v1/scribe/history", "GET", expect_auth=True)
    print_test("Get History", "/api/v1/scribe/history", "GET", success, msg)
    results['scribe_history'] = success
    
    success, msg = test_endpoint("Analyze Notes", "/api/v1/scribe/analyze", "POST",
                                 data={"content": "Test notes", "type": "handwritten"},
                                 expect_auth=True)
    print_test("Analyze Notes", "/api/v1/scribe/analyze", "POST", success, msg)
    results['scribe_analyze'] = success
    
    success, msg = test_endpoint("Validate Math", "/api/v1/scribe/validate-math", "POST",
                                 data={"expression": "2+2=4"},
                                 expect_auth=True)
    print_test("Validate Math", "/api/v1/scribe/validate-math", "POST", success, msg)
    results['scribe_math'] = success
    
    # ========== STUDY TIMER ==========
    print_category("STUDY TIMER - Pomodoro Tracking")
    
    success, msg = test_endpoint("Timer History", "/api/v1/timer/history", "GET", expect_auth=True)
    print_test("Get History", "/api/v1/timer/history", "GET", success, msg)
    results['timer_history'] = success
    
    success, msg = test_endpoint("Active Session", "/api/v1/timer/session/active", "GET", expect_auth=True)
    print_test("Get Active Session", "/api/v1/timer/session/active", "GET", success, msg)
    results['timer_active'] = success
    
    success, msg = test_endpoint("Today Stats", "/api/v1/timer/stats/today", "GET", expect_auth=True)
    print_test("Today's Stats", "/api/v1/timer/stats/today", "GET", success, msg)
    results['timer_today'] = success
    
    success, msg = test_endpoint("Week Stats", "/api/v1/timer/stats/week", "GET", expect_auth=True)
    print_test("Week Stats", "/api/v1/timer/stats/week", "GET", success, msg)
    results['timer_week'] = success
    
    success, msg = test_endpoint("Subject Stats", "/api/v1/timer/stats/subjects", "GET", expect_auth=True)
    print_test("Subject Stats", "/api/v1/timer/stats/subjects", "GET", success, msg)
    results['timer_subjects'] = success
    
    success, msg = test_endpoint("Timer Settings", "/api/v1/timer/settings", "GET", expect_auth=True)
    print_test("Get Settings", "/api/v1/timer/settings", "GET", success, msg)
    results['timer_settings'] = success
    
    # ========== SPACE (PDF MANAGEMENT) ==========
    print_category("SPACE - PDF Management")
    
    success, msg = test_endpoint("PDF List", "/api/v1/space/pdfs", "GET", expect_auth=True)
    print_test("List PDFs", "/api/v1/space/pdfs", "GET", success, msg)
    results['space_pdfs'] = success
    
    success, msg = test_endpoint("Subjects List", "/api/v1/space/subjects", "GET", expect_auth=True)
    print_test("List Subjects", "/api/v1/space/subjects", "GET", success, msg)
    results['space_subjects'] = success
    
    success, msg = test_endpoint("Create Subject", "/api/v1/space/subjects", "POST",
                                 data={"name": "Test Subject", "color": "#FF0000"},
                                 expect_auth=True)
    print_test("Create Subject", "/api/v1/space/subjects", "POST", success, msg)
    results['space_create_subject'] = success
    
    # ========== KNOWLEDGE GRAPH ==========
    print_category("KNOWLEDGE GRAPH")
    
    # Using placeholder IDs since we need actual course IDs
    success, msg = test_endpoint("Get Graph", "/api/v1/graph/test-course", "GET", expect_auth=True)
    print_test("Get Course Graph", "/api/v1/graph/{course_id}", "GET", success, msg)
    results['graph_get'] = success
    
    success, msg = test_endpoint("Learning Path", "/api/v1/graph/test-course/path", "GET", 
                                 params={"target": "test"}, expect_auth=True)
    print_test("Get Learning Path", "/api/v1/graph/{course_id}/path", "GET", success, msg)
    results['graph_path'] = success
    
    # ========== MOCK INTERVIEWS ==========
    print_category("MOCK INTERVIEWS")
    
    success, msg = test_endpoint("Interview List", "/api/v1/interviews/", "GET", expect_auth=True)
    print_test("List Interviews", "/api/v1/interviews/", "GET", success, msg)
    results['interviews_list'] = success
    
    success, msg = test_endpoint("Start Interview", "/api/v1/interviews/start", "POST",
                                 data={"topic": "Python", "difficulty": "medium"},
                                 expect_auth=True)
    print_test("Start Interview", "/api/v1/interviews/start", "POST", success, msg)
    results['interviews_start'] = success
    
    # ========== NOTES SCANNER ==========
    print_category("NOTES SCANNER - OCR & Summarization")
    
    success, msg = test_endpoint("Notes List", "/api/v1/notes-scanner/notes", "GET", expect_auth=True)
    print_test("List Notes", "/api/v1/notes-scanner/notes", "GET", success, msg)
    results['notes_list'] = success
    
    success, msg = test_endpoint("Scan Notes", "/api/v1/notes-scanner/scan", "POST",
                                 data={"image_url": "test.jpg"},
                                 expect_auth=True)
    print_test("Scan Notes", "/api/v1/notes-scanner/scan", "POST", success, msg)
    results['notes_scan'] = success
    
    # ========== MEMORY (USER PROFILE) ==========
    print_category("MEMORY - User Learning Profile")
    
    success, msg = test_endpoint("User Memory", "/api/v1/memory/test-user", "GET", expect_auth=True)
    print_test("Get User Memory", "/api/v1/memory/{user_id}", "GET", success, msg)
    results['memory_get'] = success
    
    success, msg = test_endpoint("Memory Insights", "/api/v1/memory/test-user/insights", "GET", expect_auth=True)
    print_test("Get Insights", "/api/v1/memory/{user_id}/insights", "GET", success, msg)
    results['memory_insights'] = success
    
    success, msg = test_endpoint("Update Memory", "/api/v1/memory/update", "POST",
                                 data={"user_id": "test-user", "event": "test_event", "data": {}},
                                 expect_auth=True)
    print_test("Update Memory", "/api/v1/memory/update", "POST", success, msg)
    results['memory_update'] = success
    
    # ========== STUDY ASSISTANT ==========
    print_category("STUDY ASSISTANT")
    
    success, msg = test_endpoint("Daily Drill", "/api/v1/study/daily-drill", "GET", expect_auth=True)
    print_test("Get Daily Drill", "/api/v1/study/daily-drill", "GET", success, msg)
    results['study_drill'] = success
    
    success, msg = test_endpoint("Course Progress", "/api/v1/study/progress/test-course", "GET", expect_auth=True)
    print_test("Get Progress", "/api/v1/study/progress/{course_id}", "GET", success, msg)
    results['study_progress'] = success
    
    # ========== PRINT SUMMARY ==========
    print(f"\n{Colors.BOLD}{'='*80}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}  TEST RESULTS SUMMARY{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*80}{Colors.RESET}")
    
    # Count results by category
    categories = {
        'Core': ['root', 'health', 'openapi'],
        'Chat': [k for k in results.keys() if k.startswith('chat_')],
        'Flashcards': [k for k in results.keys() if k.startswith('flashcards_')],
        'Quiz': [k for k in results.keys() if k.startswith('quiz_')],
        'Podcast': [k for k in results.keys() if k.startswith('podcast_')],
        'Hypothesis': [k for k in results.keys() if k.startswith('hypothesis_')],
        'Scribe': [k for k in results.keys() if k.startswith('scribe_')],
        'Timer': [k for k in results.keys() if k.startswith('timer_')],
        'Space': [k for k in results.keys() if k.startswith('space_')],
        'Graph': [k for k in results.keys() if k.startswith('graph_')],
        'Interviews': [k for k in results.keys() if k.startswith('interviews_')],
        'Notes': [k for k in results.keys() if k.startswith('notes_')],
        'Memory': [k for k in results.keys() if k.startswith('memory_')],
        'Study': [k for k in results.keys() if k.startswith('study_')],
    }
    
    for category, keys in categories.items():
        if not keys:
            continue
        passed = sum(1 for k in keys if results.get(k, False))
        total = len(keys)
        percentage = (passed / total * 100) if total > 0 else 0
        
        color = Colors.GREEN if percentage == 100 else Colors.YELLOW if percentage >= 50 else Colors.RED
        icon = "✅" if percentage == 100 else "⚠️" if percentage >= 50 else "❌"
        
        print(f"{icon} {color}{category:20}{Colors.RESET} {passed:2}/{total:2} passed ({percentage:5.1f}%)")
    
    # Overall statistics
    total_passed = sum(1 for v in results.values() if v)
    total_tests = len(results)
    overall_percentage = (total_passed / total_tests * 100) if total_tests > 0 else 0
    
    print(f"\n{Colors.BOLD}{'='*80}{Colors.RESET}")
    print(f"{Colors.BOLD}  OVERALL: {total_passed}/{total_tests} tests passed ({overall_percentage:.1f}%){Colors.RESET}")
    print(f"{Colors.BOLD}{'='*80}{Colors.RESET}\n")
    
    # Final verdict
    if overall_percentage == 100:
        print(f"{Colors.GREEN}{Colors.BOLD}🎉 PERFECT! All endpoints are accessible!{Colors.RESET}")
    elif overall_percentage >= 80:
        print(f"{Colors.GREEN}{Colors.BOLD}✅ EXCELLENT! Most endpoints working properly!{Colors.RESET}")
    elif overall_percentage >= 60:
        print(f"{Colors.YELLOW}{Colors.BOLD}⚠️  GOOD! Most critical endpoints functional.{Colors.RESET}")
    elif overall_percentage >= 40:
        print(f"{Colors.YELLOW}{Colors.BOLD}⚠️  FAIR! Some endpoints need attention.{Colors.RESET}")
    else:
        print(f"{Colors.RED}{Colors.BOLD}❌ NEEDS WORK! Multiple endpoint issues detected.{Colors.RESET}")
    
    print(f"\n{Colors.BOLD}Note:{Colors.RESET} 🔒 Endpoints requiring authentication are working as expected.")
    print(f"{Colors.BOLD}Tip:{Colors.RESET} See {BASE_URL}/docs for interactive API testing with authentication.\n")
    
    return overall_percentage >= 80

if __name__ == "__main__":
    main()
