"""
Test the agentic hypothesis generation API endpoint
"""
import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_agentic_hypothesis():
    """Test the agentic hypothesis generation endpoint"""
    
    print("=" * 80)
    print("Testing Agentic Hypothesis Generation API")
    print("=" * 80)
    
    # Test papers
    papers = [
        {
            "title": "Attention Is All You Need",
            "content": "We propose the Transformer, a model architecture based solely on attention mechanisms, dispensing with recurrence and convolutions entirely. The model achieves superior results in machine translation tasks.",
            "source": "arxiv"
        },
        {
            "title": "BERT: Pre-training of Deep Bidirectional Transformers",
            "content": "We introduce BERT, which stands for Bidirectional Encoder Representations from Transformers. BERT is designed to pre-train deep bidirectional representations by jointly conditioning on both left and right context.",
            "source": "arxiv"
        }
    ]
    
    # API endpoint
    url = f"{BASE_URL}/api/v2/hypothesis/generate"
    
    # Request payload with agentic mode enabled
    payload = {
        "papers": papers,
        "focus_area": "transformer architectures and attention mechanisms",
        "num_hypotheses": 3,
        "use_agentic": True  # Enable agentic mode with tool-using agents
    }
    
    print(f"\n📤 Sending request to {url}")
    print(f"   Papers: {len(papers)}")
    print(f"   Focus area: {payload['focus_area']}")
    print(f"   Agentic mode: {payload['use_agentic']}")
    print(f"   Requested hypotheses: {payload['num_hypotheses']}")
    
    try:
        # Send POST request
        print("\n⏳ Generating hypotheses (this may take 30-60 seconds)...\n")
        response = requests.post(url, json=payload, timeout=120)
        
        # Check response
        if response.status_code == 200:
            result = response.json()
            task_id = result.get("task_id")
            
            print(f"✅ Request accepted!")
            print(f"   Task ID: {task_id}")
            print(f"   Mode: {result.get('mode', 'unknown')}")
            
            # Poll for results
            print("\n⏳ Waiting for generation to complete...")
            status_url = f"{BASE_URL}/api/v2/hypothesis/status/{task_id}"
            
            max_attempts = 60
            attempt = 0
            
            while attempt < max_attempts:
                time.sleep(2)
                attempt += 1
                
                status_response = requests.get(status_url)
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    current_status = status_data.get("status")
                    
                    if current_status == "completed":
                        print(f"\n✅ Generation completed!")
                        
                        # Display results
                        hypotheses = status_data.get("hypotheses", [])
                        print(f"\n{'=' * 80}")
                        print(f"Generated {len(hypotheses)} Hypotheses:")
                        print(f"{'=' * 80}\n")
                        
                        for i, hyp in enumerate(hypotheses, 1):
                            print(f"\n{'─' * 80}")
                            print(f"Hypothesis {i}:")
                            print(f"{'─' * 80}")
                            print(f"Statement: {hyp.get('hypothesis', 'N/A')}")
                            print(f"\nRationale: {hyp.get('rationale', 'N/A')[:200]}...")
                            print(f"\nTestability: {hyp.get('testability_score', 0):.1f}/10")
                            print(f"Novelty: {hyp.get('novelty_score', 0):.1f}/10")
                            print(f"Confidence: {hyp.get('confidence_score', 0):.1f}/10")
                            
                            if hyp.get('key_concepts'):
                                print(f"\nKey Concepts: {', '.join(hyp['key_concepts'])}")
                        
                        # Display agent information if available
                        if status_data.get("agent_messages"):
                            print(f"\n\n{'=' * 80}")
                            print("Agent Activity:")
                            print(f"{'=' * 80}")
                            messages = status_data["agent_messages"]
                            print(f"Total messages: {len(messages)}")
                            print(f"Sample: {messages[0] if messages else 'None'}")
                        
                        if status_data.get("tool_usage"):
                            print(f"\n{'=' * 80}")
                            print("Tool Usage:")
                            print(f"{'=' * 80}")
                            for tool, count in status_data["tool_usage"].items():
                                print(f"  • {tool}: {count} times")
                        
                        return True
                        
                    elif current_status == "failed":
                        print(f"\n❌ Generation failed!")
                        print(f"   Error: {status_data.get('error', 'Unknown error')}")
                        return False
                        
                    elif current_status == "processing":
                        progress = status_data.get("progress", 0)
                        print(f"   Progress: {progress}% (attempt {attempt}/{max_attempts})", end="\r")
                    
            print(f"\n⏱️ Timeout: Generation took too long (>{max_attempts * 2}s)")
            return False
            
        else:
            print(f"\n❌ Request failed!")
            print(f"   Status code: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print(f"\n❌ Request timed out!")
        return False
    except requests.exceptions.ConnectionError:
        print(f"\n❌ Could not connect to server!")
        print(f"   Make sure the backend is running on {BASE_URL}")
        return False
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False


def test_health():
    """Test if the server is running"""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print(f"✅ Server is healthy")
            return True
        else:
            print(f"⚠️ Server responded with status {response.status_code}")
            return False
    except:
        print(f"❌ Server is not responding at {BASE_URL}")
        return False


if __name__ == "__main__":
    print("\n🔍 Checking server health...")
    if not test_health():
        print("\n💡 Make sure to start the backend server:")
        print("   cd backend")
        print("   python -m uvicorn app.main:app --reload")
        exit(1)
    
    print("\n" + "=" * 80)
    print("Starting Agentic Hypothesis Generation Test")
    print("=" * 80)
    
    success = test_agentic_hypothesis()
    
    print("\n" + "=" * 80)
    if success:
        print("✅ TEST PASSED - Agentic system is working!")
    else:
        print("❌ TEST FAILED - Check logs for details")
    print("=" * 80 + "\n")
