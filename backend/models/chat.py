from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

class ChatMessageCreate(BaseModel):
    content: str = Field(..., min_length=1, description="Message content")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional message metadata")

class ChatMessageResponse(BaseModel):
    id: int
    role: str
    content: str
    metadata: Optional[Dict[str, Any]]
    timestamp: datetime
    agent_id: int
    
    class Config:
        from_attributes = True

class ChatSession(BaseModel):
    session_id: str
    agent_id: str
    session_date: datetime
    message_count: int
    start_time: datetime
    end_time: datetime

class ChatStreamResponse(BaseModel):
    type: str  # start, thinking, content, end, error
    content: Optional[str] = None
    message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class TypingIndicator(BaseModel):
    user_id: str
    is_typing: bool
    agent_id: str
