from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List, Optional
import json
import asyncio
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.agent_connections: Dict[str, List[WebSocket]] = {}
        self.user_connections: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, connection_type: str, identifier: str):
        await websocket.accept()
        
        if connection_type == "agent":
            if identifier not in self.agent_connections:
                self.agent_connections[identifier] = []
            self.agent_connections[identifier].append(websocket)
        elif connection_type == "user":
            if identifier not in self.user_connections:
                self.user_connections[identifier] = []
            self.user_connections[identifier].append(websocket)
        else:
            if identifier not in self.active_connections:
                self.active_connections[identifier] = []
            self.active_connections[identifier].append(websocket)
        
        logger.info(f"WebSocket connected: {connection_type}:{identifier}")
    
    def disconnect(self, websocket: WebSocket, connection_type: str, identifier: str):
        if connection_type == "agent" and identifier in self.agent_connections:
            if websocket in self.agent_connections[identifier]:
                self.agent_connections[identifier].remove(websocket)
            if not self.agent_connections[identifier]:
                del self.agent_connections[identifier]
        elif connection_type == "user" and identifier in self.user_connections:
            if websocket in self.user_connections[identifier]:
                self.user_connections[identifier].remove(websocket)
            if not self.user_connections[identifier]:
                del self.user_connections[identifier]
        else:
            if identifier in self.active_connections:
                if websocket in self.active_connections[identifier]:
                    self.active_connections[identifier].remove(websocket)
                if not self.active_connections[identifier]:
                    del self.active_connections[identifier]
        
        logger.info(f"WebSocket disconnected: {connection_type}:{identifier}")
    
    async def send_personal_message(self, message: dict, connection_type: str, identifier: str):
        connections = []
        if connection_type == "agent":
            connections = self.agent_connections.get(identifier, [])
        elif connection_type == "user":
            connections = self.user_connections.get(identifier, [])
        else:
            connections = self.active_connections.get(identifier, [])
        
        for connection in connections:
            try:
                await connection.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error sending message to {connection_type}:{identifier}: {e}")
                await self.disconnect(connection, connection_type, identifier)
    
    async def broadcast_to_agent(self, agent_id: str, message: dict):
        """Broadcast message to all connections for a specific agent"""
        if agent_id in self.agent_connections:
            for connection in self.agent_connections[agent_id]:
                try:
                    await connection.send_text(json.dumps(message))
                except Exception as e:
                    logger.error(f"Error broadcasting to agent {agent_id}: {e}")
                    await self.disconnect(connection, "agent", agent_id)
    
    async def broadcast_to_user(self, user_id: str, message: dict):
        """Broadcast message to all connections for a specific user"""
        if user_id in self.user_connections:
            for connection in self.user_connections[user_id]:
                try:
                    await connection.send_text(json.dumps(message))
                except Exception as e:
                    logger.error(f"Error broadcasting to user {user_id}: {e}")
                    await self.disconnect(connection, "user", user_id)
    
    async def broadcast_log(self, agent_id: str, log_data: dict):
        """Broadcast log message to agent and user connections"""
        message = {
            "type": "log",
            "agent_id": agent_id,
            "timestamp": datetime.now().isoformat(),
            "data": log_data
        }
        
        # Send to agent connections
        await self.broadcast_to_agent(agent_id, message)
        
        # Send to user connections (if we can determine the user)
        # This would need to be implemented based on your user-agent mapping
    
    async def broadcast_chat(self, agent_id: str, chat_data: dict):
        """Broadcast chat message to agent and user connections"""
        message = {
            "type": "chat",
            "agent_id": agent_id,
            "timestamp": datetime.now().isoformat(),
            "data": chat_data
        }
        
        await self.broadcast_to_agent(agent_id, message)
    
    async def broadcast_agent_status(self, agent_id: str, status: str):
        """Broadcast agent status change"""
        message = {
            "type": "agent_status",
            "agent_id": agent_id,
            "status": status,
            "timestamp": datetime.now().isoformat()
        }
        
        await self.broadcast_to_agent(agent_id, message)
    
    async def disconnect_all(self):
        """Disconnect all active connections"""
        for connections in self.active_connections.values():
            for connection in connections:
                try:
                    await connection.close()
                except:
                    pass
        
        for connections in self.agent_connections.values():
            for connection in connections:
                try:
                    await connection.close()
                except:
                    pass
        
        for connections in self.user_connections.values():
            for connection in connections:
                try:
                    await connection.close()
                except:
                    pass
        
        self.active_connections.clear()
        self.agent_connections.clear()
        self.user_connections.clear()

# Global WebSocket manager instance
websocket_manager = ConnectionManager()

# WebSocket endpoint handlers
async def handle_agent_websocket(websocket: WebSocket, agent_id: str):
    await websocket_manager.connect(websocket, "agent", agent_id)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle incoming messages from agent
            if message.get("type") == "log":
                await websocket_manager.broadcast_log(agent_id, message.get("data", {}))
            elif message.get("type") == "chat":
                await websocket_manager.broadcast_chat(agent_id, message.get("data", {}))
            elif message.get("type") == "status":
                await websocket_manager.broadcast_agent_status(agent_id, message.get("status", "unknown"))
            
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket, "agent", agent_id)
    except Exception as e:
        logger.error(f"WebSocket error for agent {agent_id}: {e}")
        websocket_manager.disconnect(websocket, "agent", agent_id)

async def handle_user_websocket(websocket: WebSocket, user_id: str):
    await websocket_manager.connect(websocket, "user", user_id)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle incoming messages from user
            # This could include commands to start/stop agents, etc.
            
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket, "user", user_id)
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
        websocket_manager.disconnect(websocket, "user", user_id)
