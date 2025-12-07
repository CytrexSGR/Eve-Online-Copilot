#!/bin/bash
# EVE Co-Pilot - Start all services
# Usage: ./start_services.sh

cd /home/cytrex/eve_copilot

echo "=== EVE Co-Pilot Startup ==="
echo ""

# Kill existing processes
echo "Stopping existing services..."
pkill -f "uvicorn main:app" 2>/dev/null
pkill -f "node.*vite" 2>/dev/null
sleep 2

# Start Backend
echo "Starting Backend (Port 8000)..."
nohup /home/cytrex/.local/bin/uvicorn main:app --host 0.0.0.0 --port 8000 > /tmp/uvicorn.log 2>&1 &
BACKEND_PID=$!
echo "  PID: $BACKEND_PID"

# Wait for backend to start
sleep 3

# Start Frontend
echo "Starting Frontend (Port 3000)..."
cd /home/cytrex/eve_copilot/frontend
nohup npm run dev > /tmp/frontend.log 2>&1 &
FRONTEND_PID=$!
echo "  PID: $FRONTEND_PID"

# Wait and verify
sleep 5

echo ""
echo "=== Service Status ==="

if curl -s http://localhost:8000/api/regions > /dev/null 2>&1; then
    echo "Backend:  RUNNING (http://localhost:8000)"
else
    echo "Backend:  FAILED - check /tmp/uvicorn.log"
fi

if curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo "Frontend: RUNNING (http://localhost:3000)"
else
    echo "Frontend: FAILED - check /tmp/frontend.log"
fi

echo ""
echo "=== Cron Jobs ==="
crontab -l 2>/dev/null | grep -v "^#" | grep -v "^$"

echo ""
echo "=== Logs ==="
echo "Backend:  tail -f /tmp/uvicorn.log"
echo "Frontend: tail -f /tmp/frontend.log"
echo "Prices:   tail -f /home/cytrex/eve_copilot/logs/regional_prices.log"
