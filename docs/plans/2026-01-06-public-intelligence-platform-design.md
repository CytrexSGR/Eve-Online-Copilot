# EVE Intelligence Platform - Public Web Service Design

**Date:** 2026-01-06
**Domain:** eve.infinimind-creations.com
**Purpose:** Public combat intelligence reports with Google Ads monetization

---

## Overview

A public-facing web platform providing real-time EVE Online combat intelligence reports. Separate from the private EVE Co-Pilot system, designed for maximum reach and monetization through Google AdSense.

---

## Architecture

### High-Level Components

```
Browser → Nginx (HTTPS) → React SPA (Static)
                        ↓
                   FastAPI :8001 → Redis (Cached Reports)
```

**Key Decisions:**
- **Separate FastAPI App** on port 8001 (isolation from private API on 8000)
- **React Frontend** with Vite (consistent with existing stack)
- **Shared Redis** for cached reports (read-only access)
- **All 4 Reports Public** for maximum traffic
- **Cached API Responses** with 60s frontend polling

---

## Backend API (Port 8001)

### Project Structure

```
eve_copilot/
├── public_api/
│   ├── main.py              # FastAPI application
│   ├── routers/
│   │   └── reports.py       # Report endpoints
│   ├── middleware/
│   │   ├── rate_limit.py    # Rate limiting (100 req/min)
│   │   └── security.py      # Security headers
│   └── requirements.txt     # Dependencies
```

### API Endpoints

| Endpoint | Method | Description | Cache |
|----------|--------|-------------|-------|
| `/api/reports/battle-24h` | GET | 24h Battle Report | 10min |
| `/api/reports/war-profiteering` | GET | War Profiteering Digest | 1h |
| `/api/reports/alliance-wars` | GET | Alliance War Tracker | 30min |
| `/api/reports/trade-routes` | GET | Trade Route Danger Map | 1h |
| `/api/health` | GET | Health check | - |

### Security Measures

1. **Rate Limiting:** 100 requests/minute per IP (SlowAPI)
2. **Security Headers:** HSTS, X-Frame-Options, CSP, X-Content-Type-Options
3. **CORS:** Only `eve.infinimind-creations.com`
4. **Read-Only:** No write operations, no database access
5. **IP Blocking:** Fail2ban integration for abuse

### Data Access

- Uses `ZKillboardReportsService` (existing)
- Shared Redis client (read-only)
- No PostgreSQL connection (security)
- All data from Redis cache

---

## Frontend (React + Vite)

### Project Structure

```
public-frontend/
├── src/
│   ├── components/
│   │   ├── ReportCard.tsx        # Reusable report container
│   │   ├── RefreshIndicator.tsx  # "Updated 2min ago"
│   │   ├── AdSlot.tsx            # Google Ads wrapper
│   │   └── Layout.tsx            # Header/Footer
│   ├── pages/
│   │   ├── Home.tsx              # Dashboard (all 4 reports)
│   │   ├── BattleReport.tsx      # Detail view
│   │   ├── WarProfiteering.tsx   # Detail view
│   │   ├── AllianceWars.tsx      # Detail view
│   │   └── TradeRoutes.tsx       # Detail view
│   ├── services/
│   │   └── api.ts                # API client with polling
│   ├── App.tsx
│   └── main.tsx
├── public/
│   ├── ads.txt                   # Google AdSense verification
│   └── robots.txt
├── index.html
├── vite.config.ts
└── package.json
```

### UI/UX Design

**Theme:**
- Dark mode (EVE Online aesthetic)
- Space-themed color palette
- Responsive design (mobile-first)

**Features:**
- Auto-refresh every 60 seconds
- Loading skeletons
- Error handling with retry
- "Last updated" timestamps
- Toast notifications for updates

**Performance:**
- Code splitting per page
- Lazy loading for detail views
- Gzip compression (Nginx)
- Tree shaking (Vite)

---

## Google Ads Integration

### AdSense Setup

1. **Register Domain:** eve.infinimind-creations.com in AdSense
2. **Verify Ownership:** ads.txt file in `/public`
3. **Create Ad Units:** 4 placements

