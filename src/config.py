"""
Configuration settings for the DiscourseKG platform.
"""

import os
from typing import Optional
from dotenv import load_dotenv
from pyprojroot import here


class Config:
    """Configuration class for the DiscourseKG platform."""

    load_dotenv()
    
    # Environment Configuration
    ENVIRONMENT: str = os.getenv('ENVIRONMENT', 'test')
    
    # OpenAI Configuration
    OPENAI_API_KEY: Optional[str] = os.getenv('OPENAI_API_KEY')
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_MAX_TOKENS: int = 5000
    OPENAI_TEMPERATURE: float = 0.1
    
    # Data Paths - Use absolute paths from project root
    PROJECT_ROOT = here()
    DATA_ROOT: str = str(PROJECT_ROOT / "data")
    PIPELINE_STATE_FILE: str = str(PROJECT_ROOT / "data" / ENVIRONMENT / "state" / f"pipeline_state_{ENVIRONMENT}.jsonl")
    
    # Analysis Settings
    MAX_TRANSCRIPT_LENGTH: int = 4000  # Characters to send to OpenAI
    BATCH_SIZE: int = 10  # For batch processing
    
    # Pipeline Configuration
    TARGET_SUMMARY_TOKENS: int = 1000  # Target token count for summarization
    
    # Summarization Configuration
    SUMMARIZER_MODEL: str = "all-MiniLM-L6-v2"  # Sentence transformer model
    SUMMARIZER_TOKENIZER: str = "cl100k_base"  # Tiktoken tokenizer


# Global config instance
config = Config()
