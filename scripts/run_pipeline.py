#!/usr/bin/env python3
"""
Main pipeline runner for KG-Sentiment platform.

This script orchestrates the complete pipeline:
1. Data ingestion/loading
2. Summarization (if needed)
3. Content categorization
4. Knowledge graph construction
5. Results storage

Usage:
    python scripts/run_pipeline.py --input-file data/raw/donald_trump/speeches/2025/09/23/speech_un_091500.json
    python scripts/run_pipeline.py --input-dir data/raw/donald_trump/speeches/2025/09/23/ --batch
    python scripts/run_pipeline.py --input-file <file> --skip-summarization
"""

import argparse
import sys
import json
import time
from pathlib import Path
from typing import List, Dict, Any

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from src.preprocessing.extractive_summarizer import ExtractiveSummarizer
from src.processing.content_categorizer import ContentCategorizer
from src.config import config
from src.utils.logging_utils import get_logger


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


def process_single_file(
    file_path: Path, 
    skip_summarization: bool = False,
    target_words: int = 3750
) -> Dict[str, Any]:
    """Process a single JSON file through the pipeline."""
    logger = get_logger("pipeline_runner", "pipeline.log")
    
    logger.info(f"Processing file: {file_path}")
    
    # Step 1: Load data
    content_data = load_json_file(file_path)
    original_transcript = content_data['transcript']
    
    # Step 2: Summarize (if needed)
    if skip_summarization:
        logger.info("Skipping summarization")
        summarized_text = original_transcript
    else:
        logger.info(f"Summarizing to ~{target_words} words...")
        summarizer = ExtractiveSummarizer()
        summarized_text = summarizer.summarize(original_transcript, target_words)
        
        if not summarized_text:
            logger.warning("Summarization failed, using original text")
            summarized_text = original_transcript
        else:
            content_data['transcript'] = summarized_text
    
    # Step 3: Categorize
    logger.info("Categorizing content...")
    categorizer = ContentCategorizer()
    result = categorizer.categorize_content(content_data)
    
    # Step 4: Prepare output
    output = {
        "file_info": {
            "input_file": str(file_path),
            "original_length": len(original_transcript),
            "processed_length": len(summarized_text),
            "skip_summarization": skip_summarization
        },
        "content_data": content_data,
        "categorization_results": result,
        "metadata": {
            "processed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "pipeline_version": "1.0.0"
        }
    }
    
    logger.info(f"Successfully processed: {len(result.get('categories', []))} categories, "
                f"{sum(len(cat.get('entities', [])) for cat in result.get('categories', []))} entities")
    
    return output


def process_batch_files(
    input_dir: Path,
    skip_summarization: bool = False,
    target_words: int = 3750
) -> List[Dict[str, Any]]:
    """Process multiple JSON files in a directory."""
    logger = get_logger("pipeline_runner", "pipeline.log")
    
    json_files = list(input_dir.glob("**/*.json"))
    if not json_files:
        raise ValueError(f"No JSON files found in {input_dir}")
    
    logger.info(f"Found {len(json_files)} JSON files to process")
    
    results = []
    successful = 0
    failed = 0
    
    for i, file_path in enumerate(json_files, 1):
        try:
            logger.info(f"Processing {i}/{len(json_files)}: {file_path.name}")
            result = process_single_file(file_path, skip_summarization, target_words)
            results.append(result)
            successful += 1
        except Exception as e:
            logger.error(f"Failed to process {file_path}: {e}")
            results.append({
                "file_info": {"input_file": str(file_path), "error": str(e)},
                "metadata": {"processed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ")}
            })
            failed += 1
    
    logger.info(f"Batch processing complete: {successful} successful, {failed} failed")
    return results


def save_results(results: Any, output_path: Path):
    """Save results to JSON file."""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, default=str)


def main():
    parser = argparse.ArgumentParser(description="KG-Sentiment Pipeline Runner")
    parser.add_argument("--input-file", type=Path, help="Single JSON file to process")
    parser.add_argument("--input-dir", type=Path, help="Directory containing JSON files to process")
    parser.add_argument("--output", type=Path, help="Output file path (default: auto-generated)")
    parser.add_argument("--skip-summarization", action="store_true", 
                       help="Skip summarization step")
    parser.add_argument("--target-words", type=int, default=3750,
                       help="Target word count for summarization (default: 3750)")
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
            
            result = process_single_file(
                args.input_file, 
                args.skip_summarization, 
                args.target_words
            )
            
            # Generate output path if not specified
            if not args.output:
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                output_file = args.input_file.stem + f"_processed_{timestamp}.json"
                args.output = Path("data/outputs") / output_file
            
            save_results(result, args.output)
            print(f"✅ Successfully processed: {args.input_file}")
            print(f"📁 Results saved to: {args.output}")
            
        elif args.input_dir:
            # Process batch
            if not args.input_dir.exists():
                raise FileNotFoundError(f"Input directory not found: {args.input_dir}")
            
            results = process_batch_files(
                args.input_dir,
                args.skip_summarization,
                args.target_words
            )
            
            # Generate output path if not specified
            if not args.output:
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                args.output = Path("data/outputs") / f"batch_processed_{timestamp}.json"
            
            save_results(results, args.output)
            print(f"✅ Successfully processed batch from: {args.input_dir}")
            print(f"📁 Results saved to: {args.output}")
            
    except Exception as e:
        print(f"❌ Pipeline failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
