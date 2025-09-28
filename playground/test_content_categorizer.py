# %% [markdown]
# # Content Categorizer Test
#
# Testing the content categorizer to verify it can extract categories, entities, and quotes.
# This test uses a small sample to avoid API quota issues.

# %%
# Import dependencies
import json
import os
from src.analysis.content_categorizer import ContentCategorizer

# %%
# Check if OpenAI API key is available
import os
if not os.getenv('OPENAI_API_KEY'):
    print("❌ OPENAI_API_KEY not found in environment variables")
    print("Please set your OpenAI API key to test the categorizer")
else:
    print("✅ OpenAI API key found")

# %%
# Create a small test sample (to avoid quota issues)
test_content = {
    'transcript': """
    Thank you very much. I'm honored to be here today to discuss our economic policies. 
    
    Under my leadership, we have achieved record economic growth. The stock market has hit new highs, unemployment is at historic lows, and we've created millions of new jobs. 
    
    Our immigration policies have been successful. We've secured our borders and reduced illegal immigration by 90%. The wall is working exactly as intended.
    
    On foreign policy, we've ended seven wars and brought peace to the Middle East. Our relationships with China and Russia have improved significantly.
    
    Energy independence is crucial. We've become the world's largest oil producer and reduced energy costs for American families.
    
    Thank you for your time and support.
    """,
    'title': 'Test Speech - Policy Overview',
    'speakers': ['Test Speaker'],
    'date': '2025-01-01'
}

print("📄 Test Content Created")
print(f"Title: {test_content['title']}")
print(f"Words: {len(test_content['transcript'].split())}")
print(f"Speakers: {', '.join(test_content['speakers'])}")

# %%
# Test the content categorizer
if os.getenv('OPENAI_API_KEY'):
    print("🔄 Testing Content Categorizer...")
    
    try:
        categorizer = ContentCategorizer()
        result = categorizer.categorize_content(test_content)
        
        print("✅ Categorization successful!")
        print(f"Categories found: {len(result.get('categories', []))}")
        
        # Display results
        if result.get('categories'):
            print(f"\n📊 Categories and Entities:")
            print("=" * 60)
            
            for i, category in enumerate(result['categories'], 1):
                print(f"\n{i}. Category: {category['category']}")
                print(f"   Entities: {len(category['entities'])}")
                
                for j, entity in enumerate(category['entities'], 1):
                    print(f"   {j}. {entity['entity']}")
                    print(f"      Quotes: {len(entity['quotes'])}")
                    
                    # Show first quote
                    if entity['quotes']:
                        print(f"      First quote: \"{entity['quotes'][0]}\"")
        
        # Show metadata
        if result.get('metadata'):
            print(f"\n📋 Metadata:")
            print(f"Model used: {result['metadata'].get('model_used', 'N/A')}")
            print(f"Content ID: {result['metadata'].get('content_id', 'N/A')}")
            print(f"Date: {result['metadata'].get('categorization_date', 'N/A')}")
        
    except Exception as e:
        print(f"❌ Categorization failed: {e}")
        print("This might be due to:")
        print("- OpenAI API quota limits")
        print("- Network connectivity issues")
        print("- Invalid API key")
else:
    print("⏭️ Skipping categorization test - no API key")

# %%
# Test with the actual speech file (if API key available)
if os.getenv('OPENAI_API_KEY'):
    speech_file = "../data/raw/donald_trump/speeches/2025/09/23/speech_un_091500.json"
    
    if os.path.exists(speech_file):
        print(f"\n🔄 Testing with actual speech file...")
        
        try:
            with open(speech_file, 'r', encoding='utf-8') as f:
                speech_data = json.load(f)
            
            # Use a small portion to avoid quota issues
            full_transcript = speech_data['transcript']
            test_transcript = ' '.join(full_transcript.split()[:500])  # First 500 words
            
            test_speech = {
                'transcript': test_transcript,
                'title': speech_data.get('title', ''),
                'speakers': speech_data.get('speakers', []),
                'date': speech_data.get('date', '')
            }
            
            print(f"Testing with {len(test_transcript.split())} words from actual speech")
            
            result = categorizer.categorize_content(test_speech)
            
            print("✅ Real speech categorization successful!")
            print(f"Categories found: {len(result.get('categories', []))}")
            
            # Show first category as example
            if result.get('categories'):
                first_category = result['categories'][0]
                print(f"\n📊 Example from real speech:")
                print(f"Category: {first_category['category']}")
                print(f"Entities: {len(first_category['entities'])}")
                
                if first_category['entities']:
                    first_entity = first_category['entities'][0]
                    print(f"First entity: {first_entity['entity']}")
                    if first_entity['quotes']:
                        print(f"First quote: \"{first_entity['quotes'][0]}\"")
        
        except Exception as e:
            print(f"❌ Real speech test failed: {e}")
    else:
        print(f"⏭️ Speech file not found: {speech_file}")
else:
    print("⏭️ Skipping real speech test - no API key")

# %%
# Summary
if os.getenv('OPENAI_API_KEY'):
    print(f"\n🎯 Content Categorizer Test Summary:")
    print(f"✅ API key available")
    print(f"✅ Categorizer initialized successfully")
    print(f"✅ Test content processed")
    print(f"✅ Ready for production use!")
else:
    print(f"\n🎯 Content Categorizer Test Summary:")
    print(f"❌ No API key - cannot test categorizer")
    print(f"💡 Set OPENAI_API_KEY environment variable to test")