### Ad Placements

| Location | Format | Size | Priority |
|----------|--------|------|----------|
| Header | Leaderboard | 728x90 | High |
| Sidebar | Rectangle | 300x250 | High |
| Between Reports | Medium Rectangle | 300x250 | Medium |
| Footer | Leaderboard | 728x90 | Low |
| Mobile | Responsive Banner | Auto | High |

### GDPR Compliance

- Cookie consent banner (cookieconsent.js)
- Privacy policy page
- Cookie policy page
- Opt-out mechanism

### Implementation

```tsx
// src/components/AdSlot.tsx
import { useEffect } from 'react';

export function AdSlot({
  adSlot,
  format = 'auto',
  style = { display: 'block' }
}) {
  useEffect(() => {
    try {
      (window.adsbygoogle = window.adsbygoogle || []).push({});
    } catch (e) {
      console.error('AdSense error:', e);
    }
  }, []);

  return (
    <ins
      className="adsbygoogle"
      style={style}
      data-ad-client="ca-pub-XXXXXXXX"
      data-ad-slot={adSlot}
      data-ad-format={format}
    />
  );
}
```

---

## Nginx Configuration

### Virtual Host

**File:** `/etc/nginx/sites-available/eve-intelligence`

```nginx
# Rate limiting zone
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=100r/m;

# HTTPS Server
server {
    listen 443 ssl http2;
    server_name eve.infinimind-creations.com;

    # SSL Certificates (Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/eve.infinimind-creations.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/eve.infinimind-creations.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Static Frontend
    location / {
        root /home/cytrex/eve_copilot/public-frontend/dist;
        try_files $uri $uri/ /index.html;

        # Caching
        expires 1h;
        add_header Cache-Control "public, immutable";

        # Compression
        gzip on;
        gzip_types text/css application/javascript application/json;
        gzip_min_length 1000;
    }

    # API Proxy
    location /api/ {
        proxy_pass http://localhost:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Rate Limiting
        limit_req zone=api_limit burst=20 nodelay;
        limit_req_status 429;

        # Timeouts
        proxy_connect_timeout 5s;
        proxy_send_timeout 10s;
        proxy_read_timeout 10s;
    }

    # Health Check (no rate limit)
    location = /api/health {
        proxy_pass http://localhost:8001;
        access_log off;
    }

    # Access Logs
    access_log /var/log/nginx/eve-intelligence-access.log;
    error_log /var/log/nginx/eve-intelligence-error.log;
}

# HTTP → HTTPS Redirect
server {
    listen 80;
    server_name eve.infinimind-creations.com;
    return 301 https://$server_name$request_uri;
}
```

### Let's Encrypt Setup

```bash
sudo certbot --nginx -d eve.infinimind-creations.com
sudo systemctl reload nginx
```

---

## Deployment

### Systemd Service

**File:** `/etc/systemd/system/eve-intelligence-api.service`

```ini
[Unit]
Description=EVE Intelligence Public API
After=network.target redis.service postgresql.service
Requires=redis.service

[Service]
Type=simple
User=cytrex
Group=cytrex
WorkingDirectory=/home/cytrex/eve_copilot
Environment="PATH=/home/cytrex/.local/bin:/usr/local/bin:/usr/bin:/bin"

ExecStart=/home/cytrex/.local/bin/uvicorn public_api.main:app \
    --host 0.0.0.0 \
    --port 8001 \
    --workers 2 \
    --log-level info

Restart=always
RestartSec=10

# Security
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

### Service Management

```bash
# Install and start
sudo systemctl daemon-reload
sudo systemctl enable eve-intelligence-api
sudo systemctl start eve-intelligence-api

# Check status
sudo systemctl status eve-intelligence-api

