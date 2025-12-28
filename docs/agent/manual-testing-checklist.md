# Agent Runtime Phase 4 - Manual Testing Checklist

## Purpose
This checklist verifies the complete agent workflow integration including session creation, WebSocket connection, event streaming, plan approval, and runtime verification.

## Prerequisites
- Backend server running on http://localhost:8000
- Frontend dev server running on http://localhost:5173
- PostgreSQL database accessible
- WebSocket endpoint at ws://localhost:8000/agent/stream/{session_id}

---

## Test Environment Setup

- [ ] Backend server is running (`uvicorn main:app --reload`)
- [ ] Frontend dev server is running (`npm run dev`)
- [ ] Backend API docs accessible at http://localhost:8000/docs
- [ ] Frontend accessible at http://localhost:5173

---

## Session Management Tests

### Creating Sessions

- [ ] Navigate to http://localhost:5173/agent
- [ ] Verify "Create Agent Session" form is displayed
- [ ] Select autonomy level: READ_ONLY
- [ ] Click "Create Session" button
- [ ] Verify session ID appears (format: sess-XXXXX)
- [ ] Verify "Connected" status shows with green indicator
- [ ] Repeat for other autonomy levels:
  - [ ] RECOMMENDATIONS
  - [ ] ASSISTED
  - [ ] SUPERVISED

### Session State

- [ ] Verify session details displayed:
  - [ ] Session ID
  - [ ] Autonomy level
  - [ ] Connection status (green dot)
- [ ] Click "End Session" button
- [ ] Verify session is terminated and form reappears
- [ ] Create new session successfully after ending previous one

---

## WebSocket Connection Tests

### Connection Lifecycle

- [ ] Create new session
- [ ] Verify connection status changes to "Connected" (green)
- [ ] Check browser DevTools Network tab for WebSocket connection
- [ ] Verify WebSocket URL: ws://localhost:8000/agent/stream/{session_id}
- [ ] Verify connection state: OPEN (readyState: 1)

### Auto-Reconnect

- [ ] Create session and wait for connection
- [ ] Restart backend server (to close WebSocket)
- [ ] Verify frontend attempts reconnection
- [ ] Verify connection restored when backend available

### Keepalive

- [ ] Create session and wait 60+ seconds
- [ ] Verify connection remains active (green indicator)
- [ ] Check DevTools Network tab for ping/pong messages

---

## Event Stream Display Tests

### Initial State

- [ ] Create session without triggering any actions
- [ ] Verify "No events yet. Waiting for agent activity..." message displays
- [ ] Verify event stream container is visible

### Event Reception

- [ ] Trigger agent activity (via backend API or direct WebSocket send)
- [ ] Send SESSION_CREATED event
- [ ] Verify event appears in stream with:
  - [ ] Correct icon (🟢)
  - [ ] Correct color (green)
  - [ ] Timestamp
  - [ ] Event type label

### Multiple Events

- [ ] Send sequence of events:
  1. [ ] SESSION_CREATED
  2. [ ] PLANNING_STARTED
  3. [ ] PLAN_PROPOSED
  4. [ ] TOOL_CALL_STARTED
  5. [ ] TOOL_CALL_COMPLETED
  6. [ ] ANSWER_READY
  7. [ ] COMPLETED
- [ ] Verify all events display in correct order
- [ ] Verify auto-scroll works (latest event visible)

### Event-Specific Rendering

- [ ] PLAN_PROPOSED shows:
  - [ ] Purpose
  - [ ] Tool count
  - [ ] Auto-executing status
- [ ] TOOL_CALL_STARTED shows:
  - [ ] Tool name
- [ ] TOOL_CALL_COMPLETED shows:
  - [ ] Tool name
  - [ ] Duration in ms
- [ ] TOOL_CALL_FAILED shows:
  - [ ] Tool name
  - [ ] Error message
  - [ ] Retry count
- [ ] ANSWER_READY shows:
  - [ ] Answer text in monospace box
- [ ] AUTHORIZATION_DENIED shows:
  - [ ] Tool name
  - [ ] Denial reason

### Event Stream Controls

- [ ] Click "Clear Events" button
- [ ] Verify all events removed
- [ ] Verify empty state message appears
- [ ] Send new events and verify they appear

---

## Plan Approval Interface Tests

### Plan Approval Card Display

- [ ] Send PLAN_PROPOSED event with auto_executing: false
- [ ] Verify Plan Approval Card appears above event stream
- [ ] Verify card displays:
  - [ ] "Plan Approval Required" header
  - [ ] Purpose text
  - [ ] Tool count
  - [ ] Risk level (with appropriate color)
  - [ ] Step-by-step breakdown
  - [ ] Tool names in code blocks
  - [ ] Argument count for each step

### Approval Flow

- [ ] Click "Approve & Execute" button
- [ ] Verify button shows loading state ("Approving...")
- [ ] Verify API call to /agent/execute
- [ ] Verify PLAN_APPROVED event received
- [ ] Verify approval card disappears
- [ ] Verify EXECUTION_STARTED event appears in stream

### Rejection Flow

