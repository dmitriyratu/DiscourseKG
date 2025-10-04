#!/usr/bin/env python3
"""
Test script for the updated schema without prominence and is_market_relevant fields.
"""

import sys
import os
import json
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from processing.content_categorizer import ContentCategorizer
from schemas import EntityMention, CategoryWithEntities, CategorizationOutput
from config import config

def test_schema_validation():
    """Test that the updated schema works correctly"""
    print("Testing Updated Schema")
    print("=" * 50)
    
    # Test EntityMention creation
    try:
        entity = EntityMention(
            entity_name="United Nations",
            entity_type="other",
            sentiment="negative",
            context="The speaker criticizes the UN for not helping with negotiations",
            quotes=[
                "The United Nations did not even try to help in any of them.",
                "I never even received a phone call from the United Nations."
            ]
        )
        print("PASS: EntityMention schema validation passed")
        print(f"   Entity: {entity.entity_name}")
        print(f"   Type: {entity.entity_type}")
        print(f"   Sentiment: {entity.sentiment}")
        print(f"   Quotes: {len(entity.quotes)} quotes")
        
    except Exception as e:
        print(f"FAIL: EntityMention validation failed: {e}")
        return False
    
    # Test CategoryWithEntities creation
    try:
        category = CategoryWithEntities(
            category="foreign_relations",
            entities=[entity]
        )
        print("PASS CategoryWithEntities schema validation passed")
        print(f"   Category: {category.category}")
        print(f"   Entities: {len(category.entities)}")
        
    except Exception as e:
        print(f"FAIL CategoryWithEntities validation failed: {e}")
        return False
    
    # Test CategorizationOutput creation
    try:
        output = CategorizationOutput(
            categories=[category]
        )
        print("PASS CategorizationOutput schema validation passed")
        print(f"   Categories: {len(output.categories)}")
        
    except Exception as e:
        print(f"FAIL CategorizationOutput validation failed: {e}")
        return False
    
    return True

def test_content_categorizer_initialization():
    """Test that ContentCategorizer can be initialized with updated schema"""
    print("\n Testing ContentCategorizer Initialization")
    print("=" * 50)
    
    try:
        categorizer = ContentCategorizer()
        print("PASS ContentCategorizer initialized successfully")
        print(f"   Model: {categorizer.llm.model_name}")
        print(f"   Temperature: {categorizer.llm.temperature}")
        
        # Test that the chain can be created
        if hasattr(categorizer, 'chain') and categorizer.chain:
            print("PASS LangChain pipeline created successfully")
        else:
            print("FAIL LangChain pipeline creation failed")
            return False
            
        return True
        
    except Exception as e:
        print(f"FAIL ContentCategorizer initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_simple_categorization():
    """Test categorization with a simple example"""
    print("\n Testing Simple Categorization")
    print("=" * 50)
    
    # Simple test content
    test_content = {
        "id": "test-001",
        "title": "Test Speech",
        "speakers": ["Test Speaker"],
        "date": "2025-01-15",
        "transcript": "I think Apple is doing great work in technology. However, China's trade policies are concerning. We need to work with the United Nations on this issue."
    }
    
    try:
        categorizer = ContentCategorizer()
        result = categorizer.categorize_content(test_content)
        
        print("PASS Categorization completed successfully")
        print(f"   Categories found: {len(result.get('categories', []))}")
        
        for i, category in enumerate(result.get('categories', [])):
            print(f"\n   Category {i+1}: {category.get('category', 'Unknown')}")
            entities = category.get('entities', [])
            print(f"   Entities: {len(entities)}")
            
            for j, entity in enumerate(entities):
                print(f"     {j+1}. {entity.get('entity_name', 'Unknown')}")
                print(f"        Type: {entity.get('entity_type', 'Unknown')}")
                print(f"        Sentiment: {entity.get('sentiment', 'Unknown')}")
                quotes = entity.get('quotes', [])
                print(f"        Quotes: {len(quotes)}")
                if quotes:
                    print(f"        Sample quote: {quotes[0][:100]}...")
        
        return True
        
    except Exception as e:
        print(f"FAIL Categorization test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test function"""
    print(" Testing Updated Schema System")
    print("=" * 60)
    
    # Test 1: Schema validation
    if not test_schema_validation():
        print("\nFAIL Schema validation failed")
        return
    
    # Test 2: ContentCategorizer initialization
    if not test_content_categorizer_initialization():
        print("\nFAIL ContentCategorizer initialization failed")
        return
    
    # Test 3: Simple categorization
    if not test_simple_categorization():
        print("\nFAIL Simple categorization test failed")
        return
    
    print("\n All Tests Passed!")
    print("=" * 60)
    print("PASS Schema updated successfully:")
    print("   - Removed prominence field")
    print("   - Removed is_market_relevant field")
    print("   - Enhanced quote extraction prompt")
    print("   - System is ready for use")

if __name__ == "__main__":
    main()
