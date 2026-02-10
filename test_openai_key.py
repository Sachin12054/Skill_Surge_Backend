"""
Test OpenAI API key validity
"""
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

def test_openai_key():
    """Test if OpenAI API key is valid"""
    print("=" * 80)
    print("Testing OpenAI API Key")
    print("=" * 80)
    
    # Load from config
    print("\n1. Loading API key from config...")
    try:
        from app.core.config import get_settings
        settings = get_settings()
        api_key = settings.OPENAI_API_KEY
        print(f"   ✓ API key loaded: {api_key[:20]}...{api_key[-4:]}")
    except Exception as e:
        print(f"   ✗ Failed to load config: {e}")
        return False
    
    # Test with OpenAI
    print("\n2. Testing API key with OpenAI...")
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key, timeout=30.0)
        
        print("   ⏳ Sending test request (may take 10-30 seconds)...")
        
        # Try a simple completion
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Say 'API key works!'"}],
            max_tokens=10
        )
        
        result = response.choices[0].message.content
        print(f"   ✓ API Response: {result}")
        print(f"   ✓ Model used: {response.model}")
        print(f"   ✓ Tokens used: {response.usage.total_tokens}")
        
        return True
        
    except Exception as e:
        print(f"   ✗ API call failed: {e}")
        return False

if __name__ == "__main__":
    success = test_openai_key()
    
    print("\n" + "=" * 80)
    if success:
        print("✅ OpenAI API Key is VALID and working with gpt-4o-mini")
    else:
        print("❌ OpenAI API Key test FAILED")
        print("\nPlease check:")
        print("  1. API key is correct in backend/.env")
        print("  2. API key has credits/quota remaining")
        print("  3. Network connection is working")
    print("=" * 80 + "\n")
    
    sys.exit(0 if success else 1)
