/**
 * Agent Runtime Event Types
 *
 * Matches backend event models from copilot_server/agent/events.py
 */

export enum AgentEventType {
  // Session Events
  SESSION_CREATED = "session_created",
  SESSION_RESUMED = "session_resumed",

  // Planning Events
  PLANNING_STARTED = "planning_started",
  PLAN_PROPOSED = "plan_proposed",
  PLAN_APPROVED = "plan_approved",
  PLAN_REJECTED = "plan_rejected",

  // Execution Events
  EXECUTION_STARTED = "execution_started",
  TOOL_CALL_STARTED = "tool_call_started",
  TOOL_CALL_COMPLETED = "tool_call_completed",
  TOOL_CALL_FAILED = "tool_call_failed",
  THINKING = "thinking",

  // Completion Events
  ANSWER_READY = "answer_ready",
  COMPLETED = "completed",
  COMPLETED_WITH_ERRORS = "completed_with_errors",

  // Control Events
  WAITING_FOR_APPROVAL = "waiting_for_approval",
  MESSAGE_QUEUED = "message_queued",
  INTERRUPTED = "interrupted",
  ERROR = "error",
  AUTHORIZATION_DENIED = "authorization_denied",
}

export interface AgentEvent {
  type: AgentEventType;
  session_id: string;
  plan_id?: string;
  payload: Record<string, any>;
  timestamp: string; // ISO 8601
}

export interface PlanProposedEventPayload {
  purpose: string;
  steps: Array<{
    tool: string;
    arguments: Record<string, any>;
  }>;
  max_risk_level: string;
  tool_count: number;
  auto_executing: boolean;
}

export interface ToolCallStartedEventPayload {
  step_index: number;
  tool: string;
  arguments: Record<string, any>;
}

export interface ToolCallCompletedEventPayload {
  step_index: number;
  tool: string;
  duration_ms: number;
  result_preview: string;
}

export interface ToolCallFailedEventPayload {
  step_index: number;
  tool: string;
  error: string;
  retry_count: number;
}

export interface AnswerReadyEventPayload {
  answer: string;
  tool_calls_count: number;
  duration_ms: number;
}

export interface AuthorizationDeniedEventPayload {
  tool: string;
  reason: string;
}

export interface WaitingForApprovalEventPayload {
  message: string;
}

// Type guards
export function isPlanProposedEvent(event: AgentEvent): event is AgentEvent & { payload: PlanProposedEventPayload } {
  return event.type === AgentEventType.PLAN_PROPOSED;
}

export function isToolCallStartedEvent(event: AgentEvent): event is AgentEvent & { payload: ToolCallStartedEventPayload } {
  return event.type === AgentEventType.TOOL_CALL_STARTED;
}

export function isToolCallCompletedEvent(event: AgentEvent): event is AgentEvent & { payload: ToolCallCompletedEventPayload } {
  return event.type === AgentEventType.TOOL_CALL_COMPLETED;
}

export function isAnswerReadyEvent(event: AgentEvent): event is AgentEvent & { payload: AnswerReadyEventPayload } {
  return event.type === AgentEventType.ANSWER_READY;
}

export function isAuthorizationDeniedEvent(event: AgentEvent): event is AgentEvent & { payload: AuthorizationDeniedEventPayload } {
  return event.type === AgentEventType.AUTHORIZATION_DENIED;
}
