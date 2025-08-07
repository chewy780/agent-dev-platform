from fastapi import APIRouter, Depends, HTTPException, status, WebSocket
from sqlalchemy.orm import Session
from typing import List, Optional
import json
import os
import yaml
from datetime import datetime
import uuid

from core.database import get_db, Agent, User, AgentLog, TaskTrace
from core.config import settings
from models.agent import AgentCreate, AgentUpdate, AgentResponse, AgentListResponse
from services.agent_service import AgentService
from services.auth_service import get_current_user
from core.websocket import websocket_manager, handle_agent_websocket

router = APIRouter()

@router.get("/", response_model=List[AgentListResponse])
async def list_agents(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all agents for the current user"""
    agents = db.query(Agent).filter(Agent.owner_id == current_user.id).offset(skip).limit(limit).all()
    return [AgentListResponse.from_orm(agent) for agent in agents]

@router.post("/", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    agent_data: AgentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new agent"""
    # Check if agent ID already exists
    existing_agent = db.query(Agent).filter(Agent.agent_id == agent_data.agent_id).first()
    if existing_agent:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Agent ID already exists"
        )
    
    # Create agent in database
    agent = Agent(
        agent_id=agent_data.agent_id,
        name=agent_data.name,
        description=agent_data.description,
        config=agent_data.config.dict() if agent_data.config else {},
        api_keys=agent_data.api_keys.dict() if agent_data.api_keys else {},
        tools=agent_data.tools,
        permissions=agent_data.permissions.dict() if agent_data.permissions else {},
        owner_id=current_user.id
    )
    
    db.add(agent)
    db.commit()
    db.refresh(agent)
    
    # Save agent config to file
    await AgentService.save_agent_config(agent)
    
    return AgentResponse.from_orm(agent)

@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific agent by ID"""
    agent = db.query(Agent).filter(
        Agent.agent_id == agent_id,
        Agent.owner_id == current_user.id
    ).first()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
    
    return AgentResponse.from_orm(agent)

@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: str,
    agent_data: AgentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update an existing agent"""
    agent = db.query(Agent).filter(
        Agent.agent_id == agent_id,
        Agent.owner_id == current_user.id
    ).first()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
    
    # Update fields
    if agent_data.name is not None:
        agent.name = agent_data.name
    if agent_data.description is not None:
        agent.description = agent_data.description
    if agent_data.config is not None:
        agent.config = agent_data.config.dict()
    if agent_data.api_keys is not None:
        agent.api_keys = agent_data.api_keys.dict()
    if agent_data.tools is not None:
        agent.tools = agent_data.tools
    if agent_data.permissions is not None:
        agent.permissions = agent_data.permissions.dict()
    
    agent.updated_at = datetime.now()
    db.commit()
    db.refresh(agent)
    
    # Update agent config file
    await AgentService.save_agent_config(agent)
    
    return AgentResponse.from_orm(agent)

@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    agent_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete an agent"""
    agent = db.query(Agent).filter(
        Agent.agent_id == agent_id,
        Agent.owner_id == current_user.id
    ).first()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
    
    # Stop agent if running
    if agent.is_running:
        await AgentService.stop_agent(agent_id)
    
    # Delete agent config file
    await AgentService.delete_agent_config(agent_id)
    
    # Delete from database
    db.delete(agent)
    db.commit()
    
    return None

@router.post("/{agent_id}/start")
async def start_agent(
    agent_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Start an agent"""
    agent = db.query(Agent).filter(
        Agent.agent_id == agent_id,
        Agent.owner_id == current_user.id
    ).first()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
    
    if agent.is_running:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Agent is already running"
        )
    
    try:
        await AgentService.start_agent(agent)
        agent.is_running = True
        agent.last_run = datetime.now()
        db.commit()
        
        # Broadcast status change
        await websocket_manager.broadcast_agent_status(agent_id, "running")
        
        return {"message": "Agent started successfully", "agent_id": agent_id}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start agent: {str(e)}"
        )

