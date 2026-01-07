# Nginx Configuration

This directory contains the nginx reverse proxy configuration for the EVE Intelligence Public Dashboard.

## Configuration File

**`eve-intelligence.conf`** - Complete nginx configuration with:
- HTTP to HTTPS redirect
- SSL/TLS configuration (Let's Encrypt)
- Reverse proxy for public-frontend (Port 5173)
- Reverse proxy for Main API `/api/war/*` (Port 8000)
- Reverse proxy for Public API `/api/*` (Port 8001)
- WebSocket support for Agent Runtime
- Security headers (HSTS, X-Frame-Options, etc.)
- HTTP/2 support

## Domain

**Production:** https://eve.infinimind-creations.com

## Installation

1. **Install the configuration:**
   ```bash
   sudo cp eve-intelligence.conf /etc/nginx/sites-available/eve-intelligence
   sudo ln -sf /etc/nginx/sites-available/eve-intelligence /etc/nginx/sites-enabled/
   ```

2. **Test the configuration:**
   ```bash
   sudo nginx -t
   ```

3. **Reload nginx:**
   ```bash
   sudo systemctl reload nginx
   ```

## SSL Certificate

SSL certificate is managed by **Let's Encrypt** (Certbot).

### Initial Setup

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Request certificate
sudo certbot certonly --webroot -w /var/www/html \
  -d eve.infinimind-creations.com \
  --email your-email@example.com \
  --agree-tos --non-interactive
```

### Auto-Renewal

Certbot automatically sets up a systemd timer for renewal:

```bash
# Check renewal timer
sudo systemctl status certbot.timer

# Test renewal (dry-run)
sudo certbot renew --dry-run

# Manual renewal
sudo certbot renew
```

Certificates expire **90 days** after issuance and are automatically renewed **30 days** before expiration.

## Port Forwarding

Ensure your router/firewall forwards these ports:

| Port | Protocol | Purpose |
|------|----------|---------|
| 80   | TCP      | HTTP (Let's Encrypt verification + redirect) |
| 443  | TCP      | HTTPS (encrypted traffic) |

## Backend Services

The nginx configuration expects these services to be running locally:

| Service | Port | Purpose |
|---------|------|---------|
| public-frontend | 5173 | React frontend (Vite dev server) |
| Public API | 8001 | FastAPI public intelligence API |
| Main API | 8000 | FastAPI main API (internal tools) |

## Security Features

- **TLS 1.2/1.3 only** - Modern encryption protocols
- **HSTS** - Force HTTPS for 1 year (includeSubDomains)
- **X-Frame-Options: SAMEORIGIN** - Prevent clickjacking
- **X-Content-Type-Options: nosniff** - Prevent MIME sniffing
- **X-XSS-Protection** - Enable browser XSS filter
- **HTTP/2** - Faster page loads

## Troubleshooting

### Check nginx status:
```bash
sudo systemctl status nginx
```

### View nginx logs:
```bash
# Error log
sudo tail -f /var/log/nginx/error.log

# Access log
sudo tail -f /var/log/nginx/access.log
```

### Test SSL certificate:
```bash
# Check certificate expiry
sudo certbot certificates

# SSL Labs test
https://www.ssllabs.com/ssltest/analyze.html?d=eve.infinimind-creations.com
```

### Common Issues

**502 Bad Gateway:**
- Check if backend services are running (Port 5173, 8000, 8001)
- Check firewall rules: `sudo iptables -L -n`

**SSL Certificate Renewal Failed:**
- Ensure port 80 is accessible from the internet
- Check Let's Encrypt logs: `/var/log/letsencrypt/letsencrypt.log`

## Production Deployment

For production deployment with systemd services, see [DEPLOYMENT.md](../docs/DEPLOYMENT.md).
