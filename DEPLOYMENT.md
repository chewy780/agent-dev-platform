# Agent Development Platform - Deployment Guide

This guide will help you deploy the Agent Development Platform on your server.

## 🚀 Quick Start

### Prerequisites

- **Server**: Ubuntu 20.04+ or similar Linux distribution
- **Docker**: Version 20.10+
- **Docker Compose**: Version 2.0+
- **Git**: For cloning the repository
- **OpenSSL**: For generating secure keys

### Automated Deployment

1. **Clone the repository**:
```bash
git clone <your-repo-url>
cd agent-dev-platform
```

2. **Run the deployment script**:
```bash
./deploy.sh
```

The script will:
- Check system requirements
- Set up environment variables
- Create necessary directories
- Build and start all services
- Create an initial admin user
- Verify all services are healthy

### Manual Deployment

If you prefer to deploy manually or need to customize the setup:

#### 1. Install Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Install additional tools
sudo apt install -y curl net-tools openssl
```

#### 2. Configure Environment

Create a `.env` file in the project root:

```bash
# Server Configuration
HOST=51.81.187.172
FRONTEND_PORT=3000
BACKEND_PORT=5000

# Database
DATABASE_URL=sqlite:///./agents.db

# Security (Generate secure keys!)
SECRET_KEY=your-secret-key-here
JWT_SECRET=your-jwt-secret-here

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
```

#### 3. Create Directories

```bash
mkdir -p agents logs uploads data nginx
```

#### 4. Build and Start Services

```bash
# Build images
docker-compose build --no-cache

# Start services
docker-compose up -d

# Check status
docker-compose ps
```

#### 5. Create Admin User

```bash
docker-compose exec backend python -c "
import sys
sys.path.append('/app')
from core.database import SessionLocal, User
from services.auth_service import get_password_hash

db = SessionLocal()
try:
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
finally:
    db.close()
"
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `HOST` | Server IP address | `51.81.187.172` |
| `FRONTEND_PORT` | Frontend port | `3000` |
| `BACKEND_PORT` | Backend API port | `5000` |
| `DATABASE_URL` | Database connection string | `sqlite:///./agents.db` |
| `SECRET_KEY` | Flask secret key | Auto-generated |
| `JWT_SECRET` | JWT signing secret | Auto-generated |
| `REDIS_URL` | Redis connection URL | `redis://redis:6379` |
| `LOG_LEVEL` | Logging level | `INFO` |

### Port Configuration

The platform uses the following ports:

- **3000**: Frontend (React)
- **5000**: Backend API (FastAPI)
- **6379**: Redis (internal)
- **80**: Nginx (optional)

### Security Considerations

1. **Change default passwords**:
   - Default admin: `admin/admin123`
   - Change immediately after deployment

2. **Generate secure keys**:
   ```bash
   openssl rand -hex 32  # For SECRET_KEY
   openssl rand -hex 32  # For JWT_SECRET
   ```

3. **Firewall configuration**:
   ```bash
   sudo ufw allow 3000/tcp  # Frontend
   sudo ufw allow 5000/tcp  # Backend API
   sudo ufw enable
   ```

4. **SSL/TLS** (Production):
   - Use Let's Encrypt for free certificates
   - Configure nginx with SSL
   - Redirect HTTP to HTTPS

## 📊 Monitoring

### Health Checks

```bash
# Check all services
docker-compose ps

# Check individual services
curl http://localhost:5000/health  # Backend
curl http://localhost:3000         # Frontend
docker-compose exec redis redis-cli ping  # Redis
```

### Logs

```bash
# View all logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f redis
```

### Metrics

The platform provides metrics endpoints:

- `/api/health` - Service health
- `/api/metrics` - Performance metrics (if enabled)

## 🔄 Updates

### Update the Platform

```bash
# Pull latest changes
git pull

# Rebuild and restart
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# Check status
docker-compose ps
```

### Backup and Restore

#### Backup

```bash
# Backup database
docker-compose exec backend sqlite3 /app/agents.db ".backup /app/backup/agents_$(date +%Y%m%d_%H%M%S).db"

# Backup agent configurations
tar -czf agent_configs_$(date +%Y%m%d_%H%M%S).tar.gz agents/

# Backup logs
tar -czf logs_$(date +%Y%m%d_%H%M%S).tar.gz logs/
```

#### Restore

```bash
# Restore database
docker-compose exec backend sqlite3 /app/agents.db ".restore /app/backup/agents_20231201_120000.db"

# Restore agent configurations
tar -xzf agent_configs_20231201_120000.tar.gz

# Restart services
docker-compose restart
```

## 🛠️ Troubleshooting

### Common Issues

#### 1. Port Already in Use

```bash
# Check what's using the port
sudo netstat -tulpn | grep :3000

# Kill the process or change the port in docker-compose.yml
```

#### 2. Permission Denied

```bash
# Fix Docker permissions
sudo usermod -aG docker $USER
newgrp docker
```

#### 3. Database Issues

```bash
# Reset database
docker-compose down
rm -f data/agents.db
docker-compose up -d
```

#### 4. Memory Issues

```bash
# Check memory usage
docker stats

# Increase Docker memory limit in Docker Desktop settings
```

#### 5. Network Issues

```bash
# Check network connectivity
docker-compose exec backend ping redis
docker-compose exec frontend ping backend

# Restart Docker network
docker-compose down
docker network prune
docker-compose up -d
```

### Debug Mode

Enable debug logging:

```bash
# Set log level to DEBUG
echo "LOG_LEVEL=DEBUG" >> .env

# Restart services
docker-compose restart
```

### Performance Tuning

#### For High Load

1. **Increase resources**:
   ```yaml
   # In docker-compose.yml
   services:
     backend:
       deploy:
         resources:
           limits:
             memory: 2G
             cpus: '1.0'
   ```

2. **Enable caching**:
   ```bash
   # Redis is already configured for caching
   # Monitor Redis memory usage
   docker-compose exec redis redis-cli info memory
   ```

3. **Database optimization**:
   ```bash
   # For SQLite, ensure proper indexing
   # Consider PostgreSQL for production
   ```

## 🔐 Security Hardening

### Production Checklist

- [ ] Change default admin password
- [ ] Generate secure SECRET_KEY and JWT_SECRET
- [ ] Configure SSL/TLS certificates
- [ ] Set up firewall rules
- [ ] Enable rate limiting
- [ ] Configure backup strategy
- [ ] Set up monitoring and alerting
- [ ] Regular security updates
- [ ] Access logging
- [ ] Database encryption (if needed)

### SSL Configuration

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

## 📞 Support

If you encounter issues:

1. Check the logs: `docker-compose logs -f`
2. Verify configuration in `.env`
3. Check system resources: `docker stats`
4. Review this troubleshooting guide
5. Open an issue in the repository

## 🎯 Next Steps

After successful deployment:

1. **Access the platform**: http://51.81.187.172:3000
2. **Login**: admin/admin123
3. **Create your first agent**
4. **Configure API keys**
5. **Set up monitoring**
6. **Customize the platform**

Happy agent development! 🤖
