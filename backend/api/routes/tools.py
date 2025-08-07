from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
import json
import os
from pathlib import Path

from core.database import get_db, User
from models.tools import ToolInfo, ToolCategory, ToolExecution
from services.auth_service import get_current_user

router = APIRouter()

# Available tools registry
AVAILABLE_TOOLS = {
    "file_system": {
        "name": "File System",
        "description": "Read, write, and manage files on the system",
        "category": "system",
        "permissions": ["file_access"],
        "parameters": {
            "read_file": {"path": "string"},
            "write_file": {"path": "string", "content": "string"},
            "list_directory": {"path": "string"},
            "delete_file": {"path": "string"}
        }
    },
    "shell": {
        "name": "Shell Commands",
        "description": "Execute shell commands on the system",
        "category": "system",
        "permissions": ["shell_access"],
        "parameters": {
            "execute": {"command": "string", "timeout": "number"}
        }
    },
    "browser": {
        "name": "Web Browser",
        "description": "Automate web browser interactions",
        "category": "web",
        "permissions": ["browser_access"],
        "parameters": {
            "navigate": {"url": "string"},
            "click": {"selector": "string"},
            "type": {"selector": "string", "text": "string"},
            "screenshot": {"path": "string"}
        }
    },
    "api_client": {
        "name": "API Client",
        "description": "Make HTTP requests to external APIs",
        "category": "network",
        "permissions": ["network_access"],
        "parameters": {
            "get": {"url": "string", "headers": "object"},
            "post": {"url": "string", "data": "object", "headers": "object"},
            "put": {"url": "string", "data": "object", "headers": "object"},
            "delete": {"url": "string", "headers": "object"}
        }
    },
    "database": {
        "name": "Database",
        "description": "Execute database queries",
        "category": "data",
        "permissions": ["database_access"],
        "parameters": {
            "query": {"sql": "string", "params": "object"},
            "execute": {"sql": "string", "params": "object"}
        }
    },
    "python_repl": {
        "name": "Python REPL",
        "description": "Execute Python code",
        "category": "development",
        "permissions": ["shell_access"],
        "parameters": {
            "execute": {"code": "string", "timeout": "number"}
        }
    }
}

