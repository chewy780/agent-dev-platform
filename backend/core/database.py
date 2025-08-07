from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func
from datetime import datetime
import json
from typing import Dict, Any

from core.config import settings

# Database setup
engine = create_engine(settings.database_url, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def init_db():
    Base.metadata.create_all(bind=engine)

# Models
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    agents = relationship("Agent", back_populates="owner")
    api_keys = relationship("APIKey", back_populates="user")

class Agent(Base):
    __tablename__ = "agents"
    
    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(String, unique=True, index=True)  # Custom agent ID
    name = Column(String, index=True)
    description = Column(Text)
    config = Column(JSON)  # Agent configuration
    api_keys = Column(JSON)  # Encrypted API keys
    tools = Column(JSON)  # Available tools
    permissions = Column(JSON)  # Agent permissions
    is_active = Column(Boolean, default=True)
    is_running = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    last_run = Column(DateTime)
    
    # Foreign keys
    owner_id = Column(Integer, ForeignKey("users.id"))
    
    # Relationships
    owner = relationship("User", back_populates="agents")
    logs = relationship("AgentLog", back_populates="agent")
    chats = relationship("ChatMessage", back_populates="agent")

class APIKey(Base):
    __tablename__ = "api_keys"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    provider = Column(String, index=True)  # openai, anthropic, etc.
    encrypted_key = Column(String)  # Encrypted API key
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    
    # Foreign keys
    user_id = Column(Integer, ForeignKey("users.id"))
    
    # Relationships
    user = relationship("User", back_populates="api_keys")

class AgentLog(Base):
    __tablename__ = "agent_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    level = Column(String, index=True)  # INFO, WARNING, ERROR, DEBUG
    message = Column(Text)
    metadata = Column(JSON)  # Additional log data
    timestamp = Column(DateTime, default=func.now())
    
    # Foreign keys
    agent_id = Column(Integer, ForeignKey("agents.id"))
    
    # Relationships
    agent = relationship("Agent", back_populates="logs")

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    role = Column(String, index=True)  # user, assistant, system
    content = Column(Text)
    metadata = Column(JSON)  # Additional message data
    timestamp = Column(DateTime, default=func.now())
    
    # Foreign keys
    agent_id = Column(Integer, ForeignKey("agents.id"))
    
    # Relationships
    agent = relationship("Agent", back_populates="chats")

class TaskTrace(Base):
    __tablename__ = "task_traces"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String, unique=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"))
    status = Column(String, index=True)  # pending, running, completed, failed
    task_type = Column(String, index=True)
    input_data = Column(JSON)
    output_data = Column(JSON)
    error_message = Column(Text)
    started_at = Column(DateTime, default=func.now())
    completed_at = Column(DateTime)
    duration_ms = Column(Integer)
    
    # Relationships
    agent = relationship("Agent")

# Utility functions
def serialize_model(model):
    """Convert SQLAlchemy model to dict"""
    if hasattr(model, '__table__'):
        return {c.name: getattr(model, c.name) for c in model.__table__.columns}
    return model

def deserialize_json(json_data: str) -> Dict[str, Any]:
    """Safely deserialize JSON data"""
    if isinstance(json_data, dict):
        return json_data
    try:
        return json.loads(json_data) if json_data else {}
    except json.JSONDecodeError:
        return {}
