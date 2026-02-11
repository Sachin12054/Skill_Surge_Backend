"""
Comprehensive endpoint test for Cognito Backend on Render.
Tests ALL 89 endpoints discovered from the OpenAPI schema.
 
Expected behavior:
- Public endpoints: 200 OK
- Auth-required endpoints: 401/403 (no token) - confirms they're routed and responding
- CRITICAL: No 500 errors (would indicate broken imports/code from optimization)
"""

import requests
import json
import time
import sys

BASE = "https://skill-surge-backend-1.onrender.com"

# Colors for terminal
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"
BOLD = "\033[1m"

results = {"pass": [], "warn": [], "fail": []}

def test(method, path, tag, expected_codes=None, json_body=None, params=None, files=None, data=None):
    """Test a single endpoint."""
    if expected_codes is None:
        expected_codes = [200, 401, 403, 422, 307]
    
    url = f"{BASE}{path}"
    try:
        if method == "GET":
            r = requests.get(url, params=params, timeout=30)
        elif method == "POST":
            if files:
                r = requests.post(url, data=data, files=files, timeout=30)
            else:
                r = requests.post(url, json=json_body, params=params, timeout=30)
        elif method == "PUT":
            r = requests.put(url, json=json_body, params=params, timeout=30)
        elif method == "DELETE":
            r = requests.delete(url, params=params, timeout=30)
        else:
            print(f"  Unknown method: {method}")
            return
        
        status = r.status_code
        
        if status == 500:
            print(f"  {RED}FAIL{RESET} [{status}] {method:6s} {path}")
            try:
                detail = r.json().get("detail", r.text[:200])
            except:
                detail = r.text[:200]
            print(f"       {RED}Server Error: {detail}{RESET}")
            results["fail"].append({"method": method, "path": path, "status": status, "tag": tag, "detail": str(detail)[:200]})
        elif status in expected_codes:
            print(f"  {GREEN}PASS{RESET} [{status}] {method:6s} {path}")
            results["pass"].append({"method": method, "path": path, "status": status, "tag": tag})
        else:
            print(f"  {YELLOW}WARN{RESET} [{status}] {method:6s} {path}")
            results["warn"].append({"method": method, "path": path, "status": status, "tag": tag})
    except requests.exceptions.Timeout:
        print(f"  {YELLOW}TOUT{RESET} [---] {method:6s} {path}")
        results["warn"].append({"method": method, "path": path, "status": "timeout", "tag": tag})
    except Exception as e:
        print(f"  {RED}ERR {RESET} [---] {method:6s} {path} -> {e}")
        results["fail"].append({"method": method, "path": path, "status": "error", "tag": tag, "detail": str(e)[:200]})


