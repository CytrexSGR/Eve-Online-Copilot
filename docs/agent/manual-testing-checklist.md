# Agent Runtime - Manual Testing Checklist

## Purpose
This checklist verifies the complete agent workflow integration including session creation, WebSocket connection, event streaming, plan approval, runtime verification, and Phase 5 advanced features (character selection, event filtering, search, keyboard shortcuts, session persistence).

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

---

## Phase 5: Advanced Features Tests

### Character Selection

- [ ] Navigate to http://localhost:5173/agent
- [ ] Verify character dropdown displays all 3 characters:
  - [ ] Artallus (526379435)
  - [ ] Cytrex (1117367444)
  - [ ] Cytricia (110592475)
- [ ] Select "Artallus" from dropdown
- [ ] Create session
- [ ] Verify selected character is used in session creation
- [ ] End session
- [ ] Change character to "Cytrex"
- [ ] Create new session
- [ ] Verify new character is used

### Event Filtering

- [ ] Create session and generate multiple event types
- [ ] Click "Filter Events" dropdown
- [ ] Verify dropdown shows all event types (19 types)
- [ ] Select "PLAN_PROPOSED" event type
- [ ] Verify only PLAN_PROPOSED events display in stream
- [ ] Click "Select All" button
- [ ] Verify all event types selected
- [ ] Verify selected count badge shows correct number
- [ ] Click "Clear All" button
- [ ] Verify all selections cleared
- [ ] Verify all events display again
- [ ] Select multiple types (PLAN_PROPOSED, ERROR, TOOL_CALL_STARTED)
- [ ] Verify only selected types show in stream
- [ ] Click outside dropdown to close
- [ ] Verify dropdown closes

### Event Search

- [ ] Create session with various events
- [ ] Type "plan" in search input
- [ ] Verify only events containing "plan" in type or payload display
- [ ] Verify clear button (X) appears
- [ ] Type "error" in search
- [ ] Verify search filters by payload content
- [ ] Click clear button (X)
- [ ] Verify search clears and all events display
- [ ] Test search combined with filters:
  - [ ] Select event type filter
  - [ ] Type search query
  - [ ] Verify both filters apply together

### Session Persistence

- [ ] Create session with RECOMMENDATIONS autonomy level
- [ ] Note the session ID
- [ ] Refresh browser page (F5 or Ctrl+R)
- [ ] Verify session ID persists after reload
- [ ] Verify autonomy level persists
- [ ] Verify WebSocket reconnects automatically
- [ ] Click "End Session"
- [ ] Refresh browser page
- [ ] Verify session is cleared (no session restored)
- [ ] Create new session
- [ ] Close browser tab
- [ ] Reopen http://localhost:5173/agent
- [ ] Verify session persists across tab close

### Keyboard Shortcuts

- [ ] Create session
- [ ] Press Ctrl+K
- [ ] Verify search input receives focus
- [ ] Type in search and press Esc
- [ ] Verify search clears
- [ ] Generate some events
- [ ] Press Ctrl+L
- [ ] Verify events are cleared
- [ ] Press Ctrl+/
- [ ] Verify shortcuts help dialog appears
- [ ] Verify help shows:
  - [ ] Ctrl+K: Focus search
  - [ ] Ctrl+/: Show shortcuts
  - [ ] Ctrl+L: Clear events
  - [ ] Esc: Clear filters
- [ ] Click in search input
- [ ] Press Ctrl+K while focused
- [ ] Verify shortcut does NOT trigger (input focused)
- [ ] Tab to message textarea
- [ ] Press Ctrl+Enter
- [ ] Verify shortcut does NOT trigger in textarea

### Chat Message Input (Component Ready - Not Backend Connected)

- [ ] Verify chat input textarea is visible below session info
- [ ] Type a test message in textarea
- [ ] Verify "Send" button is enabled
- [ ] Clear textarea
- [ ] Verify "Send" button is disabled when empty
- [ ] Type message and press Ctrl+Enter
- [ ] Verify message would be sent (currently no backend connection)
- [ ] Verify textarea clears after send

### Message History Display (Component Ready - Not Backend Connected)

- [ ] Verify message history component displays
- [ ] Verify empty state shows "No messages yet"
- [ ] Component ready for future backend integration

---

## Final Verification

- [ ] All automated tests pass (68/68)
- [ ] All manual tests completed
- [ ] No console errors in browser
- [ ] No console errors in backend
- [ ] Production build succeeds
- [ ] Documentation complete
- [ ] Code committed and pushed

---

## Known Issues / Notes

_Document any issues discovered during testing:_

- Chat input and message history components are implemented but not yet connected to backend `/agent/chat` endpoint
- Streaming message support hook is ready but backend SSE implementation pending

---

## Testing Completed By

- **Tester:** ________________
- **Date:** ________________
- **Version:** Phase 5 - Task 10 (Integration & Final Testing)
- **Status:** ☐ PASS  ☐ FAIL

---

**End of Manual Testing Checklist**
