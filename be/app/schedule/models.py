from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class ScheduleCreate(BaseModel):
    """Model for creating a new schedule."""
    agentId: str
    cronExpression: str
    user_message: str

class Schedule(BaseModel):
    """Model representing a schedule."""
    user_id: str
    id: str
    agentId: str
    agentUserId: Optional[str] = None
    agentName: str
    cronExpression: str
    status: str
    createdAt: str
    updatedAt: str
    user_message: Optional[str] = None
