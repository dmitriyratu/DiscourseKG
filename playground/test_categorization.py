#!/usr/bin/env python3
import json
import sys
import os
import requests

from src.analysis.openai_categorizer import OpenAICategorizer, categorize_speech_file

# +
# Path to the existing speech file
speech_file = "../data/raw/donald_trump/speeches/2025/09/23/speech_un_091500.json"

with open(speech_file, 'r', encoding='utf-8') as f:
    speech_data = json.load(f)
# -

speech_data.keys()

def summarize_with_ollama(text, target_words=5000, model="llama3.2"):
    """
    Summarize text using Ollama Llama 3.2 locally.
    
    Args:
        text: Input text to summarize
        target_words: Target word count for summary
        model: Ollama model to use (default: llama3.2)
    
    Returns:
        Summarized text
    """
    # Ollama API endpoint (runs locally)
    url = "http://localhost:11434/api/generate"
    
    # Create prompt for summarization
    prompt = f"""Please summarize the following speech transcript, reducing it from approximately {len(text.split())} words to approximately {target_words} words. 

Maintain the key points, main themes, and important details while preserving the speaker's tone and style. Focus on the most significant content.

Speech transcript:
{text}

Summary:"""
    
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.3,  # Lower temperature for more consistent summarization
            "top_p": 0.9,
            "max_tokens": 2000  # Adjust based on your target length
        }
    }
    
    try:
        response = requests.post(url, json=payload, timeout=300)
        response.raise_for_status()
        
        result = response.json()
        summary = result.get('response', '').strip()
        
        return summary
        
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to Ollama. Make sure it's running:")
        print("   1. Install Ollama: https://ollama.ai")
        print("   2. Run: ollama run llama3.2")
        print("   3. Ensure Ollama is running on localhost:11434")
        return None
    except Exception as e:
        print(f"❌ Error with Ollama: {e}")
        return None

def check_ollama_status():
    """Check if Ollama is running and llama3.2 is available."""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get('models', [])
            available_models = [model['name'] for model in models]
            
            if 'llama3.2' in available_models:
                print("✅ Ollama is running with llama3.2 model available")
                return True
            else:
                print("❌ llama3.2 model not found. Available models:")
                for model in available_models:
                    print(f"   - {model}")
                print("\nTo install llama3.2: ollama run llama3.2")
                return False
        else:
            print("❌ Ollama is not responding")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Ollama is not running. Please start it first.")
        return False
    except Exception as e:
        print(f"❌ Error checking Ollama: {e}")
        return False

# Test Ollama integration
print("\n🔍 Checking Ollama status...")
if check_ollama_status():
    print("\n📝 Testing summarization with Ollama Llama 3.2...")
    
    # Get the transcript
    transcript = speech_data['transcript']
    original_words = len(transcript.split())
    target_words = 5000  # Target: 10k → 5k words
    
    print(f"Original: {original_words:,} words")
    print(f"Target: {target_words:,} words")
    print("Summarizing... (this may take a few minutes)")
    
    # Summarize using Ollama
    summary = summarize_with_ollama(transcript, target_words)
    
    if summary:
        summary_words = len(summary.split())
        reduction_percent = ((original_words - summary_words) / original_words) * 100
        
        print(f"\n✅ Summarization complete!")
        print(f"Summary: {summary_words:,} words")
        print(f"Reduction: {reduction_percent:.1f}%")
        print(f"\n📄 Summary preview (first 200 words):")
        print(f"{summary[:200]}...")
        
        # Now you can send this summary to OpenAI for categorization
        print(f"\n💡 Next step: Send this {summary_words:,} word summary to OpenAI")
        print(f"   Cost savings: ~{reduction_percent:.0f}% reduction in API costs")
    else:
        print("❌ Summarization failed. Please check Ollama setup.")
else:
    print("\n💡 To use Ollama summarization:")
    print("1. Install Ollama: https://ollama.ai")
    print("2. Run: ollama run llama3.2")
    print("3. Restart this script")











# +
# Categorize the speech
result = categorize_speech_file(speech_file)

print("✅ Categorization successful!")
print("\n📊 Results:")
print(f"Primary Topics: {result.get('primary_topics', [])}")
print(f"Secondary Topics: {result.get('secondary_topics', [])}")
print(f"Overall Sentiment: {result.get('sentiment', {}).get('overall', 'N/A')}")
print(f"Summary: {result.get('summary', 'N/A')}")
# -