- [ ] Send new PLAN_PROPOSED event
- [ ] Click "Reject" button
- [ ] Verify rejection reason textarea appears
- [ ] Type rejection reason: "Not safe to execute"
- [ ] Click "Confirm Rejection" button
- [ ] Verify button shows loading state ("Rejecting...")
- [ ] Verify API call to /agent/reject
- [ ] Verify PLAN_REJECTED event received
- [ ] Verify approval card disappears

### Rejection Cancellation

- [ ] Send PLAN_PROPOSED event
- [ ] Click "Reject" button
- [ ] Type partial rejection reason
- [ ] Click "Cancel" button
- [ ] Verify textarea disappears
- [ ] Verify approve/reject buttons reappear
- [ ] Verify typed reason is cleared

---

## Progress & Retry Visualization Tests

### Progress Indicator

- [ ] Send events with progress information
- [ ] Verify progress bar displays
- [ ] Verify percentage updates correctly
- [ ] Verify "X / Total" text shows

### Retry Indicator

- [ ] Send TOOL_CALL_FAILED event with retry_count: 1
- [ ] Verify RetryIndicator appears
- [ ] Verify retry count display: "Attempt 2 of 4"
- [ ] Verify retry bars show current attempt (yellow, pulsing)
- [ ] Send TOOL_CALL_FAILED with retry_count: 2
- [ ] Verify retry indicator updates
- [ ] Verify previous attempts shown in red
- [ ] Verify error message displays

---

## Autonomy Level Tests

### READ_ONLY Mode

- [ ] Create session with autonomy_level: READ_ONLY
- [ ] Send PLAN_PROPOSED event
- [ ] Verify auto_executing: false
- [ ] Verify approval card appears
- [ ] Verify plan does NOT auto-execute

### RECOMMENDATIONS Mode

- [ ] Create session with autonomy_level: RECOMMENDATIONS
- [ ] Send PLAN_PROPOSED with max_risk_level: READ_ONLY
- [ ] Verify auto_executing: true
- [ ] Verify plan auto-executes without approval

### ASSISTED Mode

- [ ] Create session with autonomy_level: ASSISTED
- [ ] Send PLAN_PROPOSED with max_risk_level: WRITE_LOW_RISK
- [ ] Verify auto_executing: true
- [ ] Verify plan auto-executes without approval
- [ ] Send PLAN_PROPOSED with max_risk_level: WRITE_HIGH_RISK
- [ ] Verify auto_executing: false
- [ ] Verify approval card appears

---

## Error Handling Tests

### WebSocket Error

- [ ] Stop backend while connected
- [ ] Verify connection status changes to "Disconnected" (red)
- [ ] Verify error message displays
- [ ] Restart backend
- [ ] Verify auto-reconnection

### API Error

- [ ] Create session
- [ ] Manually send malformed JSON via WebSocket
- [ ] Verify error handling (no crash)
- [ ] Verify error logged to console

### Session Not Found

- [ ] Create session
- [ ] Delete session from backend
- [ ] Send event
- [ ] Verify graceful error handling

---

## UI/UX Tests

### Dark Mode Styling

- [ ] Verify all components use dark theme colors
- [ ] Verify text readability (sufficient contrast)
- [ ] Verify borders are subtle and visible
- [ ] Verify hover states work on buttons
- [ ] Verify focus states visible on interactive elements

### Responsive Layout

- [ ] Resize browser window to 1024px width
- [ ] Verify layout remains usable
- [ ] Verify event stream scrollable
- [ ] Resize to 768px width
- [ ] Verify components stack appropriately

### Accessibility

- [ ] Navigate with keyboard only (Tab/Shift+Tab)
- [ ] Verify all interactive elements focusable
- [ ] Verify focus indicator visible
- [ ] Press Enter on buttons to activate
- [ ] Verify screen reader compatibility (if available)

---

## Performance Tests

### Event Stream Performance

- [ ] Send 100+ events rapidly
- [ ] Verify UI remains responsive
- [ ] Verify auto-scroll works
- [ ] Verify no memory leaks (check DevTools Memory)

### WebSocket Performance

- [ ] Keep session open for 5+ minutes
- [ ] Verify connection stable
- [ ] Verify no memory leaks
- [ ] Verify keepalive pings don't accumulate

---

## Production Build Tests

### Build Process

- [ ] Run `npm run build`
- [ ] Verify build completes without errors
- [ ] Verify `dist/` folder created
- [ ] Verify assets generated (JS, CSS, HTML)

### Production Deployment

- [ ] Serve production build: `npm run preview`
- [ ] Access preview server
- [ ] Verify Agent Dashboard accessible
- [ ] Verify all functionality works in production mode
- [ ] Check browser console for errors

---

## Cross-Browser Tests (Optional)

- [ ] Test in Chrome
- [ ] Test in Firefox
- [ ] Test in Safari (if available)
- [ ] Test in Edge
- [ ] Verify WebSocket works in all browsers

---

## Final Verification

- [ ] All automated tests pass (27/27)
- [ ] All manual tests completed
- [ ] No console errors in browser
- [ ] No console errors in backend
- [ ] Production build succeeds
- [ ] Documentation complete
- [ ] Code committed and pushed

---

## Known Issues / Notes

_Document any issues discovered during testing:_

-

---

## Testing Completed By

- **Tester:** ________________
- **Date:** ________________
- **Version:** Phase 4 - Task 7
- **Status:** ☐ PASS  ☐ FAIL

---

**End of Manual Testing Checklist**
