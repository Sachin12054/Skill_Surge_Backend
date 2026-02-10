"""
Test script for Agentic Hypothesis Lab
Run this to verify all tools and agents work correctly
"""

import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.abspath('.'))

from app.agents.tools import (
    search_arxiv,
    search_semantic_scholar,
    check_hypothesis_novelty,
    score_hypothesis_testability,
    validate_statistical_claim,
)
from app.agents.hypothesis_agent_agentic import generate_hypotheses_agentic


def test_tools():
    """Test individual tools."""
    print("=" * 60)
    print("TESTING INDIVIDUAL TOOLS")
    print("=" * 60)
    
    # Test 1: ArXiv Search
    print("\n1️⃣  Testing ArXiv Search...")
    try:
        result = search_arxiv.invoke({"query": "machine learning", "max_results": 2})
        if result and len(result) > 0:
            print(f"   ✅ Found {len(result)} papers on ArXiv")
            print(f"   📄 Sample: {result[0].get('title', 'N/A')[:60]}...")
        else:
            print("   ⚠️  No results returned")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 2: Semantic Scholar Search
    print("\n2️⃣  Testing Semantic Scholar...")
    try:
        result = search_semantic_scholar.invoke({"query": "deep learning", "limit": 2})
        if result and len(result) > 0:
            print(f"   ✅ Found {len(result)} papers on Semantic Scholar")
            if "error" not in result[0]:
                print(f"   📊 Citations: {result[0].get('citations', 0)}")
        else:
            print("   ⚠️  No results returned")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 3: Novelty Check
    print("\n3️⃣  Testing Novelty Checker...")
    try:
        result = check_hypothesis_novelty.invoke({
            "hypothesis": "Combining transformers with reinforcement learning"
        })
        if result and "novelty_score" in result:
            print(f"   ✅ Novelty Score: {result['novelty_score']:.2f}")
            print(f"   💡 Assessment: {result.get('assessment', 'N/A')}")
        else:
            print("   ⚠️  No score returned")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 4: Testability Scorer
    print("\n4️⃣  Testing Testability Scorer...")
    try:
        result = score_hypothesis_testability.invoke({
            "hypothesis": "Increasing dataset size will improve model accuracy by 10%",
            "methodology": ["A/B testing", "Statistical analysis"]
        })
        if result and "testability_score" in result:
            print(f"   ✅ Testability: {result['testability_score']:.2f}")
            print(f"   🎯 Assessment: {result.get('assessment', 'N/A')}")
        else:
            print("   ⚠️  No score returned")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 5: Statistical Validator
    print("\n5️⃣  Testing Statistical Validator...")
    try:
        result = validate_statistical_claim.invoke({
            "claim": "The correlation between X and Y is significant at p<0.05",
            "data_description": "Randomized controlled trial with n=100"
        })
        if result and "valid" in result:
            print(f"   ✅ Valid: {result['valid']}")
            print(f"   📈 Confidence: {result.get('confidence', 0):.2f}")
            if result.get('warnings'):
                print(f"   ⚠️  Warnings: {len(result['warnings'])}")
        else:
            print("   ⚠️  No validation result")
    except Exception as e:
        print(f"   ❌ Error: {e}")


async def test_agentic_workflow():
    """Test the full agentic workflow."""
    print("\n" + "=" * 60)
    print("TESTING AGENTIC WORKFLOW")
    print("=" * 60)
    
    # Mock papers for testing
    test_papers = [
        {
            "id": "test_paper_1",
            "title": "Attention Mechanisms in Deep Learning",
            "content": """
            Abstract: This paper explores attention mechanisms in neural networks.
            We find that multi-head attention improves performance on various tasks.
            The key insight is that different heads learn different patterns.
            Experimental results show 15% improvement on image classification.
            """,
            "key_concepts": ["attention", "neural networks", "deep learning"],
        },
        {
            "id": "test_paper_2",
            "title": "Reinforcement Learning for Control Tasks",
            "content": """
            Abstract: We apply reinforcement learning to robotic control.
            Policy gradient methods show promising results on continuous control.
            Our experiments demonstrate stable learning on challenging tasks.
            Results indicate 20% improvement over baseline methods.
            """,
            "key_concepts": ["reinforcement learning", "control", "policy gradients"],
        },
    ]
    
    print("\n🤖 Starting Agentic Hypothesis Generation...")
    print(f"   📄 Using {len(test_papers)} test papers")
    print(f"   🎯 Focus: Combining attention with RL\n")
    
    try:
        result = await generate_hypotheses_agentic(
            papers=test_papers,
            focus_area="Combining attention mechanisms with reinforcement learning"
        )
        
        if result.get("success"):
            print("✅ AGENTIC WORKFLOW SUCCEEDED!\n")
            
            # Show hypotheses
            hypotheses = result.get("hypotheses", [])
            print(f"📊 Generated {len(hypotheses)} hypotheses:")
            for i, hyp in enumerate(hypotheses, 1):
                print(f"\n   {i}. {hyp.get('title', 'Untitled')}")
                print(f"      Testability: {hyp.get('testability_score', 0):.2f}")
                print(f"      Novelty: {hyp.get('novelty_score', 0):.2f}")
                print(f"      Confidence: {hyp.get('confidence', 0):.2f}")
            
            # Show agent activity
            messages = result.get("agent_messages", [])
            if messages:
                print(f"\n🗨️  Agent Activity ({len(messages)} messages):")
                for msg in messages[:5]:  # Show first 5
                    role = msg.get("role", "unknown")
                    content = msg.get("content", "")[:80]
                    print(f"   [{role}]: {content}...")
            
            # Show tool results
            tool_results = result.get("tool_results", {})
            if tool_results:
                print(f"\n🔧 Tool Usage:")
                for agent, data in tool_results.items():
                    if isinstance(data, dict) and data.get("completed"):
                        calls = data.get("tool_calls", 0)
                        print(f"   {agent}: {calls} tool calls")
            
            print("\n✨ All systems operational!")
            
        else:
            error = result.get("error", "Unknown error")
            print(f"❌ WORKFLOW FAILED: {error}")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Run all tests."""
    print("\n" + "🚀" * 30)
    print("AGENTIC HYPOTHESIS LAB - SYSTEM TEST")
    print("🚀" * 30)
    
    # Test tools
    test_tools()
    
    # Test agentic workflow
    asyncio.run(test_agentic_workflow())
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)
    print("\nIf all tests passed, the system is ready! 🎉")
    print("Run the FastAPI server with: uvicorn app.main:app --reload")
    print()


if __name__ == "__main__":
    main()