@router.get("/", response_model=List[ToolInfo])
async def list_available_tools(
    category: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """List all available tools"""
    tools = []
    
    for tool_id, tool_info in AVAILABLE_TOOLS.items():
        if category and tool_info["category"] != category:
            continue
            
        tools.append(ToolInfo(
            id=tool_id,
            name=tool_info["name"],
            description=tool_info["description"],
            category=tool_info["category"],
            permissions=tool_info["permissions"],
            parameters=tool_info["parameters"]
        ))
    
    return tools

@router.get("/categories", response_model=List[ToolCategory])
async def get_tool_categories(
    current_user: User = Depends(get_current_user)
):
    """Get all tool categories"""
    categories = {}
    
    for tool_info in AVAILABLE_TOOLS.values():
        category = tool_info["category"]
        if category not in categories:
            categories[category] = {
                "name": category.title(),
                "description": f"Tools for {category} operations",
                "tool_count": 0
            }
        categories[category]["tool_count"] += 1
    
    return [
        ToolCategory(
            id=cat_id,
            name=cat_info["name"],
            description=cat_info["description"],
            tool_count=cat_info["tool_count"]
        )
        for cat_id, cat_info in categories.items()
    ]

@router.get("/{tool_id}", response_model=ToolInfo)
async def get_tool_info(
    tool_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get detailed information about a specific tool"""
    if tool_id not in AVAILABLE_TOOLS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tool not found"
        )
    
    tool_info = AVAILABLE_TOOLS[tool_id]
    
    return ToolInfo(
        id=tool_id,
        name=tool_info["name"],
        description=tool_info["description"],
        category=tool_info["category"],
        permissions=tool_info["permissions"],
        parameters=tool_info["parameters"]
    )

@router.post("/{tool_id}/execute")
async def execute_tool(
    tool_id: str,
    execution: ToolExecution,
    current_user: User = Depends(get_current_user)
):
    """Execute a tool with given parameters"""
    if tool_id not in AVAILABLE_TOOLS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tool not found"
        )
    
    tool_info = AVAILABLE_TOOLS[tool_id]
    
    # Check if user has required permissions
    # This would typically check against user's agent permissions
    # For now, we'll allow all executions
    
    try:
        result = await _execute_tool_function(tool_id, execution.action, execution.parameters)
        return {
            "success": True,
            "result": result,
            "execution_time_ms": 0,  # Would calculate actual execution time
            "tool_id": tool_id,
            "action": execution.action
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "tool_id": tool_id,
            "action": execution.action
        }

async def _execute_tool_function(tool_id: str, action: str, parameters: Dict[str, Any]):
    """Execute the actual tool function"""
    if tool_id == "file_system":
        return await _execute_file_system(action, parameters)
    elif tool_id == "shell":
        return await _execute_shell(action, parameters)
    elif tool_id == "browser":
        return await _execute_browser(action, parameters)
    elif tool_id == "api_client":
        return await _execute_api_client(action, parameters)
    elif tool_id == "database":
        return await _execute_database(action, parameters)
    elif tool_id == "python_repl":
        return await _execute_python_repl(action, parameters)
    else:
        raise ValueError(f"Unknown tool: {tool_id}")

async def _execute_file_system(action: str, parameters: Dict[str, Any]):
    """Execute file system operations"""
    import aiofiles
    
    if action == "read_file":
        path = parameters.get("path")
        if not path:
            raise ValueError("Path parameter is required")
        
        async with aiofiles.open(path, 'r') as f:
            content = await f.read()
        return {"content": content, "path": path}
    
    elif action == "write_file":
        path = parameters.get("path")
        content = parameters.get("content", "")
        
        if not path:
            raise ValueError("Path parameter is required")
        
        # Ensure directory exists
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        
        async with aiofiles.open(path, 'w') as f:
            await f.write(content)
        return {"success": True, "path": path, "bytes_written": len(content)}
    
    elif action == "list_directory":
        path = parameters.get("path", ".")
        
        items = []
        for item in Path(path).iterdir():
            items.append({
                "name": item.name,
                "is_file": item.is_file(),
                "is_directory": item.is_dir(),
                "size": item.stat().st_size if item.is_file() else None
            })
        
        return {"items": items, "path": path}
    
    elif action == "delete_file":
        path = parameters.get("path")
        if not path:
            raise ValueError("Path parameter is required")
        
        Path(path).unlink()
        return {"success": True, "path": path}
    
    else:
        raise ValueError(f"Unknown file system action: {action}")

async def _execute_shell(action: str, parameters: Dict[str, Any]):
    """Execute shell commands"""
    import asyncio
    import subprocess
    
    if action == "execute":
        command = parameters.get("command")
        timeout = parameters.get("timeout", 30)
        
        if not command:
            raise ValueError("Command parameter is required")
        
        try:
            process = await asyncio.wait_for(
                asyncio.create_subprocess_exec(
                    *command.split(),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                ),
                timeout=timeout
            )
            
            stdout, stderr = await process.communicate()
            
            return {
                "return_code": process.returncode,
                "stdout": stdout.decode(),
                "stderr": stderr.decode(),
                "command": command
            }
        except asyncio.TimeoutError:
            return {
                "error": "Command timed out",
                "command": command,
                "timeout": timeout
            }
    
    else:
        raise ValueError(f"Unknown shell action: {action}")

async def _execute_browser(action: str, parameters: Dict[str, Any]):
    """Execute browser automation"""
    # This would integrate with a browser automation library like Selenium or Playwright
    # For now, return a mock response
    
    if action == "navigate":
        url = parameters.get("url")
        return {"success": True, "url": url, "title": "Mock Page Title"}
    
    elif action == "click":
        selector = parameters.get("selector")
        return {"success": True, "clicked": selector}
    
    elif action == "type":
        selector = parameters.get("selector")
        text = parameters.get("text")
        return {"success": True, "typed": text, "selector": selector}
    
    elif action == "screenshot":
        path = parameters.get("path", "screenshot.png")
        return {"success": True, "screenshot_path": path}
    
    else:
        raise ValueError(f"Unknown browser action: {action}")

async def _execute_api_client(action: str, parameters: Dict[str, Any]):
    """Execute API client operations"""
    import httpx
    
    url = parameters.get("url")
    headers = parameters.get("headers", {})
    
    if not url:
        raise ValueError("URL parameter is required")
    
    async with httpx.AsyncClient() as client:
        if action == "get":
            response = await client.get(url, headers=headers)
        elif action == "post":
            data = parameters.get("data", {})
            response = await client.post(url, json=data, headers=headers)
        elif action == "put":
            data = parameters.get("data", {})
            response = await client.put(url, json=data, headers=headers)
        elif action == "delete":
            response = await client.delete(url, headers=headers)
        else:
            raise ValueError(f"Unknown API action: {action}")
        
        return {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "content": response.text,
            "url": url
        }

async def _execute_database(action: str, parameters: Dict[str, Any]):
    """Execute database operations"""
    # This would integrate with the database system
    # For now, return a mock response
    
    sql = parameters.get("sql")
    params = parameters.get("params", {})
    
    if not sql:
        raise ValueError("SQL parameter is required")
    
    if action == "query":
        return {
            "success": True,
            "rows": [{"mock": "data"}],
            "row_count": 1,
            "sql": sql
        }
    
    elif action == "execute":
        return {
            "success": True,
            "affected_rows": 1,
            "sql": sql
        }
    
    else:
        raise ValueError(f"Unknown database action: {action}")

async def _execute_python_repl(action: str, parameters: Dict[str, Any]):
    """Execute Python code"""
    import asyncio
    import subprocess
    import tempfile
    
    if action == "execute":
        code = parameters.get("code")
        timeout = parameters.get("timeout", 30)
        
        if not code:
            raise ValueError("Code parameter is required")
        
        # Create temporary file with code
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_file = f.name
        
        try:
            process = await asyncio.wait_for(
                asyncio.create_subprocess_exec(
                    "python", temp_file,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                ),
                timeout=timeout
            )
            
            stdout, stderr = await process.communicate()
            
            return {
                "return_code": process.returncode,
                "stdout": stdout.decode(),
                "stderr": stderr.decode(),
                "code": code
            }
        finally:
            # Clean up temporary file
            os.unlink(temp_file)
    
    else:
        raise ValueError(f"Unknown Python REPL action: {action}")

@router.get("/plugins/installed")
async def get_installed_plugins(
    current_user: User = Depends(get_current_user)
):
    """Get list of installed plugins"""
    # This would scan for installed plugins
    # For now, return empty list
    return []

@router.post("/plugins/install")
async def install_plugin(
    plugin_url: str,
    current_user: User = Depends(get_current_user)
):
    """Install a plugin from URL or package"""
    # This would handle plugin installation
    # For now, return mock response
    return {
        "success": True,
        "plugin_name": "mock_plugin",
        "version": "1.0.0",
        "message": "Plugin installed successfully"
    }
