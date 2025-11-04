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
    
    # Data Paths - Use absolute paths from project root
    PROJECT_ROOT = here()
    DATA_ROOT: str = str(PROJECT_ROOT / "data")
    PIPELINE_STATE_FILE: str = str(PROJECT_ROOT / "data" / ENVIRONMENT / "state" / f"pipeline_state_{ENVIRONMENT}.jsonl")


# Global config instance
config = Config()
