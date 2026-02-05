"""
Configuration settings for the DiscourseKG platform.
"""

import os
from pathlib import Path
from pydantic import BaseModel, Field, computed_field
from dotenv import load_dotenv
from pyprojroot import here

load_dotenv()


class Config(BaseModel):
    """Configuration class for the DiscourseKG platform."""
    
    # Environment Configuration
    ENVIRONMENT: str = Field(default_factory=lambda: os.getenv('ENVIRONMENT', 'test'))
    
    @computed_field
    @property
    def PROJECT_ROOT(self) -> Path:
        """Project root directory."""
        return here()
    
    @computed_field
    @property
    def DATA_ROOT(self) -> str:
        """Data directory path."""
        return str(self.PROJECT_ROOT / "data")
    
    @computed_field
    @property
    def PIPELINE_STATE_FILE(self) -> str:
        """Pipeline state file path."""
        return str(self.PROJECT_ROOT / "data" / self.ENVIRONMENT / "state" / f"pipeline_state_{self.ENVIRONMENT}.jsonl")
    
    model_config = {"frozen": True}  # Make immutable


# Global config instance
config = Config()
