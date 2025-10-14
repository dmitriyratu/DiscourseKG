"""
Configuration settings for the KG-Sentiment platform.
"""

import os
from typing import Optional
from dotenv import load_dotenv
import logging



class Config:
    """Configuration class for the KG-Sentiment platform."""

    load_dotenv()
    
    # OpenAI Configuration
    OPENAI_API_KEY: Optional[str] = os.getenv('OPENAI_API_KEY')
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_MAX_TOKENS: int = 2000
    OPENAI_TEMPERATURE: float = 0.1  # Low temperature for consistent results
    
    # AWS Configuration
    AWS_REGION: str = os.getenv('AWS_REGION', 'us-east-1')
    S3_BUCKET: str = os.getenv('S3_BUCKET', 'kg-sentiment-data')
    
    # Data Paths
    DATA_ROOT: str = "data"
    RAW_DATA_PATH: str = os.path.join(DATA_ROOT, "raw")
    PROCESSED_DATA_PATH: str = os.path.join(DATA_ROOT, "processed")
    OUTPUTS_PATH: str = os.path.join(DATA_ROOT, "outputs")
    STATE_PATH: str = os.path.join(DATA_ROOT, "state")
    PIPELINE_STATE_FILE: str = os.path.join(STATE_PATH, "pipeline_state.jsonl")
    
    # Analysis Settings
    MAX_TRANSCRIPT_LENGTH: int = 4000  # Characters to send to OpenAI
    BATCH_SIZE: int = 10  # For batch processing
    


# Global config instance
config = Config()
