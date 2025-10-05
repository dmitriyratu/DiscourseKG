#!/usr/bin/env python3
"""
Categorization pipeline component for KG-Sentiment platform.

This pipeline component runs the content categorization step on input files.
Part of the KG-Sentiment processing pipeline.
"""

import argparse
import sys
import json
import time
from pathlib import Path
from typing import List, Dict, Any

from src.processing.content_categorizer import ContentCategorizer
from src.utils.logging_utils import get_logger
from src.config import config


def load_json_file(file_path: Path) -> Dict[str, Any]:
    """Load and validate JSON file."""
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


def categorize_single_file(file_path: Path) -> Dict[str, Any]:
    """Categorize a single JSON file."""
    logger = get_logger("categorizer", "categorizer.log")
    
    logger.info(f"Categorizing file: {file_path}")
    
    # Load data
    content_data = load_json_file(file_path)
    
    # Initialize categorizer
    categorizer = ContentCategorizer()
    
    # Categorize
    start_time = time.time()
    result = categorizer.categorize_content(content_data)
    processing_time = time.time() - start_time
    
    # Extract metrics
    categories_count = len(result.get('categories', []))
    entities_count = sum(len(cat.get('entities', [])) for cat in result.get('categories', []))
    
    # Prepare output
    output = {
        "file_info": {
            "input_file": str(file_path),
            "categories_count": categories_count,
            "entities_count": entities_count,
            "processing_time": processing_time
        },
        "content_data": content_data,
        "categorization_results": result,
        "metadata": {
            "processed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "categorizer_version": "1.0.0"
        }
    }
    
    logger.info(f"Successfully categorized: {categories_count} categories, "
                f"{entities_count} entities in {processing_time:.2f}s")
    
    return output


def categorize_batch_files(input_dir: Path) -> List[Dict[str, Any]]:
    """Categorize multiple JSON files in a directory."""
    logger = get_logger("categorizer", "categorizer.log")
    
    json_files = list(input_dir.glob("**/*.json"))
    if not json_files:
        raise ValueError(f"No JSON files found in {input_dir}")
    
    logger.info(f"Found {len(json_files)} JSON files to categorize")
    
    results = []
    successful = 0
    failed = 0
    
    for i, file_path in enumerate(json_files, 1):
        try:
            logger.info(f"Processing {i}/{len(json_files)}: {file_path.name}")
            result = categorize_single_file(file_path)
            results.append(result)
            successful += 1
        except Exception as e:
            logger.error(f"Failed to categorize {file_path}: {e}")
            results.append({
                "file_info": {"input_file": str(file_path), "error": str(e)},
                "metadata": {"processed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ")}
            })
            failed += 1
    
    logger.info(f"Batch categorization complete: {successful} successful, {failed} failed")
    return results


def save_results(results: Any, output_path: Path):
    """Save results to JSON file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, default=str)


def main():
    parser = argparse.ArgumentParser(description="KG-Sentiment Categorization Pipeline")
    parser.add_argument("--input-file", type=Path, help="Single JSON file to categorize")
    parser.add_argument("--input-dir", type=Path, help="Directory containing JSON files to categorize")
    parser.add_argument("--output", type=Path, help="Output file path (default: auto-generated)")
    parser.add_argument("--batch", action="store_true",
                       help="Process multiple files (use with --input-dir)")
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.input_file and not args.input_dir:
        parser.error("Must specify either --input-file or --input-dir")
    
    if args.input_file and args.input_dir:
        parser.error("Cannot specify both --input-file and --input-dir")
    
    if args.batch and not args.input_dir:
        parser.error("--batch requires --input-dir")
    
    try:
        if args.input_file:
            # Process single file
            if not args.input_file.exists():
                raise FileNotFoundError(f"Input file not found: {args.input_file}")
            
            result = categorize_single_file(args.input_file)
            
            # Generate output path if not specified
            if not args.output:
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                output_file = args.input_file.stem + f"_categorized_{timestamp}.json"
                args.output = Path(config.OUTPUTS_PATH) / output_file
            
            save_results(result, args.output)
            print(f"✅ Successfully categorized: {args.input_file}")
            print(f"📁 Results saved to: {args.output}")
            
        elif args.input_dir:
            # Process batch
            if not args.input_dir.exists():
                raise FileNotFoundError(f"Input directory not found: {args.input_dir}")
            
            results = categorize_batch_files(args.input_dir)
            
            # Generate output path if not specified
            if not args.output:
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                args.output = Path(config.OUTPUTS_PATH) / f"batch_categorized_{timestamp}.json"
            
            save_results(results, args.output)
            print(f"✅ Successfully categorized batch from: {args.input_dir}")
            print(f"📁 Results saved to: {args.output}")
            
    except Exception as e:
        print(f"❌ Categorization failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
