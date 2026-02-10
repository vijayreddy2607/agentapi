"""Pydantic models for API requests."""
from pydantic import BaseModel, Field, field_validator, ConfigDict, AliasChoices
from typing import List, Literal, Optional, Union
from datetime import datetime


class Message(BaseModel):
    """Represents a single message in the conversation."""
    sender: str = "scammer"  # Default to scammer if not provided
    text: str
    timestamp: Union[datetime, str, int, float] = Field(default_factory=datetime.now)
    
    @field_validator('timestamp', mode='before')
    @classmethod
    def parse_timestamp(cls, v):
        """
        Convert string/int/float timestamp to datetime if needed.
        Handles:
        - ISO-8601 strings
        - Integer/Float timestamps (unix seconds or milliseconds)
        """
        if isinstance(v, (int, float)):
            try:
                # Guess if milliseconds (large int) or seconds
                # Current time ~1.7e9 seconds. 
                # 1.7e12 is milliseconds.
                if v > 1e11:  # likely milliseconds
                    return datetime.fromtimestamp(v / 1000.0)
                return datetime.fromtimestamp(v)
            except Exception:
                pass
        
        if isinstance(v, str):
            try:
                # Replace 'Z' with '+00:00' for UTC
                return datetime.fromisoformat(v.replace('Z', '+00:00'))
            except ValueError:
                pass
        return v


class Metadata(BaseModel):
    """Optional metadata about the message."""
    source: Optional[str] = "SMS"  # Message source (SMS, Email, WhatsApp, etc.)
    senderId: Optional[str] = None  # Sender identifier/phone number
    channel: Optional[str] = "SMS"
    language: Optional[str] = "English"
    locale: Optional[str] = "IN"


class MessageRequest(BaseModel):
    """Incoming API request for processing a message."""
    model_config = ConfigDict(
        # Allow camelCase field names from JSON
        populate_by_name=True,
        # Ignore extra fields (be lenient with unexpected fields)
        extra='ignore',
        json_schema_extra={
            "example": {
                "sessionId": "abc123-session-id",
                "message": {
                    "sender": "scammer",
                    "text": "Your bank account will be blocked today. Verify immediately.",
                    "timestamp": 1770005528731
                },
                "conversationHistory": [],
                "metadata": {
                    "channel": "SMS",
                    "language": "English",
                    "locale": "IN"
                }
            }
        }
    )
    
    sessionId: str = Field(
        ..., 
        validation_alias=AliasChoices("sessionId", "session_id"),
        description="Unique session identifier. Accepts 'sessionId' or 'session_id'."
    )
    message: Message = Field(..., description="Latest incoming message")
    conversationHistory: Optional[List[Message]] = Field(
        default_factory=list,
        validation_alias=AliasChoices("conversationHistory", "conversation_history"),
        description="Previous messages in the conversation. Empty array [] for first message. Accepts 'conversationHistory' or 'conversation_history'."
    )
    metadata: Optional[Metadata] = Field(
        default=None,
        description="Optional metadata about the conversation"
    )
    
    @field_validator('conversationHistory', mode='before')
    @classmethod
    def normalize_conversation_history(cls, v):
        """Convert None/null to empty list to match problem statement format."""
        if v is None:
            return []
        return v
