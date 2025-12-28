import { useRef, useEffect } from 'react';
import type { AgentEvent } from '../../types/agent-events';
import { EventItem } from './EventItem';

interface EventStreamDisplayProps {
  events: AgentEvent[];
  autoScroll?: boolean;
  maxHeight?: string;
}

export function EventStreamDisplay({
  events,
  autoScroll = true,
  maxHeight = '500px',
}: EventStreamDisplayProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to latest events when new events arrive
  useEffect(() => {
    if (autoScroll && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [events, autoScroll]);

  // Show empty state if no events
  if (events.length === 0) {
    return (
      <div className="flex items-center justify-center h-32 bg-gray-800 rounded border border-gray-700">
        <p className="text-gray-500">No events yet. Waiting for agent activity...</p>
      </div>
    );
  }

  return (
    <div
      ref={scrollRef}
      className="space-y-2 overflow-y-auto bg-gray-900 p-4 rounded"
      style={{ maxHeight }}
    >
      {events.map((event, index) => (
        <EventItem key={`${event.timestamp}-${index}`} event={event} />
      ))}
    </div>
  );
}
