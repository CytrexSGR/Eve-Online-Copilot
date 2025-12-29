#!/bin/bash
# Test complete agent flow

echo "=== Creating Session ==="
SESSION_RESPONSE=$(curl -s -X POST http://localhost:8001/agent/session \
  -H "Content-Type: application/json" \
  -d '{"character_id": 526379435}')

echo "$SESSION_RESPONSE"

SESSION_ID=$(echo "$SESSION_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['session_id'])")
echo "Session ID: $SESSION_ID"

echo ""
echo "=== Sending Chat Message ==="
curl -N -X POST http://localhost:8001/agent/chat/stream \
  -H "Content-Type: application/json" \
  -d "{\"session_id\": \"$SESSION_ID\", \"character_id\": 526379435, \"message\": \"What is the current sell price of Tritanium in Jita?\"}"

echo ""
echo ""
echo "=== Done ==="
