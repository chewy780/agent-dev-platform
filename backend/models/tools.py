from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

class ToolInfo(BaseModel):
    id: str
    name: str
    description: str
    category: str
    permissions: List[str]
    parameters: Dict[str, Any]

class ToolCategory(BaseModel):
    id: str
    name: str
    description: str
    tool_count: int

class ToolExecution(BaseModel):
    action: str = Field(..., description="Action to execute")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Parameters for the action")

class ToolExecutionResult(BaseModel):
    success: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time_ms: int
    tool_id: str
    action: str

class PluginInfo(BaseModel):
    name: str
    version: str
    description: str
    author: str
    tools: List[str]
    dependencies: List[str]
    installed: bool = False
