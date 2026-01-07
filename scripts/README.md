# EVE Intelligence Scripts

Utility scripts for monitoring and analyzing the EVE Intelligence platform.

## Traffic Analytics

### analyze_traffic.py

Analyzes nginx access logs for **eve.infinimind-creations.com** to track visitor statistics.

**Features:**
- Unique visitors count
- Most visited pages
- Top visitor IPs
- Browser statistics
- HTTP status codes
- Traffic by hour (UTC)
- External referrers

**Usage:**

```bash
# Analyze last 7 days (default)
sudo python3 scripts/analyze_traffic.py

# Analyze last 30 days
sudo python3 scripts/analyze_traffic.py --days 30

# Analyze last 1 day
sudo python3 scripts/analyze_traffic.py --days 1

# Custom log file
sudo python3 scripts/analyze_traffic.py --log-file /path/to/access.log
```

**Requirements:**
- Python 3.8+
- Sudo access (to read nginx logs)
- Nginx access logs at `/var/log/nginx/access.log`

**Output Example:**

```
======================================================================
EVE INTELLIGENCE TRAFFIC REPORT
======================================================================

📈 OVERVIEW
----------------------------------------------------------------------
Total Requests:        262
Unique Visitors:       5

📄 TOP PAGES
----------------------------------------------------------------------
    94x  /api/war/live-hotspots
    17x  /api/war/pilot-intelligence
    17x  /api/reports/alliance-wars
    ...

👥 TOP VISITORS
----------------------------------------------------------------------
   200x  77.24.99.81
    30x  152.39.196.240
    ...

🌐 BROWSERS
----------------------------------------------------------------------
   200x  Edge            ( 76.3%)
    58x  Safari          ( 22.1%)
    ...

📊 HTTP STATUS CODES
----------------------------------------------------------------------
   258x  200 OK
     4x  304 Not Modified

⏰ TRAFFIC BY HOUR (UTC)
----------------------------------------------------------------------
 7:00    220x  ████████████████████████████████████████
 8:00     42x  ███████
```

### Data Tracked

| Metric | Description |
|--------|-------------|
| **Total Requests** | All HTTP requests to eve.infinimind-creations.com |
| **Unique Visitors** | Count of unique IP addresses |
| **Top Pages** | Most frequently accessed URLs |
| **Top Visitors** | IPs with most requests |
| **Browsers** | Browser/client statistics from User-Agent |
| **Status Codes** | HTTP response code distribution |
| **Traffic by Hour** | Request volume per hour (UTC timezone) |
| **Referrers** | External sites linking to the platform |

### Privacy & GDPR

- **IP addresses** are logged in nginx access logs
- Logs are rotated daily (kept for 7 days by default)
- No cookies or client-side tracking
- No personal data beyond IP addresses
- Compliant with basic analytics requirements

To increase log retention:

```bash
# Edit logrotate config
sudo nano /etc/logrotate.d/nginx

# Change 'rotate 7' to 'rotate 30' for 30 days retention
```

### Automated Reports

Add to cron for daily reports:

```bash
# Daily traffic report at 00:00
0 0 * * * /usr/bin/python3 /home/cytrex/eve_copilot/scripts/analyze_traffic.py --days 1 > /home/cytrex/eve_copilot/logs/daily_traffic_$(date +\%Y\%m\%d).txt
```

## Advanced Analytics (Optional)

For real-time dashboards, consider installing **GoAccess**:

```bash
# Install GoAccess
sudo apt install goaccess

# Generate real-time HTML report
sudo goaccess /var/log/nginx/access.log \
  --log-format=COMBINED \
  --output=/var/www/html/stats.html \
  --real-time-html

# Access at: http://your-server/stats.html
```

**GoAccess Features:**
- Real-time updates
- Beautiful HTML dashboard
- Geolocation (with GeoIP)
- No database required
- Privacy-friendly (self-hosted)
