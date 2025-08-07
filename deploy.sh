#!/bin/bash

# Agent Development Platform Deployment Script
# This script sets up and deploys the platform on your server

set -e

echo "🚀 Starting Agent Development Platform deployment..."

# Configuration
HOST_IP="51.81.187.172"
FRONTEND_PORT=3000
BACKEND_PORT=5000
REDIS_PORT=6379

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   print_error "This script should not be run as root"
   exit 1
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

print_status "Checking system requirements..."

# Check available ports
check_port() {
    local port=$1
    if netstat -tuln | grep -q ":$port "; then
        print_warning "Port $port is already in use"
        return 1
    fi
    return 0
}

check_port $FRONTEND_PORT || print_warning "Frontend port $FRONTEND_PORT is in use"
check_port $BACKEND_PORT || print_warning "Backend port $BACKEND_PORT is in use"
check_port $REDIS_PORT || print_warning "Redis port $REDIS_PORT is in use"

# Create necessary directories
print_status "Creating directories..."
mkdir -p agents logs uploads data

# Set up environment variables
print_status "Setting up environment variables..."

cat > .env << EOF
# Server Configuration
HOST=$HOST_IP
FRONTEND_PORT=$FRONTEND_PORT
BACKEND_PORT=$BACKEND_PORT

# Database
DATABASE_URL=sqlite:///./agents.db

# Security (CHANGE THESE IN PRODUCTION!)
SECRET_KEY=$(openssl rand -hex 32)
JWT_SECRET=$(openssl rand -hex 32)

# Redis
REDIS_URL=redis://redis:6379

# OpenHands Integration
OPENHANDS_RUNTIME_URL=http://localhost:3000

# Logging
LOG_LEVEL=INFO
LOG_FILE=./logs/app.log

# Agent Configuration
MAX_AGENTS_PER_USER=10
MAX_CONCURRENT_AGENTS=5
AGENT_TIMEOUT_SECONDS=300
EOF

print_success "Environment variables configured"

# Create nginx configuration
print_status "Setting up nginx configuration..."
mkdir -p nginx

cat > nginx/nginx.conf << EOF
events {
    worker_connections 1024;
}

http {
    upstream frontend {
        server frontend:3000;
    }
    
    upstream backend {
        server backend:5000;
    }
    
    server {
        listen 80;
        server_name $HOST_IP;
        
        # Frontend
        location / {
            proxy_pass http://frontend;
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
            proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto \$scheme;
        }
        
        # Backend API
        location /api/ {
            proxy_pass http://backend;
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
            proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto \$scheme;
        }
        
        # WebSocket support
        location /ws/ {
            proxy_pass http://backend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade \$http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
            proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto \$scheme;
        }
    }
}
EOF

print_success "Nginx configuration created"

# Build and start services
print_status "Building and starting services..."

# Stop any existing containers
docker-compose down --remove-orphans

# Build images
print_status "Building Docker images..."
docker-compose build --no-cache

# Start services
print_status "Starting services..."
docker-compose up -d

# Wait for services to be ready
print_status "Waiting for services to be ready..."
sleep 30

# Check service health
print_status "Checking service health..."

# Check backend
if curl -f http://localhost:$BACKEND_PORT/health > /dev/null 2>&1; then
    print_success "Backend is healthy"
else
    print_error "Backend health check failed"
    docker-compose logs backend
    exit 1
fi

# Check frontend
if curl -f http://localhost:$FRONTEND_PORT > /dev/null 2>&1; then
    print_success "Frontend is healthy"
else
    print_error "Frontend health check failed"
    docker-compose logs frontend
    exit 1
fi

# Check Redis
if docker-compose exec redis redis-cli ping > /dev/null 2>&1; then
    print_success "Redis is healthy"
else
    print_error "Redis health check failed"
    docker-compose logs redis
    exit 1
fi

print_success "All services are healthy!"

# Create initial admin user
print_status "Creating initial admin user..."
docker-compose exec backend python -c "
import asyncio
import sys
sys.path.append('/app')
from core.database import SessionLocal, User
from services.auth_service import get_password_hash

db = SessionLocal()
try:
    # Check if admin user exists
    admin = db.query(User).filter(User.username == 'admin').first()
    if not admin:
        admin = User(
            username='admin',
            email='admin@example.com',
            hashed_password=get_password_hash('admin123'),
            is_active=True,
            is_admin=True
        )
        db.add(admin)
        db.commit()
        print('Admin user created: admin/admin123')
    else:
        print('Admin user already exists')
finally:
    db.close()
"

print_success "Deployment completed successfully!"

echo ""
echo "🎉 Agent Development Platform is now running!"
echo ""
echo "📱 Access URLs:"
echo "   Frontend: http://$HOST_IP:$FRONTEND_PORT"
echo "   Backend API: http://$HOST_IP:$BACKEND_PORT"
echo "   API Docs: http://$HOST_IP:$BACKEND_PORT/docs"
echo ""
echo "🔐 Default credentials:"
echo "   Username: admin"
echo "   Password: admin123"
echo ""
echo "📋 Useful commands:"
echo "   View logs: docker-compose logs -f"
echo "   Stop services: docker-compose down"
echo "   Restart services: docker-compose restart"
echo "   Update: git pull && docker-compose up -d --build"
echo ""
echo "⚠️  IMPORTANT: Change the default admin password after first login!"
echo ""

# Show running containers
print_status "Running containers:"
docker-compose ps
