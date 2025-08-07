from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum

class AgentStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"

class AgentConfig(BaseModel):
    model: str = Field(..., description="LLM model to use")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Model temperature")
    max_tokens: int = Field(default=4000, ge=1, le=32000, description="Maximum tokens")
    system_prompt: Optional[str] = Field(default=None, description="System prompt")
    context_window: Optional[int] = Field(default=None, description="Context window size")
    
    @validator('temperature')
    def validate_temperature(cls, v):
        if not 0.0 <= v <= 2.0:
            raise ValueError('Temperature must be between 0.0 and 2.0')
        return v

class APIKeys(BaseModel):
    openai: Optional[str] = Field(default=None, description="OpenAI API key")
    anthropic: Optional[str] = Field(default=None, description="Anthropic API key")
    google: Optional[str] = Field(default=None, description="Google API key")
    azure: Optional[str] = Field(default=None, description="Azure API key")
    custom: Optional[Dict[str, str]] = Field(default=None, description="Custom API keys")
    
    class Config:
        extra = "allow"

class AgentPermissions(BaseModel):
    file_access: bool = Field(default=False, description="Allow file system access")
    shell_access: bool = Field(default=False, description="Allow shell command execution")
    network_access: bool = Field(default=True, description="Allow network access")
    browser_access: bool = Field(default=False, description="Allow browser automation")
    api_access: bool = Field(default=True, description="Allow API calls")
    database_access: bool = Field(default=False, description="Allow database access")
    
    class Config:
        extra = "allow"

class AgentCreate(BaseModel):
    agent_id: str = Field(..., min_length=1, max_length=50, description="Unique agent identifier")
    name: str = Field(..., min_length=1, max_length=100, description="Agent name")
    description: Optional[str] = Field(default=None, max_length=500, description="Agent description")
    config: Optional[AgentConfig] = Field(default=None, description="Agent configuration")
    api_keys: Optional[APIKeys] = Field(default=None, description="API keys")
    tools: List[str] = Field(default_factory=list, description="Available tools")
    permissions: Optional[AgentPermissions] = Field(default=None, description="Agent permissions")
    
    @validator('agent_id')
    def validate_agent_id(cls, v):
        if not v.replace('-', '').replace('_', '').isalnum():
            raise ValueError('Agent ID must contain only alphanumeric characters, hyphens, and underscores')
        return v.lower()

class AgentUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    config: Optional[AgentConfig] = None
    api_keys: Optional[APIKeys] = None
    tools: Optional[List[str]] = None
    permissions: Optional[AgentPermissions] = None

class AgentResponse(BaseModel):
    id: int
    agent_id: str
    name: str
    description: Optional[str]
    config: Dict[str, Any]
    api_keys: Dict[str, Any]
    tools: List[str]
    permissions: Dict[str, Any]
    is_active: bool
    is_running: bool
    created_at: datetime
    updated_at: datetime
    last_run: Optional[datetime]
    owner_id: int
    
    class Config:
        from_attributes = True

class AgentListResponse(BaseModel):
    id: int
    agent_id: str
    name: str
    description: Optional[str]
    is_active: bool
    is_running: bool
    created_at: datetime
    updated_at: datetime
    last_run: Optional[datetime]
    
    class Config:
        from_attributes = True

class AgentLogEntry(BaseModel):
    id: int
    level: str
    message: str
    metadata: Optional[Dict[str, Any]]
    timestamp: datetime
    
    class Config:
        from_attributes = True

class TaskTraceEntry(BaseModel):
    id: int
    task_id: str
    status: str
    task_type: str
    input_data: Optional[Dict[str, Any]]
    output_data: Optional[Dict[str, Any]]
    error_message: Optional[str]
    started_at: datetime
    completed_at: Optional[datetime]
    duration_ms: Optional[int]
    
    class Config:
        from_attributes = True

class AgentStatusResponse(BaseModel):
    agent_id: str
    status: AgentStatus
    is_running: bool
    last_run: Optional[datetime]
    uptime_seconds: Optional[int] = None
    memory_usage_mb: Optional[float] = None
    cpu_usage_percent: Optional[float] = None

class AgentMetrics(BaseModel):
    agent_id: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    average_response_time_ms: float
    total_tokens_used: int
    last_24h_requests: int
    last_24h_tokens: int

class AgentTemplate(BaseModel):
    name: str
    description: str
    category: str
    config: AgentConfig
    tools: List[str]
    permissions: AgentPermissions
    example_prompts: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
