#!/usr/bin/env python3
"""
Debug script to identify OpenAI quota issues.
"""

import os
import sys
from openai import OpenAI

def check_environment():
    """Check environment variables and API key."""
    print("🔍 Environment Check")
    print("=" * 30)
    
    api_key = os.getenv('OPENAI_API_KEY')
    if api_key:
        # Mask the key for security
        masked_key = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "***"
        print(f"✅ API Key found: {masked_key}")
        print(f"   Length: {len(api_key)} characters")
        print(f"   Starts with: {api_key[:8]}")
    else:
        print("❌ OPENAI_API_KEY not found in environment")
        return False
    
    return True

def test_simple_api_call():
    """Test a very simple API call to isolate the issue."""
    print("\n🧪 Simple API Test")
    print("=" * 30)
    
    try:
        client = OpenAI()
        
        # Very simple, low-cost test
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # Cheapest model
            messages=[
                {"role": "user", "content": "Say 'Hello'"}
            ],
            max_tokens=5,  # Minimal tokens
            temperature=0
        )
        
        print("✅ Simple API call successful!")
        print(f"   Response: {response.choices[0].message.content}")
        print(f"   Model: {response.model}")
        print(f"   Usage: {response.usage}")
        
        return True
        
    except Exception as e:
        print(f"❌ Simple API call failed: {e}")
        return False

def test_account_info():
    """Try to get account information."""
    print("\n👤 Account Information Test")
    print("=" * 30)
    
    try:
        client = OpenAI()
        
        # Try to get models (this is a free endpoint)
        models = client.models.list()
        print("✅ Models endpoint accessible")
        print(f"   Found {len(models.data)} models")
        
        # Show some available models
        model_names = [model.id for model in models.data[:5]]
        print(f"   Sample models: {', '.join(model_names)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Account info test failed: {e}")
        return False

def test_quota_specific():
    """Test with the exact same parameters as your failing code."""
    print("\n🎯 Quota-Specific Test")
    print("=" * 30)
    
    try:
        client = OpenAI()
        
        # Test with the same model and settings as your categorizer
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Test message"}
            ],
            temperature=0.1,
            max_tokens=2000
        )
        
        print("✅ Quota-specific test successful!")
        print(f"   Model: {response.model}")
        print(f"   Usage: {response.usage}")
        
        return True
        
    except Exception as e:
        print(f"❌ Quota-specific test failed: {e}")
        print(f"   Error type: {type(e).__name__}")
        
        # Check if it's specifically a quota error
        error_str = str(e).lower()
        if 'quota' in error_str or '429' in error_str:
            print("   🚨 This is a quota/billing error!")
        elif 'api' in error_str and 'key' in error_str:
            print("   🔑 This is an API key error!")
        elif 'rate' in error_str and 'limit' in error_str:
            print("   ⏱️ This is a rate limit error!")
        
        return False

def main():
    print("🔧 OpenAI Quota Debug Tool")
    print("=" * 40)
    print("This will help identify why you're getting quota errors")
    print("despite having $120 in credits.\n")
    
    # Step 1: Check environment
    if not check_environment():
        print("\n❌ Cannot proceed without API key")
        return
    
    # Step 2: Test account access
    if not test_account_info():
        print("\n❌ Cannot access OpenAI account")
        return
    
    # Step 3: Simple API test
    if not test_simple_api_call():
        print("\n❌ Basic API calls failing")
        return
    
    # Step 4: Test with your exact settings
    if not test_quota_specific():
        print("\n❌ Your specific settings are causing issues")
        print("\n💡 Possible solutions:")
        print("   1. Check if you have usage limits set")
        print("   2. Verify billing is properly configured")
        print("   3. Try a different model (gpt-3.5-turbo)")
        print("   4. Check for rate limits")
        return
    
    print("\n✅ All tests passed! Your API should be working.")
    print("💡 The issue might be in your specific code or settings.")

if __name__ == "__main__":
    main()
