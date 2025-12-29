#!/bin/bash
# Test SSE streaming endpoint

# First create a session
SESSION_RESPONSE=$(curl -X POST http://localhost:8000/agent/session \
  -H "Content-Type: application/json" \
  -d '{"character_id": 526379435, "autonomy_level": "RECOMMENDATIONS"}')

SESSION_ID=$(echo $SESSION_RESPONSE | jq -r '.session_id')

echo "Created session: $SESSION_ID"

# Stream chat response
curl -N -X POST http://localhost:8000/agent/chat/stream \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"Hello!\", \"session_id\": \"$SESSION_ID\", \"character_id\": 526379435}"
