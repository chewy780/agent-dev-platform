from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import uvicorn
import os
from dotenv import load_dotenv

from api.routes import agents, auth, chat, logs, tools
from core.config import settings
from core.database import init_db
from core.websocket import websocket_manager

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    print("🚀 Agent Development Platform started")
    yield
    # Shutdown
    await websocket_manager.disconnect_all()
    print("🛑 Agent Development Platform stopped")

app = FastAPI(
    title="Agent Development Platform",
    description="Self-hosted, unrestricted agent development environment",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://51.81.187.172:3000",
        "http://51.81.187.172:5000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(agents.router, prefix="/api/agents", tags=["Agents"])
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
app.include_router(logs.router, prefix="/api/logs", tags=["Logs"])
app.include_router(tools.router, prefix="/api/tools", tags=["Tools"])

# Health check
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "agent-dev-platform"}

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Agent Development Platform API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc"
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=5000,
        reload=True,
        log_level="info"
    )
