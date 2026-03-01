"""
Configuration settings for the DiscourseKG platform.
"""

from pathlib import Path
from pydantic import BaseModel, computed_field
from pyprojroot import here


class Config(BaseModel):
    """Configuration class for the DiscourseKG platform."""

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
    def PIPELINE_STATE_DB(self) -> str:
        """Pipeline state SQLite database path."""
        return str(self.PROJECT_ROOT / "data" / "pipeline_state.db")
    
    model_config = {"frozen": True}  # Make immutable


# Global config instance
config = Config()
