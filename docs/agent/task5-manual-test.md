# Task 5: Agent Dashboard - Manual Testing Checklist

## Prerequisites

1. Backend server running: `uvicorn copilot_server.main:app --reload`
2. Frontend dev server running: `cd frontend && npm run dev`
3. Navigate to: `http://localhost:5173/agent`

## Test Cases

### 1. Session Creation
- [ ] Navigate to `/agent`
- [ ] Verify "Create Agent Session" form is displayed
- [ ] Verify autonomy level dropdown has 4 options:
  - Read Only
  - Recommendations (default)
  - Assisted
  - Supervised
- [ ] Select an autonomy level
- [ ] Click "Create Session" button
- [ ] Verify button shows "Creating Session..." while loading
- [ ] Verify session is created (session ID appears)
- [ ] Verify WebSocket connects (green dot appears)

### 2. Connection Status
- [ ] Verify connection status indicator shows green dot with "Connected" text
- [ ] Verify session ID is displayed
- [ ] Verify autonomy level is displayed

### 3. WebSocket Connection
- [ ] Open browser DevTools > Network > WS tab
- [ ] Verify WebSocket connection to `ws://localhost:8000/agent/stream/{session_id}`
- [ ] Verify ping/pong messages every 30 seconds

### 4. Event Stream
- [ ] Verify "Event Stream" section is visible
- [ ] Initially shows "No events yet. Waiting for agent activity..."
- [ ] Send a chat message via backend (if chat endpoint is ready)
- [ ] Verify events appear in the stream
- [ ] Verify events auto-scroll to bottom
- [ ] Verify "Clear Events" button works

### 5. Plan Approval (when PLAN_PROPOSED event received)
- [ ] Wait for PLAN_PROPOSED event (or trigger manually via backend)
- [ ] Verify PlanApprovalCard appears with yellow background
- [ ] Verify plan details are displayed:
  - Purpose
  - Tool count
  - Risk level (with correct color: green=READ_ONLY, yellow=WRITE_LOW_RISK, red=others)
  - Step-by-step list with tool names
- [ ] Click "Approve & Execute" button
- [ ] Verify button shows "Approving..." while loading
- [ ] Verify API call is made to `/agent/execute`
- [ ] Verify plan card disappears after approval
- [ ] Verify PLAN_APPROVED event appears in stream

### 6. Plan Rejection
- [ ] Wait for another PLAN_PROPOSED event
- [ ] Click "Reject" button
- [ ] Verify rejection reason textarea appears
- [ ] Type a rejection reason (e.g., "Too risky")
- [ ] Click "Confirm Rejection"
- [ ] Verify button shows "Rejecting..." while loading
- [ ] Verify API call is made to `/agent/reject`
- [ ] Verify plan card disappears after rejection
- [ ] Verify PLAN_REJECTED event appears in stream

### 7. Cancel Rejection
- [ ] Wait for another PLAN_PROPOSED event
- [ ] Click "Reject" button
- [ ] Type a rejection reason
- [ ] Click "Cancel" button
- [ ] Verify rejection textarea disappears
- [ ] Verify approval/reject buttons reappear

### 8. End Session
- [ ] Click "End Session" button
- [ ] Verify session is deleted
- [ ] Verify WebSocket disconnects (red dot appears)
- [ ] Verify "Create Agent Session" form reappears
- [ ] Verify event stream is cleared

### 9. Error Handling
- [ ] Stop backend server
- [ ] Try to create a session
- [ ] Verify error message appears
- [ ] Restart backend server
- [ ] With a session active, stop backend
- [ ] Verify connection status shows "Disconnected" (red dot)
- [ ] Verify WebSocket auto-reconnects when backend restarts

### 10. Navigation
- [ ] Verify "Agent" menu item appears in sidebar with Bot icon
- [ ] Click other menu items
- [ ] Click "Agent" to return to dashboard
- [ ] Verify session persists (if session ID is still in state)

### 11. Dark Mode Styling
- [ ] Verify all UI elements follow dark mode palette:
  - Background: dark gray (#0d1117, #161b22)
  - Text: light gray (#e6edf3)
  - Borders: subtle gray (#30363d)
  - Accent colors for buttons (blue, green, red)
- [ ] Verify proper contrast for readability
- [ ] Verify hover states work on interactive elements

### 12. Responsive Design
- [ ] Resize browser window
- [ ] Verify layout adjusts properly
- [ ] Verify no horizontal scrolling
- [ ] Test on mobile viewport (DevTools device mode)

## Expected API Calls

### Session Creation
```
POST /agent/chat
{
  "message": "Hello, I need help with EVE Online.",
  "character_id": 526379435,
  "session_id": null
}
```

### Get Session Details
```
GET /agent/session/{session_id}
```

### Execute Plan
```
POST /agent/execute
{
  "session_id": "...",
  "plan_id": "..."
}
```

### Reject Plan
```
POST /agent/reject
{
  "session_id": "...",
  "plan_id": "...",
  "reason": "Optional reason"
}
```

### Delete Session
```
DELETE /agent/session/{session_id}
```

### WebSocket Stream
```
WS /agent/stream/{session_id}
```

## Known Limitations

- Session creation uses hardcoded character_id (526379435 - Artallus)
- No chat input yet (Phase 5)
- Auto-executing plans don't show approval card (by design)
- WebSocket reconnection has 3 second delay

## Success Criteria

All checkboxes above should pass for Task 5 to be considered complete.
