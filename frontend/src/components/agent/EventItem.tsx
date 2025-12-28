import type { AgentEvent } from '../../types/agent-events';
import { AgentEventType } from '../../types/agent-events';
import { RetryIndicator } from './RetryIndicator';

interface EventItemProps {
  event: AgentEvent;
}

// Define icon mappings for all event types
const EVENT_ICONS: Record<string, string> = {
  [AgentEventType.SESSION_CREATED]: '🟢',
  [AgentEventType.SESSION_RESUMED]: '🔄',
  [AgentEventType.PLANNING_STARTED]: '🤔',
  [AgentEventType.PLAN_PROPOSED]: '📋',
  [AgentEventType.PLAN_APPROVED]: '✅',
  [AgentEventType.PLAN_REJECTED]: '❌',
  [AgentEventType.EXECUTION_STARTED]: '▶️',
  [AgentEventType.TOOL_CALL_STARTED]: '🔧',
  [AgentEventType.TOOL_CALL_COMPLETED]: '✓',
  [AgentEventType.TOOL_CALL_FAILED]: '⚠️',
  [AgentEventType.THINKING]: '💭',
  [AgentEventType.ANSWER_READY]: '💬',
  [AgentEventType.COMPLETED]: '🎉',
  [AgentEventType.COMPLETED_WITH_ERRORS]: '⚠️',
  [AgentEventType.WAITING_FOR_APPROVAL]: '⏸️',
  [AgentEventType.MESSAGE_QUEUED]: '📬',
  [AgentEventType.INTERRUPTED]: '⏹️',
  [AgentEventType.ERROR]: '🚨',
  [AgentEventType.AUTHORIZATION_DENIED]: '🔒',
};

// Define color mappings for all event types
const EVENT_COLORS: Record<string, string> = {
  [AgentEventType.SESSION_CREATED]: 'text-green-400',
  [AgentEventType.SESSION_RESUMED]: 'text-blue-400',
  [AgentEventType.PLANNING_STARTED]: 'text-purple-400',
  [AgentEventType.PLAN_PROPOSED]: 'text-blue-400',
  [AgentEventType.PLAN_APPROVED]: 'text-green-400',
  [AgentEventType.PLAN_REJECTED]: 'text-red-400',
  [AgentEventType.EXECUTION_STARTED]: 'text-blue-400',
  [AgentEventType.TOOL_CALL_STARTED]: 'text-blue-300',
  [AgentEventType.TOOL_CALL_COMPLETED]: 'text-green-300',
  [AgentEventType.TOOL_CALL_FAILED]: 'text-red-400',
  [AgentEventType.THINKING]: 'text-purple-300',
  [AgentEventType.ANSWER_READY]: 'text-green-400',
  [AgentEventType.COMPLETED]: 'text-green-400',
  [AgentEventType.COMPLETED_WITH_ERRORS]: 'text-yellow-400',
  [AgentEventType.WAITING_FOR_APPROVAL]: 'text-yellow-400',
  [AgentEventType.MESSAGE_QUEUED]: 'text-gray-400',
  [AgentEventType.INTERRUPTED]: 'text-red-400',
  [AgentEventType.ERROR]: 'text-red-400',
  [AgentEventType.AUTHORIZATION_DENIED]: 'text-red-400',
};

export function EventItem({ event }: EventItemProps) {
  const icon = EVENT_ICONS[event.type] || '•';
  const color = EVENT_COLORS[event.type] || 'text-gray-400';
  const timestamp = new Date(event.timestamp).toLocaleTimeString();

  const renderPayload = () => {
    switch (event.type) {
      case AgentEventType.PLAN_PROPOSED:
        return (
          <div className="text-sm text-gray-300">
            <div>Purpose: {event.payload.purpose}</div>
            <div>Tools: {event.payload.tool_count}</div>
            <div>Auto-executing: {event.payload.auto_executing ? 'Yes' : 'No'}</div>
          </div>
        );

      case AgentEventType.TOOL_CALL_STARTED:
        return (
          <div className="text-sm text-gray-300">
            Tool: {event.payload.tool}
          </div>
        );

      case AgentEventType.TOOL_CALL_COMPLETED:
        return (
          <div className="text-sm text-gray-300">
            <div>Tool: {event.payload.tool}</div>
            <div>Duration: {event.payload.duration_ms}ms</div>
          </div>
        );

      case AgentEventType.TOOL_CALL_FAILED:
        if (event.payload.retry_count > 0) {
          return (
            <RetryIndicator
              retryCount={event.payload.retry_count}
              maxRetries={3}
              tool={event.payload.tool}
              error={event.payload.error}
            />
          );
        }
        return (
          <div className="text-sm text-red-400">
            <div>Tool: {event.payload.tool}</div>
            <div>Error: {event.payload.error}</div>
            <div>Retries: {event.payload.retry_count}</div>
          </div>
        );

      case AgentEventType.AUTHORIZATION_DENIED:
        return (
          <div className="text-sm text-red-400">
            <div>Tool: {event.payload.tool}</div>
            <div>Reason: {event.payload.reason}</div>
          </div>
        );

      case AgentEventType.ANSWER_READY:
        return (
          <div className="text-sm text-gray-300">
            <div className="font-mono bg-gray-800 p-2 rounded">
              {event.payload.answer}
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="flex items-start gap-3 p-3 bg-gray-800 rounded border border-gray-700">
      <span className="text-2xl">{icon}</span>
      <div className="flex-1">
        <div className="flex items-center justify-between">
          <span className={`font-semibold ${color}`}>
            {event.type.replace(/_/g, ' ').toUpperCase()}
          </span>
          <span className="text-xs text-gray-500">{timestamp}</span>
        </div>
        {renderPayload()}
      </div>
    </div>
  );
}
