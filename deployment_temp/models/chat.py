from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel


class ChatSession(BaseModel):
    id: Optional[str] = None
    user_id: str
    title: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ChatMessage(BaseModel):
    id: Optional[str] = None
    session_id: str
    role: str
    content: str
    code: Optional[str] = None
    next_steps: Optional[str] = None
    is_deployable: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None