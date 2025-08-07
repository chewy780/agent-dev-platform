from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

class LogEntry(BaseModel):
    id: int
    level: str
    message: str
    metadata: Optional[Dict[str, Any]]
    timestamp: datetime
    agent_id: int
    
    class Config:
        from_attributes = True

class LogFilter(BaseModel):
    level: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    search: Optional[str] = None
    limit: int = 100
    offset: int = 0

class LogStats(BaseModel):
    agent_id: str
    total_logs: int
    level_distribution: Dict[str, int]
    hourly_distribution: Dict[str, int]
    date_range_start: datetime
    date_range_end: datetime

class LogExport(BaseModel):
    format: str = "json"  # json, csv
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    include_metadata: bool = True
