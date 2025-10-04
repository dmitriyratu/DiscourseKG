# %%
"""
Full Pipeline Test: JSON Load -> Summarize -> Categorize
Jupyter-compatible version with cell-by-cell execution

This script demonstrates the complete pipeline:
1. Load a real JSON file from the data directory
2. Summarize the content to ~5k tokens using ExtractiveSummarizer
3. Pass the summarized content through ContentCategorizer
4. Display comprehensive results and analysis

Run each cell sequentially to see how each part of the pipeline works.
"""

# %%
# Cell 1: Imports and Setup
import sys
import os
import json
import tiktoken
import time
from pathlib import Path
import pandas as pd
from pprint import pprint


from src.preprocessing.extractive_summarizer import ExtractiveSummarizer
from src.processing.content_categorizer import ContentCategorizer
from src.config import config

print("[OK] All imports successful!")

# %%
# Cell 2: Utility Functions
def count_tokens(text: str) -> int:
    """Count tokens using tiktoken"""
    tokenizer = tiktoken.get_encoding("cl100k_base")
    return len(tokenizer.encode(text))

def load_json_file(file_path: str) -> dict:
    """Load and validate JSON file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Validate required fields
        required_fields = ['id', 'title', 'transcript', 'speakers', 'date']
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")
        
        return data
    except Exception as e:
        raise Exception(f"Failed to load JSON file {file_path}: {e}")

print("[OK] Utility functions defined!")

# %%
# Cell 3: Configuration and File Path Setup
# Configuration
# Get project root directory (parent of playground)
project_root = Path(__file__).parent.parent
json_file_path = project_root / "data/raw/donald_trump/speeches/2025/09/23/speech_un_091500.json"
target_words = 3750  # Target ~5k tokens
output_file = project_root / "playground/full_pipeline_test_results.json"

print(f"Configuration:")
print(f"  Input file: {json_file_path}")
print(f"  Target words: {target_words}")
print(f"  Output file: {output_file}")

# Check if file exists
if not json_file_path.exists():
    print(f"[ERROR] JSON file not found: {json_file_path}")
    print("Please ensure the file exists before proceeding.")
else:
    print("[OK] Input file found!")

# %%
# Cell 4: Step 1 - Load JSON File
print("=" * 60)
print("STEP 1: LOADING JSON FILE")
print("=" * 60)

try:
    content_data = load_json_file(json_file_path)
    print(f"[OK] Successfully loaded: {content_data['title']}")
    
    # Extract key information
    original_transcript = content_data['transcript']
    original_tokens = count_tokens(original_transcript)
    original_words = len(original_transcript.split())
    
    print(f"\n[INFO] File Information:")
    print(f"  ID: {content_data['id']}")
    print(f"  Date: {content_data['date']}")
    print(f"  Speakers: {', '.join(content_data['speakers'])}")
    print(f"  Length: {len(original_transcript)} characters")
    print(f"  Words: {original_words:,}")
    print(f"  Tokens: {original_tokens:,}")
    
    # Show first 200 characters
    print(f"\n[TEXT] Content Preview:")
    print(f"  {original_transcript[:200]}...")
    
except Exception as e:
    print(f"[ERROR] Failed to load JSON: {e}")
    content_data = None

# %%
# Cell 5: Step 2 - Initialize ExtractiveSummarizer
print("=" * 60)
print("STEP 2: INITIALIZING EXTRACTIVE SUMMARIZER")
print("=" * 60)

try:
    summarizer = ExtractiveSummarizer()
    print("[OK] ExtractiveSummarizer initialized successfully!")
    
    # Show summarizer configuration
    print(f"\n[CONFIG] Summarizer Configuration:")
    print(f"  Model: all-MiniLM-L6-v2 (SentenceTransformer)")
    print(f"  Tokenizer: cl100k_base (tiktoken)")
    
except Exception as e:
    print(f"[ERROR] Failed to initialize summarizer: {e}")
    summarizer = None

# %%
# Cell 6: Step 3 - Summarize Content
print("=" * 60)
print("STEP 3: SUMMARIZING CONTENT")
print("=" * 60)

if summarizer and content_data:
    try:
        print(f"[TEXT] Summarizing {original_words:,} words to ~{target_words:,} words...")
        print("This may take a few moments...")
        
        start_time = time.time()
        summarized_text = summarizer.summarize(original_transcript, target_words)
        summarization_time = time.time() - start_time
        
        if not summarized_text:
            print("[ERROR] Summarization failed - no summary returned")
        else:
            summary_tokens = count_tokens(summarized_text)
            summary_words = len(summarized_text.split())
            compression_ratio = len(summarized_text) / len(original_transcript)
            
            print(f"[OK] Summarization completed in {summarization_time:.2f} seconds!")
            print(f"\n[INFO] Summarization Results:")
            print(f"  Original: {original_words:,} words, {original_tokens:,} tokens")
            print(f"  Summary: {summary_words:,} words, {summary_tokens:,} tokens")
            print(f"  Compression: {compression_ratio:.1%}")
            print(f"  Target achieved: {'[OK]' if summary_tokens <= 5000 else '[WARNING]'}")
            
            # Show summary preview
            print(f"\n[TEXT] Summary Preview (first 300 characters):")
            print(f"  {summarized_text[:300]}...")
            
            # Show raw summarization data
            print(f"\n[RAW] Summarization Object:")
            print(f"  Type: {type(summarized_text)}")
            print(f"  Length: {len(summarized_text)} characters")
            print(f"  Full text:\n{summarized_text}")
            
            # Update content data
            content_data['transcript'] = summarized_text
            content_data['original_transcript'] = original_transcript
            
    except Exception as e:
        print(f"[ERROR] Summarization failed: {e}")
        import traceback
        traceback.print_exc()
        summarized_text = None
else:
    print("[ERROR] Cannot proceed - summarizer or content data not available")
    summarized_text = None

# %%
# Cell 7: Step 4 - Initialize ContentCategorizer
print("=" * 60)
print("STEP 4: INITIALIZING CONTENT CATEGORIZER")
print("=" * 60)

try:
    categorizer = ContentCategorizer()
    print("[OK] ContentCategorizer initialized successfully!")
    
    print(f"\n[AI] LLM Configuration:")
    print(f"  Model: {categorizer.llm.model_name}")
    print(f"  Temperature: {categorizer.llm.temperature}")
    print(f"  Max tokens: {categorizer.llm.max_tokens}")
    
    # Show prompt structure
    print(f"\n[FORMAT] Prompt Structure:")
    print(f"  System message: Contains format instructions and enums")
    print(f"  User message: Contains content and extraction rules")
    print(f"  Output parser: PydanticOutputParser with CategorizationOutput schema")
    
except Exception as e:
    print(f"[ERROR] Failed to initialize categorizer: {e}")
    import traceback
    traceback.print_exc()
    categorizer = None

# %%
# Cell 8: Step 5 - Categorize Content
print("=" * 60)
print("STEP 5: CATEGORIZING CONTENT")
print("=" * 60)

if categorizer and content_data and summarized_text:
    try:
        print("[TARGET] Sending content to LLM for categorization...")
        print("This may take 30-60 seconds...")
        
        start_time = time.time()
        result = categorizer.categorize_content(content_data)
        categorization_time = time.time() - start_time
        
        print(f"[OK] Categorization completed in {categorization_time:.2f} seconds!")
        
        # Extract results
        categories = result.get('categories', [])
        total_entities = sum(len(cat.get('entities', [])) for cat in categories)
        metadata = result.get('metadata', {})
        
        print(f"\n[INFO] Categorization Results:")
        print(f"  Categories found: {len(categories)}")
        print(f"  Total entities: {total_entities}")
        print(f"  Model used: {metadata.get('model_used', 'Unknown')}")
        print(f"  Processing time: {categorization_time:.2f} seconds")
        
        # Show raw categorization data
        print(f"\n[RAW] Categorization Object:")
        print(f"  Type: {type(result)}")
        print(f"  Full result object:")
        pprint(result, width=120, depth=3)
        
    except Exception as e:
        print(f"[ERROR] Categorization failed: {e}")
        import traceback
        traceback.print_exc()
        result = None
        categories = []
else:
    print("[ERROR] Cannot proceed - categorizer, content data, or summarized text not available")
    result = None
    categories = []

# %%
# Cell 9: Display Results - Categories and Entities
print("=" * 60)
print("STEP 6: DISPLAYING RESULTS")
print("=" * 60)

if categories:
    print("[CATEGORIES] CATEGORIES AND ENTITIES:")
    print("=" * 40)
    
    for i, category in enumerate(categories):
        category_name = category.get('category', f'Category {i+1}')
        entities = category.get('entities', [])
        
        print(f"\n{i+1}. {category_name.upper()}")
        print(f"   Entities: {len(entities)}")
        print("-" * 30)
        
        for j, entity in enumerate(entities):
            entity_name = entity.get('entity_name', 'Unknown')
            entity_type = entity.get('entity_type', 'Unknown')
            sentiment = entity.get('sentiment', 'Unknown')
            context = entity.get('context', 'No context available')
            quotes = entity.get('quotes', [])
            
            print(f"   {j+1}. {entity_name}")
            print(f"      Type: {entity_type}")
            print(f"      Sentiment: {sentiment}")
            print(f"      Context: {context}")
            print(f"      Quotes: {len(quotes)} direct quotes")
            
            # Show first quote if available
            if quotes:
                print(f"      Sample quote: \"{quotes[0][:100]}...\"")
            print()
else:
    print("[ERROR] No categories found to display")

# %%
# Cell 10: Create Results DataFrame for Analysis
print("=" * 60)
print("STEP 7: CREATING ANALYSIS DATAFRAME")
print("=" * 60)

if categories:
    # Create a DataFrame for easier analysis
    entities_data = []
    
    for category in categories:
        category_name = category.get('category', 'Unknown')
        for entity in category.get('entities', []):
            entities_data.append({
                'category': category_name,
                'entity_name': entity.get('entity_name', 'Unknown'),
                'entity_type': entity.get('entity_type', 'Unknown'),
                'sentiment': entity.get('sentiment', 'Unknown'),
                'context': entity.get('context', ''),
                'quotes_count': len(entity.get('quotes', [])),
                'quotes': entity.get('quotes', [])
            })
    
    df_entities = pd.DataFrame(entities_data)
    
    print("[OK] Created entities DataFrame!")
    print(f"Shape: {df_entities.shape}")
    
    # Display summary statistics
    print(f"\n[INFO] SUMMARY STATISTICS:")
    print(f"  Total entities: {len(df_entities)}")
    print(f"  Categories: {df_entities['category'].nunique()}")
    print(f"  Entity types: {df_entities['entity_type'].nunique()}")
    print(f"  Sentiment distribution:")
    print(df_entities['sentiment'].value_counts().to_string())
    
    # Display the DataFrame
    print(f"\n[FORMAT] ENTITIES DATAFRAME:")
    print(df_entities[['category', 'entity_name', 'entity_type', 'sentiment', 'quotes_count']].head(10).to_string())
    
else:
    print("[ERROR] No data available for DataFrame creation")
    df_entities = None

# %%
# Cell 11: Performance Analysis
print("=" * 60)
print("STEP 8: PERFORMANCE ANALYSIS")
print("=" * 60)

if result and summarized_text:
    # Calculate performance metrics
    total_processing_time = summarization_time + categorization_time
    
    print("[TIME] PERFORMANCE METRICS:")
    print("=" * 30)
    print(f"Summarization time: {summarization_time:.2f} seconds")
    print(f"Categorization time: {categorization_time:.2f} seconds")
    print(f"Total processing time: {total_processing_time:.2f} seconds")
    
    print(f"\n[INFO] THROUGHPUT METRICS:")
    print(f"Original text: {original_words:,} words, {original_tokens:,} tokens")
    print(f"Summary text: {summary_words:,} words, {summary_tokens:,} tokens")
    print(f"Compression ratio: {compression_ratio:.1%}")
    
    print(f"\n[PERFORMANCE] PROCESSING RATES:")
    print(f"Summarization: {original_words/summarization_time:.0f} words/second")
    print(f"Categorization: {summary_words/categorization_time:.0f} words/second")
    print(f"Overall: {original_words/total_processing_time:.0f} words/second")
    
    print(f"\n[COST] COST ESTIMATION:")
    print(f"Tokens processed: {summary_tokens:,} (for categorization)")
    print(f"Estimated cost: ~${summary_tokens * 0.00015 / 1000:.4f} (GPT-4o-mini pricing)")
    
else:
    print("[ERROR] No performance data available")

# %%
# Cell 12: Save Results
print("=" * 60)
print("STEP 9: SAVING RESULTS")
print("=" * 60)

if result and summarized_text:
    try:
        # Prepare comprehensive results
        test_results = {
            "test_info": {
                "test_name": "Full Pipeline Test (Jupyter Compatible)",
                "source_file": str(json_file_path),
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ")
            },
            "input_data": {
                "original_transcript_length": len(original_transcript),
                "original_tokens": original_tokens,
                "original_words": original_words
            },
            "summarization": {
                "target_words": target_words,
                "summary_length": len(summarized_text),
                "summary_tokens": summary_tokens,
                "summary_words": summary_words,
                "compression_ratio": compression_ratio,
                "processing_time": summarization_time
            },
            "categorization_results": result,
            "performance": {
                "total_processing_time": total_processing_time,
                "summarization_time": summarization_time,
                "categorization_time": categorization_time
            },
            "summary_text": summarized_text[:1000] + "..." if len(summarized_text) > 1000 else summarized_text
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(test_results, f, indent=2, default=str)
        
        print(f"[OK] Results saved to: {output_file}")
        print(f"File size: {os.path.getsize(output_file)} bytes")
        
    except Exception as e:
        print(f"[ERROR] Failed to save results: {e}")
else:
    print("[ERROR] No results to save")

# %%
# Cell 13: Final Summary
print("=" * 60)
print("FINAL SUMMARY")
print("=" * 60)

if result and summarized_text:
    print("[SUCCESS] PIPELINE COMPLETED SUCCESSFULLY!")
    print("\n[RESULTS] KEY METRICS:")
    print(f"  [OK] Loaded: {content_data['title']}")
    print(f"  [OK] Summarized: {original_tokens:,} -> {summary_tokens:,} tokens ({compression_ratio:.1%} compression)")
    print(f"  [OK] Categorized: {len(categories)} categories, {total_entities} entities")
    print(f"  [OK] Processing time: {total_processing_time:.2f} seconds")
    print(f"  [OK] Results saved to: {output_file}")
    
    print(f"\n[ANALYSIS] ENTITY BREAKDOWN:")
    if df_entities is not None:
        print(f"  Categories: {df_entities['category'].nunique()}")
        print(f"  Entity types: {df_entities['entity_type'].value_counts().to_dict()}")
        print(f"  Sentiment distribution: {df_entities['sentiment'].value_counts().to_dict()}")
    
    print(f"\n[SUGGESTIONS] NEXT STEPS:")
    print(f"  - Review the generated DataFrame for entity analysis")
    print(f"  - Check the saved JSON file for detailed results")
    print(f"  - Modify the target_words parameter to experiment with different compression ratios")
    print(f"  - Try different input files to test the pipeline")
    
else:
    print("[ERROR] Pipeline did not complete successfully")
    print("Please check the error messages above and retry failed steps")

# %%
# Cell 14: Optional - Interactive Analysis
print("=" * 60)
print("INTERACTIVE ANALYSIS TOOLS")
print("=" * 60)

if df_entities is not None:
    print("[ANALYSIS] Available analysis functions:")
    print("  - df_entities.head() - Show first few entities")
    print("  - df_entities.groupby('category').size() - Count entities per category")
    print("  - df_entities.groupby('sentiment').size() - Count entities by sentiment")
    print("  - df_entities[df_entities['entity_type'] == 'company'] - Filter by entity type")
    print("  - df_entities[df_entities['sentiment'] == 'negative'] - Filter by sentiment")
    
    print(f"\n[INFO] Quick analysis:")
    print(f"Most mentioned category: {df_entities['category'].mode().iloc[0]}")
    print(f"Most common entity type: {df_entities['entity_type'].mode().iloc[0]}")
    print(f"Sentiment distribution: {df_entities['sentiment'].value_counts().to_dict()}")
    
    print(f"\n[QUOTES] Entities with quotes:")
    entities_with_quotes = df_entities[df_entities['quotes_count'] > 0]
    print(f"Count: {len(entities_with_quotes)}")
    if len(entities_with_quotes) > 0:
        print("Top entities with quotes:")
        for idx, row in entities_with_quotes.head(5).iterrows():
            print(f"  - {row['entity_name']}: {row['quotes_count']} quotes")
else:
    print("[ERROR] No data available for interactive analysis")

print(f"\n[OK] Jupyter-compatible script setup complete!")
print(f"Run each cell sequentially to execute the full pipeline step by step.")
# %%
