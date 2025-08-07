# Agent Development Platform

A self-hosted, unrestricted agent development environment built on top of OpenHands.

## 🚀 Features

- **Agent Management**: Create, edit, and run custom agents
- **API Key Management**: Secure storage and management of API credentials per agent
- **Live Browser Preview**: Real-time preview of agent activities
- **Drag & Drop Configuration**: Visual agent builder with code-based fallback
- **Real-time Chat Interface**: Live interaction with each agent
- **Comprehensive Logging**: Task traces, console logs, and debugging information
- **Hot Reloading**: Restart agents without losing state
- **Plugin System**: Extensible architecture for new tools and capabilities
- **Local-First**: Everything runs on your server, no cloud dependencies

## 🏗️ Architecture

```
agent-dev-platform/
├── backend/                 # FastAPI backend server
│   ├── api/                # REST API endpoints
│   ├── core/               # Core business logic
│   ├── models/             # Data models and schemas
│   ├── services/           # Business services
│   └── utils/              # Utility functions
├── frontend/               # React + Tailwind frontend
│   ├── src/
│   │   ├── components/     # Reusable UI components
│   │   ├── pages/          # Page components
│   │   ├── hooks/          # Custom React hooks
│   │   ├── services/       # API client services
│   │   └── utils/          # Frontend utilities
├── agents/                 # Agent configuration storage
├── docker/                 # Docker configuration
└── docs/                   # Documentation
```

## 🛠️ Tech Stack

- **Backend**: FastAPI (Python)
- **Frontend**: React + TypeScript + Tailwind CSS
- **Real-time**: WebSocket connections
- **Storage**: JSON/YAML files + SQLite
- **Containerization**: Docker + Docker Compose
- **Agent Runtime**: OpenHands integration

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- Node.js 18+ (for development)
- Python 3.9+ (for development)

### Installation

1. **Clone and setup**:
```bash
git clone <repository>
cd agent-dev-platform
```

2. **Start with Docker**:
```bash
docker-compose up -d
```

3. **Access the platform**:
- Frontend: http://51.81.187.172:3000
- Backend API: http://51.81.187.172:5000
- API Docs: http://51.81.187.172:5000/docs

### Development Setup

1. **Backend**:
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 5000
```

2. **Frontend**:
```bash
cd frontend
npm install
npm run dev
```

## 📋 Agent Configuration

Agents are stored as JSON/YAML files in the `/agents` directory:

```json
{
  "id": "web-assistant",
  "name": "Web Assistant",
  "description": "Agent for web browsing and automation",
  "api_keys": {
    "openai": "sk-...",
    "anthropic": "sk-ant-..."
  },
  "tools": [
    "browser",
    "file_system",
    "shell"
  ],
  "config": {
    "model": "gpt-4",
    "temperature": 0.7,
    "max_tokens": 4000
  },
  "permissions": {
    "file_access": true,
    "shell_access": true,
    "network_access": true
  }
}
```

## 🔧 Configuration

Environment variables in `.env`:

```bash
# Server Configuration
HOST=51.81.187.172
FRONTEND_PORT=3000
BACKEND_PORT=5000

# Database
DATABASE_URL=sqlite:///./agents.db

# Security
SECRET_KEY=your-secret-key
JWT_SECRET=your-jwt-secret

# OpenHands Integration
OPENHANDS_RUNTIME_URL=http://localhost:3000
```

## 🔌 Plugin Development

The platform supports custom plugins for extending agent capabilities:

```python
# plugins/custom_tool.py
from typing import Dict, Any
from .base import BasePlugin

class CustomToolPlugin(BasePlugin):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
    
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        # Your custom logic here
        return {"result": "success"}
```

## 📊 Monitoring & Logs

- **Agent Logs**: Real-time logs for each agent
- **Task Traces**: Detailed execution traces
- **Performance Metrics**: Response times, success rates
- **Error Tracking**: Comprehensive error logging

## 🔒 Security

- API key encryption at rest
- JWT-based authentication
- Role-based access control
- Secure WebSocket connections
- Input validation and sanitization

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details.
