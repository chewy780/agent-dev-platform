from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from typing import List, Optional
import json
from datetime import datetime

from core.database import get_db, Agent, ChatMessage, User
from models.chat import ChatMessageCreate, ChatMessageResponse, ChatSession
from services.auth_service import get_current_user
from core.websocket import websocket_manager

router = APIRouter()

@router.get("/{agent_id}/messages", response_model=List[ChatMessageResponse])
async def get_chat_messages(
    agent_id: str,
    limit: int = 50,
    before_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get chat messages for a specific agent"""
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
    query = db.query(ChatMessage).filter(ChatMessage.agent_id == agent.id)
    
    if before_id:
        query = query.filter(ChatMessage.id < before_id)
    
    messages = query.order_by(ChatMessage.timestamp.desc()).limit(limit).all()
    
    return [ChatMessageResponse.from_orm(msg) for msg in reversed(messages)]

@router.post("/{agent_id}/messages", response_model=ChatMessageResponse)
async def send_message(
    agent_id: str,
    message_data: ChatMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Send a message to an agent"""
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
    
    # Create chat message
    chat_message = ChatMessage(
        role="user",
        content=message_data.content,
        metadata=message_data.metadata or {},
        agent_id=agent.id
    )
    
    db.add(chat_message)
    db.commit()
    db.refresh(chat_message)
    
    # Broadcast message to agent via WebSocket
    await websocket_manager.broadcast_chat(agent_id, {
        "id": chat_message.id,
        "role": chat_message.role,
        "content": chat_message.content,
        "metadata": chat_message.metadata,
        "timestamp": chat_message.timestamp.isoformat()
    })
    
    return ChatMessageResponse.from_orm(chat_message)

@router.get("/{agent_id}/sessions", response_model=List[ChatSession])
async def get_chat_sessions(
    agent_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get chat sessions for an agent"""
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
    
    # Get unique sessions (grouped by date for now)
    from sqlalchemy import func, distinct
    
    sessions = db.query(
        func.date(ChatMessage.timestamp).label('session_date'),
        func.count(ChatMessage.id).label('message_count'),
        func.min(ChatMessage.timestamp).label('start_time'),
        func.max(ChatMessage.timestamp).label('end_time')
    ).filter(
        ChatMessage.agent_id == agent.id
    ).group_by(
        func.date(ChatMessage.timestamp)
    ).order_by(
        func.date(ChatMessage.timestamp).desc()
    ).all()
    
    return [
        ChatSession(
            session_id=f"{agent_id}_{session.session_date}",
            agent_id=agent_id,
            session_date=session.session_date,
            message_count=session.message_count,
            start_time=session.start_time,
            end_time=session.end_time
        )
        for session in sessions
    ]

@router.delete("/{agent_id}/messages")
async def clear_chat_history(
    agent_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Clear chat history for an agent"""
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
    
    # Delete all messages for this agent
    db.query(ChatMessage).filter(ChatMessage.agent_id == agent.id).delete()
    db.commit()
    
    return {"message": "Chat history cleared successfully"}

@router.websocket("/{agent_id}/chat")
async def chat_websocket(websocket: WebSocket, agent_id: str):
    """WebSocket endpoint for real-time chat with agent"""
    await websocket.accept()
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "message":
                # Handle incoming chat message
                chat_data = {
                    "role": "user",
                    "content": message.get("content", ""),
                    "metadata": message.get("metadata", {}),
                    "timestamp": datetime.now().isoformat()
                }
                
                # Broadcast to agent
                await websocket_manager.broadcast_chat(agent_id, chat_data)
                
                # Send confirmation back to client
                await websocket.send_text(json.dumps({
                    "type": "message_sent",
                    "data": chat_data
                }))
            
            elif message.get("type") == "typing":
                # Handle typing indicator
                await websocket_manager.broadcast_chat(agent_id, {
                    "type": "typing",
                    "user_id": message.get("user_id"),
                    "is_typing": message.get("is_typing", False)
                })
    
    except WebSocketDisconnect:
        # Handle disconnect
        pass
    except Exception as e:
        # Handle other errors
        await websocket.send_text(json.dumps({
            "type": "error",
            "message": str(e)
        }))

@router.post("/{agent_id}/stream")
async def stream_chat_response(
    agent_id: str,
    message_data: ChatMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Stream chat response from agent (for SSE)"""
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
    
    async def generate_response():
        """Generate streaming response"""
        # Send initial message
        yield f"data: {json.dumps({'type': 'start', 'message': 'Starting response generation...'})}\n\n"
        
        # Simulate agent processing
        await asyncio.sleep(1)
        yield f"data: {json.dumps({'type': 'thinking', 'message': 'Agent is thinking...'})}\n\n"
        
        await asyncio.sleep(2)
        yield f"data: {json.dumps({'type': 'content', 'content': 'Hello! I am your AI agent. How can I help you today?'})}\n\n"
        
        await asyncio.sleep(1)
        yield f"data: {json.dumps({'type': 'end', 'message': 'Response complete'})}\n\n"
    
    return StreamingResponse(
        generate_response(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream"
        }
    )