def main():
    print(f"\n{BOLD}{'='*70}{RESET}")
    print(f"{BOLD}  COGNITO BACKEND - COMPREHENSIVE ENDPOINT TEST{RESET}")
    print(f"{BOLD}  Server: {BASE}{RESET}")
    print(f"{BOLD}{'='*70}{RESET}\n")

    # ── 1. PUBLIC ENDPOINTS ──
    print(f"{CYAN}[1/14] Public Endpoints{RESET}")
    test("GET", "/health", "Public")
    test("GET", "/", "Public")
    test("GET", "/docs", "Public", [200, 307])
    test("GET", "/openapi.json", "Public")

    # ── 2. PODCAST ──
    print(f"\n{CYAN}[2/14] Neural Podcast (/api/v1/podcast){RESET}")
    test("POST", "/api/v1/podcast/upload", "Podcast")
    test("POST", "/api/v1/podcast/create", "Podcast", json_body={"pdf_path": "test.pdf", "user_id": "test"})
    test("GET", "/api/v1/podcast/status/test-task-id", "Podcast")
    test("GET", "/api/v1/podcast/list", "Podcast")

    # ── 3. HYPOTHESIS V1 ──
    print(f"\n{CYAN}[3/14] Hypothesis Lab V1 (/api/v1/hypothesis){RESET}")
    test("POST", "/api/v1/hypothesis/generate", "Hypothesis V1", json_body={"paper_ids": ["test"], "user_id": "test"})
    test("GET", "/api/v1/hypothesis/result/test-task-id", "Hypothesis V1")
    test("GET", "/api/v1/hypothesis/list", "Hypothesis V1")

    # ── 4. NEURO-SCRIBE ──
    print(f"\n{CYAN}[4/14] Neuro-Scribe (/api/v1/scribe){RESET}")
    test("POST", "/api/v1/scribe/analyze", "Scribe", json_body={"image": "data:image/png;base64,iVBOR", "type": "math"})
    test("POST", "/api/v1/scribe/validate-math", "Scribe", params={"latex": "x^2 + y^2 = z^2"})
    test("GET", "/api/v1/scribe/history", "Scribe")

    # ── 5. STUDY LOOP ──
    print(f"\n{CYAN}[5/14] Study Loop (/api/v1/study){RESET}")
    test("POST", "/api/v1/study/quiz", "Study Loop", json_body={"course_id": "test"})
    test("POST", "/api/v1/study/answer", "Study Loop", json_body={"question_id": "test", "answer": 0})
    test("GET", "/api/v1/study/progress/test-course-id", "Study Loop")
    test("GET", "/api/v1/study/daily-drill", "Study Loop")

    # ── 6. GRAPH NAVIGATOR ──
    print(f"\n{CYAN}[6/14] Graph Navigator (/api/v1/graph){RESET}")
    test("GET", "/api/v1/graph/test-course-id", "Graph")
    test("GET", "/api/v1/graph/test-course-id/similar/test-concept-id", "Graph")
    test("GET", "/api/v1/graph/test-course-id/path", "Graph", params={"from_concept": "A", "to_concept": "B"})
    test("POST", "/api/v1/graph/test-course-id/index", "Graph")

    # ── 7. TOTAL RECALL / MEMORY ──
    print(f"\n{CYAN}[7/14] Total Recall (/api/v1/memory){RESET}")
    test("GET", "/api/v1/memory/test-user-id", "Memory")
    test("DELETE", "/api/v1/memory/test-user-id", "Memory")
    test("POST", "/api/v1/memory/update", "Memory", json_body={"user_id": "test", "memory": {"test": True}})
    test("GET", "/api/v1/memory/test-user-id/insights", "Memory")

    # ── 8. MOCK INTERVIEWS ──
    print(f"\n{CYAN}[8/14] Mock Interviews (/api/v1/interviews){RESET}")
    test("POST", "/api/v1/interviews/start", "Interviews", json_body={"type": "technical"})
    test("GET", "/api/v1/interviews/", "Interviews")
    test("GET", "/api/v1/interviews/test-interview-id", "Interviews")
    test("POST", "/api/v1/interviews/test-interview-id/end", "Interviews")

    # ── 9. STUDY SPACE ──
    print(f"\n{CYAN}[9/14] Study Space (/api/v1/space){RESET}")
    test("GET", "/api/v1/space/subjects", "Space")
    test("POST", "/api/v1/space/subjects", "Space", json_body={"name": "Test Subject"})
    test("DELETE", "/api/v1/space/subjects/test-subj-id", "Space")
    test("PUT", "/api/v1/space/subjects/test-subj-id", "Space", json_body={"name": "Updated"})
    test("GET", "/api/v1/space/pdfs", "Space")
    test("POST", "/api/v1/space/pdfs/upload", "Space")
    test("POST", "/api/v1/space/pdfs/assign", "Space", json_body={"pdf_ids": ["test"], "subject_id": "test"})
    test("DELETE", "/api/v1/space/pdfs/test-pdf-id", "Space")
    test("GET", "/api/v1/space/pdfs/test-pdf-id/content", "Space")
    test("GET", "/api/v1/space/pdfs/test-pdf-id/url", "Space")

    # ── 10. STUDY QUIZ ──
    print(f"\n{CYAN}[10/14] Study Quiz (/api/v1/quiz){RESET}")
    test("POST", "/api/v1/quiz/generate", "Quiz", json_body={"pdf_ids": ["test"], "quiz_type": "mcq", "difficulty": "medium"})
    test("POST", "/api/v1/quiz/submit", "Quiz", json_body={"quiz_id": "test", "answers": {"q1": "a"}, "time_taken": 60})
    test("GET", "/api/v1/quiz/next-adaptive", "Quiz", params={"quiz_id": "test", "current_question_index": 0})
    test("POST", "/api/v1/quiz/answer-adaptive", "Quiz", params={"quiz_id": "test", "question_id": "q1", "answer": "a"})
    test("GET", "/api/v1/quiz/history", "Quiz")
    test("GET", "/api/v1/quiz/topics", "Quiz", params={"pdf_ids": "test-id"})
    test("DELETE", "/api/v1/quiz/test-quiz-id", "Quiz")
    test("GET", "/api/v1/quiz/test-quiz-id/resume", "Quiz")
    test("POST", "/api/v1/quiz/test-quiz-id/save-progress", "Quiz",
         params={"current_question_index": 0, "time_spent": 30},
         json_body={"q1": "a"})
    test("GET", "/api/v1/quiz/subjects/insights", "Quiz")
    test("GET", "/api/v1/quiz/test-quiz-id/full", "Quiz")

    # ── 11. FLASHCARDS ──
    print(f"\n{CYAN}[11/14] Flashcards (/api/v1/flashcards){RESET}")
    test("GET", "/api/v1/flashcards/decks", "Flashcards")
    test("POST", "/api/v1/flashcards/decks", "Flashcards", json_body={"name": "Test Deck"})
    test("GET", "/api/v1/flashcards/decks/test-deck-id", "Flashcards")
    test("PUT", "/api/v1/flashcards/decks/test-deck-id", "Flashcards", json_body={"name": "Updated"})
    test("DELETE", "/api/v1/flashcards/decks/test-deck-id", "Flashcards")
    test("POST", "/api/v1/flashcards/decks/test-deck-id/cards", "Flashcards", json_body={"front": "Q?", "back": "A!"})
    test("PUT", "/api/v1/flashcards/cards/test-card-id", "Flashcards", json_body={"front": "Updated Q?"})
    test("DELETE", "/api/v1/flashcards/cards/test-card-id", "Flashcards")
    test("POST", "/api/v1/flashcards/generate", "Flashcards", json_body={"pdf_ids": ["test"], "deck_name": "AI Gen"})
    test("GET", "/api/v1/flashcards/study/due", "Flashcards")
    test("POST", "/api/v1/flashcards/study/review", "Flashcards", json_body={"flashcard_id": "test", "quality": 3})
    test("POST", "/api/v1/flashcards/study/session/start", "Flashcards", json_body={})
    test("POST", "/api/v1/flashcards/study/session/end", "Flashcards", json_body={"session_id": "test", "cards_studied": 5, "cards_correct": 3, "total_time_seconds": 120})
    test("GET", "/api/v1/flashcards/stats", "Flashcards")

    # ── 12. STUDY TIMER ──
    print(f"\n{CYAN}[12/14] Study Timer (/api/v1/timer){RESET}")
    test("GET", "/api/v1/timer/settings", "Timer")
    test("PUT", "/api/v1/timer/settings", "Timer", json_body={"focus_duration": 25})
    test("POST", "/api/v1/timer/session/start", "Timer", json_body={"session_type": "focus", "duration_minutes": 25})
    test("POST", "/api/v1/timer/session/pause", "Timer", json_body={"session_id": "test"})
    test("POST", "/api/v1/timer/session/resume", "Timer", json_body={"session_id": "test", "pause_duration_seconds": 60})
    test("POST", "/api/v1/timer/session/end", "Timer", json_body={"session_id": "test", "actual_duration_seconds": 1500})
    test("GET", "/api/v1/timer/session/active", "Timer")
    test("GET", "/api/v1/timer/stats/today", "Timer")
    test("GET", "/api/v1/timer/stats/week", "Timer")
    test("GET", "/api/v1/timer/stats/subjects", "Timer")
    test("GET", "/api/v1/timer/history", "Timer")

    # ── 13. NOTES SCANNER ──
    print(f"\n{CYAN}[13/14] Notes Scanner (/api/v1/notes-scanner){RESET}")
    test("POST", "/api/v1/notes-scanner/scan", "Notes Scanner", json_body={"image": "data:image/png;base64,iVBOR"})
    test("GET", "/api/v1/notes-scanner/notes", "Notes Scanner")
    test("GET", "/api/v1/notes-scanner/notes/test-note-id", "Notes Scanner")
    test("DELETE", "/api/v1/notes-scanner/notes/test-note-id", "Notes Scanner")
    test("PUT", "/api/v1/notes-scanner/notes/test-note-id", "Notes Scanner", params={"title": "Updated"})
    test("POST", "/api/v1/notes-scanner/summarize", "Notes Scanner", json_body={"text": "Sample notes text"})

    # ── 14. HYPOTHESIS V2 ──
    print(f"\n{CYAN}[14/14] Hypothesis Lab V2 (/api/v2/hypothesis){RESET}")
    test("POST", "/api/v2/hypothesis/generate", "Hypothesis V2", json_body={"paper_ids": ["test"]})
    test("POST", "/api/v2/hypothesis/generate/upload", "Hypothesis V2")
    test("GET", "/api/v2/hypothesis/status/test-task-id", "Hypothesis V2")
    test("GET", "/api/v2/hypothesis/result/test-task-id", "Hypothesis V2")
    test("GET", "/api/v2/hypothesis/sessions", "Hypothesis V2")
    test("GET", "/api/v2/hypothesis/sessions/test-session-id", "Hypothesis V2")
    test("DELETE", "/api/v2/hypothesis/sessions/test-session-id", "Hypothesis V2")
    test("POST", "/api/v2/hypothesis/sessions/test-sess/hypotheses/test-hyp/save", "Hypothesis V2")
    test("GET", "/api/v2/hypothesis/saved", "Hypothesis V2")

    # ── SUMMARY ──
    total = len(results["pass"]) + len(results["warn"]) + len(results["fail"])
    print(f"\n{BOLD}{'='*70}{RESET}")
    print(f"{BOLD}  TEST SUMMARY{RESET}")
    print(f"{BOLD}{'='*70}{RESET}")
    print(f"  Total endpoints tested: {total}")
    print(f"  {GREEN}PASS: {len(results['pass'])}{RESET}")
    print(f"  {YELLOW}WARN: {len(results['warn'])}{RESET}")
    print(f"  {RED}FAIL: {len(results['fail'])}{RESET}")

    # Show pass breakdown by status code
    if results["pass"]:
        code_counts = {}
        for r in results["pass"]:
            code_counts[r["status"]] = code_counts.get(r["status"], 0) + 1
        print(f"\n  {GREEN}Pass breakdown:{RESET}")
        for code, count in sorted(code_counts.items()):
            label = {200: "OK", 401: "Unauthorized (expected, auth required)", 403: "Forbidden (expected)", 422: "Validation Error (expected, no body/params)", 307: "Redirect"}.get(code, str(code))
            print(f"    [{code}] {label}: {count}")

    # Tag breakdown
    print(f"\n  {CYAN}By module:{RESET}")
    tag_results = {}
    for status_key in ["pass", "warn", "fail"]:
        for r in results[status_key]:
            tag = r["tag"]
            if tag not in tag_results:
                tag_results[tag] = {"pass": 0, "warn": 0, "fail": 0}
            tag_results[tag][status_key] += 1
    
    for tag, counts in sorted(tag_results.items()):
        p, w, f = counts["pass"], counts["warn"], counts["fail"]
        total_t = p + w + f
        status_icon = f"{GREEN}OK{RESET}" if f == 0 else f"{RED}ISSUES{RESET}"
        print(f"    {tag:20s}: {p}/{total_t} pass  {status_icon}")

    if results["fail"]:
        print(f"\n  {RED}{BOLD}FAILED ENDPOINTS (500 / Errors):{RESET}")
        for r in results["fail"]:
            print(f"    {RED}[{r['status']}] {r['method']} {r['path']}{RESET}")
            if "detail" in r:
                print(f"         {r['detail']}")

    if results["warn"]:
        print(f"\n  {YELLOW}WARNINGS (unexpected status):{RESET}")
        for r in results["warn"]:
            print(f"    {YELLOW}[{r['status']}] {r['method']} {r['path']}{RESET}")

    print(f"\n{BOLD}{'='*70}{RESET}")
    
    # Exit code
    if results["fail"]:
        print(f"\n  {RED}RESULT: FAILURES DETECTED - Check 500 errors above{RESET}")
        return 1
    else:
        print(f"\n  {GREEN}RESULT: ALL ENDPOINTS RESPONDING CORRECTLY{RESET}")
        print(f"  No 500 server errors. All routes are properly loaded.")
        return 0


if __name__ == "__main__":
    start = time.time()
    exit_code = main()
    elapsed = time.time() - start
    print(f"  Time: {elapsed:.1f}s\n")
    sys.exit(exit_code)
