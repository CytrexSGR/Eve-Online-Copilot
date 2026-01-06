# EVE Intelligence Platform - Deployment Guide

## Prerequisites

- Ubuntu/Debian server with sudo access
- Domain: eve.infinimind-creations.com pointing to server IP
- Nginx installed
- Certbot installed

## Step 1: Install SSL Certificate

```bash
# Install certbot if not present
sudo apt update
sudo apt install certbot python3-certbot-nginx -y

# Get certificate
sudo certbot certonly --nginx -d eve.infinimind-creations.com

# Certificate will be at:
# /etc/letsencrypt/live/eve.infinimind-creations.com/fullchain.pem
# /etc/letsencrypt/live/eve.infinimind-creations.com/privkey.pem
```

## Step 2: Install Nginx Configuration

```bash
# Copy config
sudo cp /tmp/eve-intelligence.nginx.conf /etc/nginx/sites-available/eve-intelligence

# Enable site
sudo ln -s /etc/nginx/sites-available/eve-intelligence /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx
```

## Step 3: Build Frontend

```bash
cd /home/cytrex/eve_copilot/public-frontend
npm run build

# Output will be in: /home/cytrex/eve_copilot/public-frontend/dist
```

## Step 4: Create Systemd Service

```bash
sudo nano /etc/systemd/system/eve-intelligence-api.service
```

Paste content from systemd service file (see below).

## Step 5: Start Service

```bash
sudo systemctl daemon-reload
sudo systemctl enable eve-intelligence-api
sudo systemctl start eve-intelligence-api
sudo systemctl status eve-intelligence-api
```

## Step 6: Verify Deployment

```bash
# Check API
curl https://eve.infinimind-creations.com/api/health

# Check frontend
curl -I https://eve.infinimind-creations.com

# Check logs
sudo journalctl -u eve-intelligence-api -f
sudo tail -f /var/log/nginx/eve-intelligence-access.log
```

## Troubleshooting

### Service won't start
```bash
sudo journalctl -u eve-intelligence-api -n 50
```

### 502 Bad Gateway
Check if API is running:
```bash
sudo systemctl status eve-intelligence-api
curl http://localhost:8001/api/health
```

### 404 Not Found
Check Nginx config and frontend build:
```bash
ls -la /home/cytrex/eve_copilot/public-frontend/dist
sudo nginx -t
```