@router.post("/{agent_id}/stop")
async def stop_agent(
    agent_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Stop an agent"""
    agent = db.query(Agent).filter(
        Agent.agent_id == agent_id,
        Agent.owner_id == current_user.id
    ).first()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
    
    if not agent.is_running:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Agent is not running"
        )
    
    try:
        await AgentService.stop_agent(agent_id)
        agent.is_running = False
        db.commit()
        
        # Broadcast status change
        await websocket_manager.broadcast_agent_status(agent_id, "stopped")
        
        return {"message": "Agent stopped successfully", "agent_id": agent_id}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop agent: {str(e)}"
        )

@router.post("/{agent_id}/restart")
async def restart_agent(
    agent_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Restart an agent"""
    agent = db.query(Agent).filter(
        Agent.agent_id == agent_id,
        Agent.owner_id == current_user.id
    ).first()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
    
    try:
        # Stop if running
        if agent.is_running:
            await AgentService.stop_agent(agent_id)
        
        # Start again
        await AgentService.start_agent(agent)
        agent.is_running = True
        agent.last_run = datetime.now()
        db.commit()
        
        # Broadcast status change
        await websocket_manager.broadcast_agent_status(agent_id, "running")
        
        return {"message": "Agent restarted successfully", "agent_id": agent_id}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to restart agent: {str(e)}"
        )

@router.get("/{agent_id}/logs")
async def get_agent_logs(
    agent_id: str,
    limit: int = 100,
    level: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get logs for a specific agent"""
    agent = db.query(Agent).filter(
        Agent.agent_id == agent_id,
        Agent.owner_id == current_user.id
    ).first()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
    
    query = db.query(AgentLog).filter(AgentLog.agent_id == agent.id)
    
    if level:
        query = query.filter(AgentLog.level == level.upper())
    
    logs = query.order_by(AgentLog.timestamp.desc()).limit(limit).all()
    
    return [
        {
            "id": log.id,
            "level": log.level,
            "message": log.message,
            "metadata": log.metadata,
            "timestamp": log.timestamp.isoformat()
        }
        for log in logs
    ]

@router.get("/{agent_id}/tasks")
async def get_agent_tasks(
    agent_id: str,
    limit: int = 50,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get task traces for a specific agent"""
    agent = db.query(Agent).filter(
        Agent.agent_id == agent_id,
        Agent.owner_id == current_user.id
    ).first()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
    
    query = db.query(TaskTrace).filter(TaskTrace.agent_id == agent.id)
    
    if status:
        query = query.filter(TaskTrace.status == status)
    
    tasks = query.order_by(TaskTrace.started_at.desc()).limit(limit).all()
    
    return [
        {
            "id": task.id,
            "task_id": task.task_id,
            "status": task.status,
            "task_type": task.task_type,
            "input_data": task.input_data,
            "output_data": task.output_data,
            "error_message": task.error_message,
            "started_at": task.started_at.isoformat(),
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "duration_ms": task.duration_ms
        }
        for task in tasks
    ]

@router.websocket("/{agent_id}/ws")
async def agent_websocket(websocket: WebSocket, agent_id: str):
    """WebSocket endpoint for real-time agent communication"""
    await handle_agent_websocket(websocket, agent_id)

@router.post("/{agent_id}/import")
async def import_agent_config(
    agent_id: str,
    config_file: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Import agent configuration from file"""
    agent = db.query(Agent).filter(
        Agent.agent_id == agent_id,
        Agent.owner_id == current_user.id
    ).first()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
    
    try:
        config = await AgentService.import_agent_config(config_file)
        
        # Update agent with imported config
        if "name" in config:
            agent.name = config["name"]
        if "description" in config:
            agent.description = config["description"]
        if "config" in config:
            agent.config = config["config"]
        if "tools" in config:
            agent.tools = config["tools"]
        if "permissions" in config:
            agent.permissions = config["permissions"]
        
        agent.updated_at = datetime.now()
        db.commit()
        
        # Save updated config
        await AgentService.save_agent_config(agent)
        
        return {"message": "Agent configuration imported successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to import configuration: {str(e)}"
        )

@router.get("/{agent_id}/export")
async def export_agent_config(
    agent_id: str,
    format: str = "json",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Export agent configuration to file"""
    agent = db.query(Agent).filter(
        Agent.agent_id == agent_id,
        Agent.owner_id == current_user.id
    ).first()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
    
    try:
        config_data = await AgentService.export_agent_config(agent, format)
        return config_data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export configuration: {str(e)}"
        )
