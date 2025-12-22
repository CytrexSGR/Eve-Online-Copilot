# EVE Co-Pilot - Deployment Guide

**Version:** 2.0.0
**Date:** 2025-12-22

Complete deployment guide for the EVE Co-Pilot AI gaming assistant with Docker Compose.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Configuration](#configuration)
4. [Docker Deployment](#docker-deployment)
5. [Production Deployment](#production-deployment)
6. [Monitoring & Maintenance](#monitoring--maintenance)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required

- **Docker** 24.0+ with Docker Compose V2
- **Git** (to clone repository)
- **Anthropic API Key** (for Claude LLM)
- **OpenAI API Key** (for Whisper STT + TTS)
- **EVE SSO Application** (Client ID + Secret)

### System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 2 cores | 4+ cores |
| RAM | 4 GB | 8+ GB |
| Storage | 10 GB | 20+ GB |
| Network | 10 Mbps | 100+ Mbps |

---

## Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/CytrexSGR/Eve-Online-Copilot.git
cd Eve-Online-Copilot
```

### 2. Configure Environment

```bash
# Copy environment template
cp .env.docker.example .env

# Edit with your API keys and credentials
nano .env
```

**Required Configuration:**

```env
# Anthropic Claude API
ANTHROPIC_API_KEY=sk-ant-api03-...

# OpenAI API
OPENAI_API_KEY=sk-...

# EVE SSO
EVE_CLIENT_ID=your_client_id
EVE_CLIENT_SECRET=your_client_secret
```

### 3. Start Services

```bash
# Build and start all containers
docker compose up -d

# View logs
docker compose logs -f

# Check health status
docker compose ps
```

### 4. Access Application

- **Frontend:** http://localhost:5173
- **Backend API:** http://localhost:8000/docs
- **AI Copilot:** http://localhost:8001/docs

---

## Configuration

### Environment Variables

#### Database

```env
POSTGRES_DB=eve_sde              # Database name
POSTGRES_USER=eve                # Database user
POSTGRES_PASSWORD=EvE_Pr0ject_2024  # Database password
DB_PORT=5432                     # PostgreSQL port
```

#### Backend API (Port 8000)

```env
BACKEND_PORT=8000                # API port

# EVE SSO
EVE_CLIENT_ID=b4dbf38efae04055bc7037a63bcfd33b
EVE_CLIENT_SECRET=your_secret
EVE_CALLBACK_URL=http://localhost:8000/api/auth/callback

# Optional
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
RELOAD=false                     # Hot reload (dev only)
```

#### AI Copilot (Port 8001)

```env
COPILOT_PORT=8001

# Anthropic
ANTHROPIC_API_KEY=sk-ant-api03-...
ANTHROPIC_MODEL=claude-sonnet-4-20250514

# OpenAI
OPENAI_API_KEY=sk-...
WHISPER_MODEL=whisper-1          # Speech-to-Text
TTS_MODEL=tts-1                  # Text-to-Speech
TTS_VOICE=nova                   # Voice: alloy, echo, fable, onyx, nova, shimmer

# LLM Tuning
MAX_TOKENS=4096                  # Max response length
TEMPERATURE=1.0                  # Creativity (0.0-2.0)
MAX_TOOL_ITERATIONS=5            # Max tool call loops
MAX_CONVERSATION_HISTORY=50      # Message history limit
```

#### Frontend (Port 5173)

```env
FRONTEND_PORT=5173               # Frontend port
VITE_API_URL=http://localhost:8001      # API base URL
VITE_WS_URL=ws://localhost:8001         # WebSocket URL
```

---

## Docker Deployment

### Architecture

```
┌─────────────────┐
│ Frontend        │  Port 5173 (nginx)
│ (React + Vite)  │
└────────┬────────┘
         │ WebSocket + REST
         ↓
┌─────────────────┐
│ AI Copilot      │  Port 8001
│ (Claude + MCP)  │
└────────┬────────┘
         │ REST
         ↓
┌─────────────────┐
│ Backend API     │  Port 8000
│ (FastAPI)       │
└────────┬────────┘
         │ SQL
         ↓
┌─────────────────┐
│ PostgreSQL      │  Port 5432
│ (EVE SDE)       │
└─────────────────┘
```

### Container Details

#### 1. Database (`eve_copilot_db`)

- **Image:** postgres:16-alpine
- **Volume:** `postgres_data` (persistent)
- **Health Check:** `pg_isready` every 10s
- **Restart:** unless-stopped

**Features:**
- Auto-initialization from `/migrations/*.sql`
- Data persistence across restarts
- Optimized Alpine Linux base

#### 2. Backend (`eve_copilot_backend`)

- **Build:** Dockerfile.backend
- **Depends:** database (healthy)
- **Volumes:**
  - `./tokens.json` (EVE SSO tokens)
  - `./logs` (application logs)
- **Health Check:** `curl /docs` every 30s

**Endpoints:**
- 118 REST API endpoints
- EVE SSO authentication
- Market data, production, war room

#### 3. AI Copilot (`eve_copilot_ai`)

- **Build:** Dockerfile.copilot
- **Depends:** backend (healthy)
- **Volumes:**
  - `./copilot_logs` (AI logs)
- **Health Check:** `curl /health` every 30s

**Features:**
- Claude Sonnet 4.5 LLM
- 115 MCP tools
- WebSocket server
- Audio transcription + synthesis

#### 4. Frontend (`eve_copilot_frontend`)

- **Build:** frontend_chat/Dockerfile (multi-stage)
- **Depends:** copilot
- **Nginx:** Production-optimized server
- **Health Check:** `curl /health` every 30s

**Features:**
- React 18 + TypeScript
- EVE Online dark theme
- Voice input (browser API)
- Real-time chat

### Docker Compose Commands

```bash
# Start all services
docker compose up -d

# Start specific service
docker compose up -d frontend

# View logs (all services)
docker compose logs -f

# View logs (specific service)
docker compose logs -f copilot

# Restart service
docker compose restart backend

# Stop all services
docker compose down

# Stop and remove volumes
docker compose down -v

# Rebuild and restart
docker compose up -d --build

# Check health status
docker compose ps

# Execute command in container
docker compose exec backend /bin/bash
docker compose exec database psql -U eve -d eve_sde
```

### Volume Management

```bash
# List volumes
docker volume ls

# Inspect volume
docker volume inspect eve_copilot_postgres_data

# Backup database
docker compose exec database pg_dump -U eve eve_sde > backup.sql

# Restore database
cat backup.sql | docker compose exec -T database psql -U eve -d eve_sde

# Remove volumes (WARNING: data loss)
docker compose down -v
```

---

## Production Deployment

### 1. HTTPS Setup

#### Option A: Nginx Reverse Proxy

```nginx
# /etc/nginx/sites-available/eve-copilot

server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    # Frontend
    location / {
        proxy_pass http://localhost:5173;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # WebSocket
    location /copilot/ws/ {
        proxy_pass http://localhost:8001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # Backend API
    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
    }
}
```

#### Option B: Traefik (Docker)

```yaml
# Add to docker-compose.yml

services:
  traefik:
    image: traefik:v2.10
    command:
      - "--providers.docker=true"
      - "--entrypoints.web.address=:80"
      - "--entrypoints.websecure.address=:443"
      - "--certificatesresolvers.letsencrypt.acme.email=you@example.com"
      - "--certificatesresolvers.letsencrypt.acme.storage=/letsencrypt/acme.json"
      - "--certificatesresolvers.letsencrypt.acme.httpchallenge.entrypoint=web"
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - traefik_letsencrypt:/letsencrypt

  frontend:
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.frontend.rule=Host(`yourdomain.com`)"
      - "traefik.http.routers.frontend.entrypoints=websecure"
      - "traefik.http.routers.frontend.tls.certresolver=letsencrypt"
```

### 2. Update Environment for Production

```env
# .env (production)

# Public URLs
EVE_CALLBACK_URL=https://yourdomain.com/api/auth/callback
VITE_API_URL=https://yourdomain.com:8001
VITE_WS_URL=wss://yourdomain.com:8001

# Security
RELOAD=false

# Rate limiting (optional)
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=60
```

### 3. Security Hardening

#### Database

```bash
# Change default password
POSTGRES_PASSWORD=$(openssl rand -base64 32)

# Restrict network access
# Remove ports: section in docker-compose.yml for database
# (only allow internal Docker network)
```

#### API Keys

```bash
# Use secrets management
docker secret create anthropic_key anthropic.key
docker secret create openai_key openai.key

# Update docker-compose.yml
services:
  copilot:
    secrets:
      - anthropic_key
      - openai_key
```

#### Firewall

```bash
# Allow only necessary ports
ufw allow 80/tcp
ufw allow 443/tcp
ufw deny 5432/tcp  # Block external DB access
ufw enable
```

### 4. Performance Optimization

#### Docker Compose Tuning

```yaml
# docker-compose.yml

services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G

  copilot:
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 4G
        reservations:
          cpus: '2'
          memory: 2G
```

#### PostgreSQL Tuning

```bash
# Add to docker-compose.yml database service
command:
  - postgres
  - -c
  - shared_buffers=256MB
  - -c
  - max_connections=100
  - -c
  - work_mem=16MB
```

---

## Monitoring & Maintenance

### Health Monitoring

```bash
# Check all services
docker compose ps

# Expected output:
# NAME                    STATUS              PORTS
# eve_copilot_db          Up (healthy)        5432/tcp
# eve_copilot_backend     Up (healthy)        8000/tcp
# eve_copilot_ai          Up (healthy)        8001/tcp
# eve_copilot_frontend    Up (healthy)        80/tcp
```

### Log Management

```bash
# View logs
docker compose logs -f --tail=100

# Export logs
docker compose logs > logs-$(date +%Y%m%d).txt

# Log rotation (optional)
# Add to docker-compose.yml
services:
  backend:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

### Database Backups

```bash
# Automated backup script
#!/bin/bash
# backup.sh

BACKUP_DIR="/backups/eve_copilot"
mkdir -p "$BACKUP_DIR"

docker compose exec -T database pg_dump -U eve eve_sde | \
  gzip > "$BACKUP_DIR/backup-$(date +%Y%m%d-%H%M%S).sql.gz"

# Keep only last 7 days
find "$BACKUP_DIR" -name "backup-*.sql.gz" -mtime +7 -delete

# Add to crontab
# 0 2 * * * /path/to/backup.sh
```

### Updates

```bash
# Pull latest code
git pull origin main

# Rebuild and restart
docker compose down
docker compose up -d --build

# Or for zero-downtime:
docker compose up -d --build --no-deps frontend
docker compose up -d --build --no-deps backend
docker compose up -d --build --no-deps copilot
```

---

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker compose logs [service_name]

# Check Docker resources
docker system df
docker system prune

# Rebuild from scratch
docker compose down -v
docker compose build --no-cache
docker compose up -d
```

### Database Connection Failed

```bash
# Check database is running
docker compose ps database

# Test connection
docker compose exec database psql -U eve -d eve_sde -c "SELECT 1;"

# Check credentials
docker compose exec backend env | grep DATABASE

# Reset database (WARNING: data loss)
docker compose down -v
docker compose up -d database
```

### WebSocket Connection Failed

```bash
# Check copilot service
docker compose logs copilot

# Test WebSocket endpoint
curl -i -N \
  -H "Connection: Upgrade" \
  -H "Upgrade: websocket" \
  http://localhost:8001/copilot/ws/test-session

# Check firewall
ufw status
```

### API Key Issues

```bash
# Verify environment variables
docker compose exec copilot env | grep API_KEY

# Test Anthropic API
docker compose exec copilot python3 -c "
import anthropic
client = anthropic.Anthropic()
print('API key valid')
"

# Test OpenAI API
docker compose exec copilot python3 -c "
import openai
client = openai.OpenAI()
print('API key valid')
"
```

### Performance Issues

```bash
# Check resource usage
docker stats

# Check container health
docker compose ps

# Increase resources in docker-compose.yml
# See "Performance Optimization" section above

# Check logs for errors
docker compose logs -f | grep ERROR
```

### Frontend Build Fails

```bash
# Check build logs
docker compose logs frontend

# Rebuild frontend only
docker compose up -d --build frontend

# Test locally first
cd frontend_chat
npm install
npm run build
```

---

## Appendix

### Useful Commands

```bash
# Quick restart all
docker compose restart

# Force recreate containers
docker compose up -d --force-recreate

# View resource usage
docker compose top

# Export environment
docker compose config

# Validate compose file
docker compose config --quiet

# Remove all stopped containers
docker container prune

# Clean up everything
docker system prune -a --volumes
```

### Port Reference

| Service | Port | Protocol | Purpose |
|---------|------|----------|---------|
| Database | 5432 | TCP | PostgreSQL |
| Backend | 8000 | HTTP | REST API |
| Copilot | 8001 | HTTP/WS | AI + WebSocket |
| Frontend | 5173 | HTTP | Web UI |

### API Endpoints

- **Backend:** http://localhost:8000/docs
- **Copilot:** http://localhost:8001/docs
- **Health:** http://localhost:8001/health
- **WebSocket:** ws://localhost:8001/copilot/ws/{session_id}

---

**For more information:**
- [User Guide](USER_GUIDE.md)
- [Architecture](../ARCHITECTURE.md)
- [Development Guide](../CLAUDE.md)

---

**Last Updated:** 2025-12-22
**Maintainer:** Cytrex
