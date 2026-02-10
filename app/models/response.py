"""Pydantic models for API responses."""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ResponseMessage(BaseModel):
    """Response message from the agent."""
    sender: str = "user"
    text: str
    timestamp: datetime


class EngagementMetrics(BaseModel):
    """Metrics about the engagement."""
    engagementDurationSeconds: int
    totalMessagesExchanged: int


class ExtractedIntelligence(BaseModel):
    """Intelligence extracted from the conversation."""
    bankAccounts: list[str] = Field(default_factory=list)
    upiIds: list[str] = Field(default_factory=list)
    phishingLinks: list[str] = Field(default_factory=list)
    phoneNumbers: list[str] = Field(default_factory=list)
    suspiciousKeywords: list[str] = Field(default_factory=list)


class MessageResponse(BaseModel):
    """API response for message processing."""
    status: str = "success"
    scamDetected: bool
    response: Optional[ResponseMessage] = None
    engagementMetrics: EngagementMetrics
    extractedIntelligence: ExtractedIntelligence
    agentNotes: str = ""
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "scamDetected": True,
                "response": {
                    "sender": "user",
                    "text": "Why will my account be blocked?",
                    "timestamp": "2026-01-28T10:16:00Z"
                },
                "engagementMetrics": {
                    "engagementDurationSeconds": 45,
                    "totalMessagesExchanged": 2
                },
                "extractedIntelligence": {
                    "bankAccounts": [],
                    "upiIds": [],
                    "phishingLinks": [],
                    "phoneNumbers": [],
                    "suspiciousKeywords": ["blocked", "verify"]
                },
                "agentNotes": "Initial engagement, scammer using urgency tactics"
            }
        }
