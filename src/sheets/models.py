"""
Pydantic models for data validation.
"""

from typing import Optional
from pydantic import BaseModel, Field


class UserContext(BaseModel):
    """Model for user context from Telegram."""

    user_id: int = Field(..., description="Telegram user ID")
    username: Optional[str] = Field(None, description="Telegram username (without @)")
    first_name: Optional[str] = Field(None, description="User's first name")
    last_name: Optional[str] = Field(None, description="User's last name")

    def get_display_name(self) -> str:
        """Get a display name for the user."""
        if self.username:
            return self.username
        if self.first_name:
            full_name = self.first_name
            if self.last_name:
                full_name += f" {self.last_name}"
            return full_name
        return f"User{self.user_id}"
