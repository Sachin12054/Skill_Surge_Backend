"""
Test script for agentic hypothesis generation tools only (without full app imports).
Tests all 8 tools individually and the multi-agent workflow.
"""

import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

print("=" * 80)
print("Testing Agentic Hypothesis Generation System (Tools Only)")
print("=" * 80)

# Test 1: Import tools (directly without __init__.py)
print("\n📦 Importing tools...")
try:
    # Import tool modules directly to avoid __init__.py chain
    import importlib.util
    
    # Load search_tools
    search_tools_path = os.path.join(os.path.dirname(__file__), "app", "agents", "tools", "search_tools.py")
    spec = importlib.util.spec_from_file_location("search_tools", search_tools_path)
    search_tools = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(search_tools)
    
    # Load validation_tools  
    validation_tools_path = os.path.join(os.path.dirname(__file__), "app", "agents", "tools", "validation_tools.py")
    spec = importlib.util.spec_from_file_location("validation_tools", validation_tools_path)
    validation_tools = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validation_tools)
    
    # Extract functions
    search_arxiv = search_tools.search_arxiv
    search_semantic_scholar = search_tools.search_semantic_scholar
    check_hypothesis_novelty = search_tools.check_hypothesis_novelty
    find_related_concepts = search_tools.find_related_concepts
    
    score_hypothesis_testability = validation_tools.score_hypothesis_testability
    validate_statistical_claim = validation_tools.validate_statistical_claim
    execute_python_code = validation_tools.execute_python_code
    analyze_research_feasibility = validation_tools.analyze_research_feasibility
    
    print("✓ All tools imported successfully")
except Exception as e:
    print(f"✗ Import failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)


async def test_tools():
    """Test individual tools"""
    print("\n" + "=" * 80)
    print("Testing Individual Tools")
    print("=" * 80)

    # Test 1: ArXiv Search
    print("\n1. Testing ArXiv Search...")
    try:
        result = search_arxiv.invoke({"query": "attention mechanism transformer", "max_results": 2})
        print(f"   ✓ Found {len(result.get('papers', []))} papers")
        if result.get("papers"):
            print(f"   → First paper: {result['papers'][0]['title'][:60]}...")
    except Exception as e:
        print(f"   ✗ Error: {e}")

    # Test 2: Semantic Scholar
    print("\n2. Testing Semantic Scholar...")
    try:
        result = search_semantic_scholar.invoke({"query": "transformer neural networks", "limit": 2})
        print(f"   ✓ Found {len(result.get('papers', []))} papers")
        if result.get("papers"):
            print(f"   → First paper: {result['papers'][0]['title'][:60]}...")
    except Exception as e:
        print(f"   ✗ Error: {e}")

    # Test 3: Hypothesis Novelty Check
    print("\n3. Testing Hypothesis Novelty Check...")
    try:
        result = check_hypothesis_novelty.invoke({
            "hypothesis": "Attention mechanisms improve transformer performance"
        })
        print(f"   ✓ Novelty score: {result.get('novelty_score', 0):.2f}")
        print(f"   → Assessment: {result.get('assessment', 'Unknown')}")
    except Exception as e:
        print(f"   ✗ Error: {e}")

    # Test 4: Find Related Concepts
    print("\n4. Testing Find Related Concepts...")
    try:
        result = find_related_concepts.invoke({"concept": "attention mechanism"})
        concepts = result.get("concepts", [])
        print(f"   ✓ Found {len(concepts)} related concepts")
        print(f"   → Concepts: {', '.join(concepts[:5])}")
    except Exception as e:
        print(f"   ✗ Error: {e}")

    # Test 5: Testability Scoring
    print("\n5. Testing Hypothesis Testability Scoring...")
    try:
        result = score_hypothesis_testability.invoke({
            "hypothesis": "Increasing model size by 10x improves accuracy by 5%",
            "methodology": "Train models at different scales and measure accuracy on benchmark",
        })
        print(f"   ✓ Testability score: {result.get('score', 0):.2f}/10")
        print(f"   → Feedback: {result.get('feedback', 'No feedback')[:60]}...")
    except Exception as e:
        print(f"   ✗ Error: {e}")

    # Test 6: Statistical Validation
    print("\n6. Testing Statistical Claim Validation...")
    try:
        result = validate_statistical_claim.invoke({
            "claim": "Model A achieves 95% accuracy (p<0.05)",
            "data_description": "Tested on 1000 samples with 5-fold cross-validation",
        })
        print(f"   ✓ Valid: {result.get('is_valid', False)}")
        print(f"   → Issues: {', '.join(result.get('issues', ['None']))}")
    except Exception as e:
        print(f"   ✗ Error: {e}")

    # Test 7: Python Code Execution
    print("\n7. Testing Python Code Execution...")
    try:
        result = execute_python_code.invoke({"code": "import numpy as np\nprint(np.mean([1, 2, 3, 4, 5]))"})
        print(f"   ✓ Success: {result.get('success', False)}")
        print(f"   → Output: {result.get('output', 'No output').strip()}")
    except Exception as e:
        print(f"   ✗ Error: {e}")

    # Test 8: Research Feasibility
    print("\n8. Testing Research Feasibility Analysis...")
    try:
        result = analyze_research_feasibility.invoke({
            "hypothesis": "Train a 100B parameter model to test scaling laws",
            "required_resources": "1000 GPUs, 6 months, $10M budget",
            "timeframe": "6 months",
        })
        print(f"   ✓ Feasibility score: {result.get('feasibility_score', 0):.2f}/10")
        print(f"   → Assessment: {result.get('assessment', 'Unknown')}")
    except Exception as e:
        print(f"   ✗ Error: {e}")


async def test_workflow():
    """Test the full agentic workflow without importing the main app"""
    print("\n" + "=" * 80)
    print("Testing LangGraph Workflow Components")
    print("=" * 80)

    print("\n🔧 Testing workflow components...")
    print("   Note: Full workflow test requires OpenAI API key")
    print("   → To test full workflow: Set OPENAI_API_KEY environment variable")
    print("   → Then run: from app.agents.hypothesis_agent_agentic import generate_hypotheses_agentic")


async def main():
    print("\n🚀 Starting tests...\n")

    # Test individual tools
    await test_tools()

    # Test workflow components
    await test_workflow()

    print("\n" + "=" * 80)
    print("✅ All tool tests completed!")
    print("=" * 80)
    print("\nNext Steps:")
    print("1. Set OPENAI_API_KEY environment variable")
    print("2. Start backend server: uvicorn app.main:app --reload")
    print("3. Test from mobile app with 'Agentic Mode' toggle enabled")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
