import asyncio
import json
import yaml
import os
import subprocess
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid
import httpx
from pathlib import Path

from core.config import settings
from core.database import Agent, AgentLog, TaskTrace
from core.websocket import websocket_manager

logger = logging.getLogger(__name__)

class AgentService:
    """Service for managing agent lifecycle and operations"""
    
    _running_agents: Dict[str, asyncio.Task] = {}
    _agent_processes: Dict[str, subprocess.Popen] = {}
    
    @classmethod
    async def save_agent_config(cls, agent: Agent) -> None:
        """Save agent configuration to file"""
        config_path = Path(settings.agents_dir) / f"{agent.agent_id}.json"
        
        config_data = {
            "id": agent.agent_id,
            "name": agent.name,
            "description": agent.description,
            "config": agent.config,
            "api_keys": agent.api_keys,
            "tools": agent.tools,
            "permissions": agent.permissions,
            "created_at": agent.created_at.isoformat(),
            "updated_at": agent.updated_at.isoformat()
        }
        
        with open(config_path, 'w') as f:
            json.dump(config_data, f, indent=2, default=str)
        
        logger.info(f"Saved agent config: {config_path}")
    
    @classmethod
    async def load_agent_config(cls, agent_id: str) -> Dict[str, Any]:
        """Load agent configuration from file"""
        config_path = Path(settings.agents_dir) / f"{agent_id}.json"
        
        if not config_path.exists():
            raise FileNotFoundError(f"Agent config not found: {config_path}")
        
        with open(config_path, 'r') as f:
            config_data = json.load(f)
        
        return config_data
    
    @classmethod
    async def delete_agent_config(cls, agent_id: str) -> None:
        """Delete agent configuration file"""
        config_path = Path(settings.agents_dir) / f"{agent_id}.json"
        
        if config_path.exists():
            config_path.unlink()
            logger.info(f"Deleted agent config: {config_path}")
    
    @classmethod
    async def start_agent(cls, agent: Agent) -> None:
        """Start an agent using OpenHands integration"""
        if agent.agent_id in cls._running_agents:
            raise RuntimeError(f"Agent {agent.agent_id} is already running")
        
        try:
            # Create agent workspace
            workspace_path = Path(settings.agents_dir) / "workspaces" / agent.agent_id
            workspace_path.mkdir(parents=True, exist_ok=True)
            
            # Prepare agent environment
            env_vars = cls._prepare_agent_environment(agent)
            
            # Start agent process using OpenHands
            process = await cls._start_openhands_agent(agent, workspace_path, env_vars)
            
            # Store process reference
            cls._agent_processes[agent.agent_id] = process
            
            # Create monitoring task
            monitor_task = asyncio.create_task(
                cls._monitor_agent_process(agent.agent_id, process)
            )
            cls._running_agents[agent.agent_id] = monitor_task
            
            # Log agent start
            await cls._log_agent_event(agent.id, "INFO", f"Agent {agent.agent_id} started successfully")
            
            logger.info(f"Started agent: {agent.agent_id}")
            
        except Exception as e:
            logger.error(f"Failed to start agent {agent.agent_id}: {e}")
            await cls._log_agent_event(agent.id, "ERROR", f"Failed to start agent: {str(e)}")
            raise
    
    @classmethod
    async def stop_agent(cls, agent_id: str) -> None:
        """Stop a running agent"""
        if agent_id not in cls._running_agents:
            logger.warning(f"Agent {agent_id} is not running")
            return
        
        try:
            # Cancel monitoring task
            monitor_task = cls._running_agents[agent_id]
            monitor_task.cancel()
            
            # Terminate process
            if agent_id in cls._agent_processes:
                process = cls._agent_processes[agent_id]
                process.terminate()
                
                # Wait for graceful shutdown
                try:
                    await asyncio.wait_for(process.wait(), timeout=10.0)
                except asyncio.TimeoutError:
                    process.kill()
                    await process.wait()
                
                del cls._agent_processes[agent_id]
            
            del cls._running_agents[agent_id]
            
            logger.info(f"Stopped agent: {agent_id}")
            
        except Exception as e:
            logger.error(f"Error stopping agent {agent_id}: {e}")
            raise
    
    @classmethod
    async def restart_agent(cls, agent: Agent) -> None:
        """Restart an agent"""
        if agent.agent_id in cls._running_agents:
            await cls.stop_agent(agent.agent_id)
        
        await asyncio.sleep(1)  # Brief pause
        await cls.start_agent(agent)
    
    @classmethod
    def _prepare_agent_environment(cls, agent: Agent) -> Dict[str, str]:
        """Prepare environment variables for agent"""
        env_vars = {
            "AGENT_ID": agent.agent_id,
            "AGENT_NAME": agent.name,
            "AGENT_CONFIG": json.dumps(agent.config),
            "AGENT_TOOLS": json.dumps(agent.tools),
            "AGENT_PERMISSIONS": json.dumps(agent.permissions),
            "WEBSOCKET_URL": f"ws://localhost:5000/api/agents/{agent.agent_id}/ws",
            "API_BASE_URL": "http://localhost:5000/api",
        }
        
        # Add API keys to environment
        if agent.api_keys:
            for provider, key in agent.api_keys.items():
                if key:
                    env_vars[f"{provider.upper()}_API_KEY"] = key
        
        return env_vars
    
    @classmethod
    async def _start_openhands_agent(cls, agent: Agent, workspace_path: Path, env_vars: Dict[str, str]) -> subprocess.Popen:
        """Start agent using OpenHands runtime"""
        # This would integrate with the existing OpenHands system
        # For now, we'll create a simple Python process that simulates an agent
        
        agent_script = f"""
import asyncio
import json
import os
import websockets
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AgentRuntime:
    def __init__(self, agent_id, config, tools, permissions):
        self.agent_id = agent_id
        self.config = config
        self.tools = tools
        self.permissions = permissions
        self.websocket = None
        
    async def connect_websocket(self):
        websocket_url = os.getenv('WEBSOCKET_URL')
        if websocket_url:
            try:
                self.websocket = await websockets.connect(websocket_url)
                logger.info(f"Connected to WebSocket: {{websocket_url}}")
            except Exception as e:
                logger.error(f"Failed to connect to WebSocket: {{e}}")
    
    async def send_log(self, level, message, metadata=None):
        if self.websocket:
            log_data = {{
                "type": "log",
                "level": level,
                "message": message,
                "metadata": metadata or {{}},
                "timestamp": datetime.now().isoformat()
            }}
            await self.websocket.send(json.dumps(log_data))
    
    async def run(self):
        await self.connect_websocket()
        await self.send_log("INFO", f"Agent {{self.agent_id}} started")
        
        # Simulate agent running
        while True:
            await asyncio.sleep(5)
            await self.send_log("INFO", f"Agent {{self.agent_id}} heartbeat")

if __name__ == "__main__":
    agent_id = os.getenv('AGENT_ID')
    config = json.loads(os.getenv('AGENT_CONFIG', '{{}}'))
    tools = json.loads(os.getenv('AGENT_TOOLS', '[]'))
    permissions = json.loads(os.getenv('AGENT_PERMISSIONS', '{{}}'))
    
    agent = AgentRuntime(agent_id, config, tools, permissions)
    asyncio.run(agent.run())
"""
        
        # Write agent script to workspace
        script_path = workspace_path / "agent_runtime.py"
        with open(script_path, 'w') as f:
            f.write(agent_script)
        
        # Start the agent process
        process = subprocess.Popen(
            ["python", str(script_path)],
            cwd=str(workspace_path),
            env={**os.environ, **env_vars},
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        return process
    
    @classmethod
    async def _monitor_agent_process(cls, agent_id: str, process: subprocess.Popen) -> None:
        """Monitor agent process and handle output"""
        try:
            while process.poll() is None:
                # Read stdout
                if process.stdout:
                    line = process.stdout.readline()
                    if line:
                        await cls._log_agent_event(agent_id, "INFO", line.strip())
                
                # Read stderr
                if process.stderr:
                    line = process.stderr.readline()
                    if line:
                        await cls._log_agent_event(agent_id, "ERROR", line.strip())
                
                await asyncio.sleep(0.1)
            
            # Process finished
            return_code = process.returncode
            if return_code != 0:
                await cls._log_agent_event(agent_id, "ERROR", f"Agent process exited with code {return_code}")
            else:
                await cls._log_agent_event(agent_id, "INFO", "Agent process finished normally")
                
        except Exception as e:
            logger.error(f"Error monitoring agent {agent_id}: {e}")
            await cls._log_agent_event(agent_id, "ERROR", f"Monitoring error: {str(e)}")
    
    @classmethod
    async def _log_agent_event(cls, agent_id: str, level: str, message: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Log agent event to database and broadcast via WebSocket"""
        # This would typically save to database
        # For now, we'll just broadcast via WebSocket
        
        log_data = {
            "level": level,
            "message": message,
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat()
        }
        
        await websocket_manager.broadcast_log(agent_id, log_data)
    
    @classmethod
    async def import_agent_config(cls, config_file: str) -> Dict[str, Any]:
        """Import agent configuration from file"""
        config_path = Path(config_file)
        
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_file}")
        
        if config_path.suffix.lower() == '.yaml' or config_path.suffix.lower() == '.yml':
            with open(config_path, 'r') as f:
                config_data = yaml.safe_load(f)
        else:
            with open(config_path, 'r') as f:
                config_data = json.load(f)
        
        return config_data
    
    @classmethod
    async def export_agent_config(cls, agent: Agent, format: str = "json") -> Dict[str, Any]:
        """Export agent configuration"""
        config_data = {
            "id": agent.agent_id,
            "name": agent.name,
            "description": agent.description,
            "config": agent.config,
            "tools": agent.tools,
            "permissions": agent.permissions,
            "created_at": agent.created_at.isoformat(),
            "updated_at": agent.updated_at.isoformat()
        }
        
        if format.lower() == "yaml":
            return {
                "content": yaml.dump(config_data, default_flow_style=False),
                "filename": f"{agent.agent_id}.yaml",
                "content_type": "text/yaml"
            }
        else:
            return {
                "content": json.dumps(config_data, indent=2, default=str),
                "filename": f"{agent.agent_id}.json",
                "content_type": "application/json"
            }
    
    @classmethod
    async def get_agent_status(cls, agent_id: str) -> Dict[str, Any]:
        """Get current status of an agent"""
        is_running = agent_id in cls._running_agents
        
        status_data = {
            "agent_id": agent_id,
            "is_running": is_running,
            "status": "running" if is_running else "stopped",
            "uptime_seconds": None,
            "memory_usage_mb": None,
            "cpu_usage_percent": None
        }
        
        if is_running and agent_id in cls._agent_processes:
            process = cls._agent_processes[agent_id]
            try:
                # Get process info (platform specific)
                import psutil
                proc = psutil.Process(process.pid)
                status_data["memory_usage_mb"] = proc.memory_info().rss / 1024 / 1024
                status_data["cpu_usage_percent"] = proc.cpu_percent()
            except ImportError:
                pass  # psutil not available
        
        return status_data
    
    @classmethod
    async def list_running_agents(cls) -> List[str]:
        """Get list of currently running agent IDs"""
        return list(cls._running_agents.keys())
    
    @classmethod
    async def get_agent_metrics(cls, agent_id: str) -> Dict[str, Any]:
        """Get metrics for an agent"""
        # This would typically query the database for metrics
        # For now, return basic metrics
        return {
            "agent_id": agent_id,
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "average_response_time_ms": 0.0,
            "total_tokens_used": 0,
            "last_24h_requests": 0,
            "last_24h_tokens": 0
        }