# View logs
sudo journalctl -u eve-intelligence-api -f
```

---

## Monitoring & Analytics

### Application Monitoring

1. **Health Endpoint:** `/api/health`
   - Redis connectivity check
   - Response time tracking
   - 200 OK if healthy

2. **Logging:**
   - Application logs: `/var/log/eve-intelligence/app.log`
   - Error logs: `/var/log/eve-intelligence/error.log`
   - Nginx logs: `/var/log/nginx/eve-intelligence-*.log`

3. **Metrics:**
   - Request count per endpoint
   - Response times (p50, p95, p99)
   - Error rates
   - Cache hit rates

### External Monitoring

1. **UptimeRobot:** Free uptime monitoring
   - Check every 5 minutes
   - Alert on downtime
   - Status page

2. **Google Analytics 4:**
   - Page views
   - User engagement
   - Traffic sources
   - Ad performance

3. **Google Search Console:**
   - SEO monitoring
   - Search performance
   - Index status

---

## Security Considerations

### API Security

- **No Authentication:** Public API, read-only
- **Rate Limiting:** 100 requests/minute per IP
- **CORS:** Strict origin policy
- **Input Validation:** All query parameters validated
- **No User Data:** Zero personal data collection

### Infrastructure Security

- **HTTPS Only:** Forced redirect from HTTP
- **TLS 1.2+:** Strong cipher suites
- **Security Headers:** HSTS, CSP, X-Frame-Options
- **Fail2ban:** IP blocking for abuse
- **Firewall:** UFW with port restrictions

### GDPR Compliance

- **Cookie Banner:** Required for Google Ads
- **Privacy Policy:** Data collection disclosure
- **No User Accounts:** No personal data storage
- **Analytics Opt-Out:** Respect DNT headers

---

## Performance Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| Page Load (FCP) | < 1.5s | Lighthouse |
| API Response (p95) | < 200ms | Application logs |
| Uptime | > 99.5% | UptimeRobot |
| Cache Hit Rate | > 95% | Redis INFO |
| Mobile Score | > 90 | PageSpeed Insights |

---

## Future Enhancements

### Phase 2 (Optional)

1. **Historical Data:**
   - Archive reports to PostgreSQL
   - Charts/graphs with Chart.js
   - Trend analysis

2. **Premium Features:**
   - API Keys for developers
   - Custom alerts via email
   - Ad-free subscription ($5/month)

3. **SEO Optimization:**
   - Server-side rendering (Next.js migration)
   - Sitemap.xml
   - Structured data (Schema.org)

4. **CDN Integration:**
   - Cloudflare for static assets
   - DDoS protection
   - Global edge caching

---

## Deployment Checklist

### Before Launch

- [ ] Backend API implemented and tested
- [ ] Frontend built and tested
- [ ] Nginx configured
- [ ] SSL certificate installed
- [ ] Systemd service configured
- [ ] Google AdSense approved
- [ ] Privacy policy published
- [ ] Cookie consent implemented
- [ ] Analytics configured
- [ ] Monitoring setup
- [ ] Rate limiting tested
- [ ] Mobile responsiveness verified

### Launch Day

- [ ] Deploy backend to production
- [ ] Deploy frontend to production
- [ ] Enable systemd service
- [ ] Verify HTTPS works
- [ ] Test all 4 reports load
- [ ] Verify ads display
- [ ] Check Google Analytics
- [ ] Monitor error logs
- [ ] Announce to EVE community

### Post-Launch

- [ ] Monitor uptime (first 24h)
- [ ] Check ad revenue
- [ ] Gather user feedback
- [ ] Optimize performance
- [ ] SEO improvements

---

## Estimated Timeline

| Phase | Duration | Tasks |
|-------|----------|-------|
| Backend API | 2-3 hours | FastAPI app, routes, security |
| Frontend | 4-6 hours | React app, components, styling |
| Nginx & SSL | 1 hour | Configuration, certbot |
| Google Ads | 1 hour | AdSense setup, integration |
| Testing | 2 hours | End-to-end, mobile, performance |
| Deployment | 1 hour | Systemd, startup, verification |
| **Total** | **11-14 hours** | Full implementation |

---

## Success Metrics

**Month 1 Goals:**
- 1,000+ unique visitors
- 10,000+ page views
- $10+ ad revenue
- 99.5%+ uptime
- < 2s average page load

**Month 3 Goals:**
- 5,000+ unique visitors
- 50,000+ page views
- $100+ ad revenue
- Featured on EVE news sites
- API access requests

---

**End of Design Document**
