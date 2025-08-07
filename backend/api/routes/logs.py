from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta

from core.database import get_db, Agent, AgentLog, User
from models.logs import LogEntry, LogFilter, LogStats
from services.auth_service import get_current_user

router = APIRouter()

@router.get("/{agent_id}", response_model=List[LogEntry])
async def get_agent_logs(
    agent_id: str,
    level: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get logs for a specific agent with filtering"""
    # Verify agent ownership
    agent = db.query(Agent).filter(
        Agent.agent_id == agent_id,
        Agent.owner_id == current_user.id
    ).first()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
    
    # Build query
    query = db.query(AgentLog).filter(AgentLog.agent_id == agent.id)
    
    # Apply filters
    if level:
        query = query.filter(AgentLog.level == level.upper())
    
    if start_time:
        query = query.filter(AgentLog.timestamp >= start_time)
    
    if end_time:
        query = query.filter(AgentLog.timestamp <= end_time)
    
    if search:
        query = query.filter(AgentLog.message.contains(search))
    
    # Get logs
    logs = query.order_by(AgentLog.timestamp.desc()).offset(offset).limit(limit).all()
    
    return [LogEntry.from_orm(log) for log in logs]

@router.get("/{agent_id}/stats", response_model=LogStats)
async def get_log_stats(
    agent_id: str,
    days: int = 7,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get log statistics for an agent"""
    # Verify agent ownership
    agent = db.query(Agent).filter(
        Agent.agent_id == agent_id,
        Agent.owner_id == current_user.id
    ).first()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
    
    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    # Get log counts by level
    from sqlalchemy import func
    
    level_stats = db.query(
        AgentLog.level,
        func.count(AgentLog.id).label('count')
    ).filter(
        AgentLog.agent_id == agent.id,
        AgentLog.timestamp >= start_date,
        AgentLog.timestamp <= end_date
    ).group_by(AgentLog.level).all()
    
    # Get total logs
    total_logs = db.query(func.count(AgentLog.id)).filter(
        AgentLog.agent_id == agent.id,
        AgentLog.timestamp >= start_date,
        AgentLog.timestamp <= end_date
    ).scalar()
    
    # Get logs by hour for the last 24 hours
    hourly_stats = db.query(
        func.strftime('%H', AgentLog.timestamp).label('hour'),
        func.count(AgentLog.id).label('count')
    ).filter(
        AgentLog.agent_id == agent.id,
        AgentLog.timestamp >= end_date - timedelta(hours=24)
    ).group_by(
        func.strftime('%H', AgentLog.timestamp)
    ).order_by('hour').all()
    
    return LogStats(
        agent_id=agent_id,
        total_logs=total_logs,
        level_distribution={level: count for level, count in level_stats},
        hourly_distribution={hour: count for hour, count in hourly_stats},
        date_range_start=start_date,
        date_range_end=end_date
    )

@router.delete("/{agent_id}")
async def clear_agent_logs(
    agent_id: str,
    before_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Clear logs for an agent"""
    # Verify agent ownership
    agent = db.query(Agent).filter(
        Agent.agent_id == agent_id,
        Agent.owner_id == current_user.id
    ).first()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
    
    # Build delete query
    query = db.query(AgentLog).filter(AgentLog.agent_id == agent.id)
    
    if before_date:
        query = query.filter(AgentLog.timestamp < before_date)
    
    # Delete logs
    deleted_count = query.delete()
    db.commit()
    
    return {"message": f"Deleted {deleted_count} log entries"}

@router.get("/{agent_id}/export")
async def export_logs(
    agent_id: str,
    format: str = "json",
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Export logs for an agent"""
    from fastapi.responses import Response
    import json
    import csv
    from io import StringIO
    
    # Verify agent ownership
    agent = db.query(Agent).filter(
        Agent.agent_id == agent_id,
        Agent.owner_id == current_user.id
    ).first()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
    
    # Build query
    query = db.query(AgentLog).filter(AgentLog.agent_id == agent.id)
    
    if start_time:
        query = query.filter(AgentLog.timestamp >= start_time)
    
    if end_time:
        query = query.filter(AgentLog.timestamp <= end_time)
    
    logs = query.order_by(AgentLog.timestamp.desc()).all()
    
    if format.lower() == "csv":
        # Export as CSV
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(["Timestamp", "Level", "Message", "Metadata"])
        
        for log in logs:
            writer.writerow([
                log.timestamp.isoformat(),
                log.level,
                log.message,
                json.dumps(log.metadata) if log.metadata else ""
            ])
        
        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={agent_id}_logs.csv"}
        )
    else:
        # Export as JSON
        log_data = [
            {
                "timestamp": log.timestamp.isoformat(),
                "level": log.level,
                "message": log.message,
                "metadata": log.metadata
            }
            for log in logs
        ]
        
        return Response(
            content=json.dumps(log_data, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename={agent_id}_logs.json"}
        )

@router.get("/{agent_id}/realtime")
async def get_realtime_logs(
    agent_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get real-time logs for an agent (SSE)"""
    from fastapi.responses import StreamingResponse
    import asyncio
    
    # Verify agent ownership
    agent = db.query(Agent).filter(
        Agent.agent_id == agent_id,
        Agent.owner_id == current_user.id
    ).first()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
    
    async def generate_log_stream():
        """Generate streaming log data"""
        last_log_id = 0
        
        while True:
            # Get new logs since last check
            new_logs = db.query(AgentLog).filter(
                AgentLog.agent_id == agent.id,
                AgentLog.id > last_log_id
            ).order_by(AgentLog.timestamp.asc()).all()
            
            for log in new_logs:
                log_data = {
                    "id": log.id,
                    "timestamp": log.timestamp.isoformat(),
                    "level": log.level,
                    "message": log.message,
                    "metadata": log.metadata
                }
                
                yield f"data: {json.dumps(log_data)}\n\n"
                last_log_id = log.id
            
            await asyncio.sleep(1)  # Check every second
    
    return StreamingResponse(
        generate_log_stream(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream"
        }
    )
