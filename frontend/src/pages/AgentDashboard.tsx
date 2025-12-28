import { useState } from 'react';
import { useAgentWebSocket } from '../hooks/useAgentWebSocket';
import { EventStreamDisplay } from '../components/agent/EventStreamDisplay';
import { PlanApprovalCard } from '../components/agent/PlanApprovalCard';
import { CharacterSelector, type Character } from '../components/agent/CharacterSelector';
import { EventFilter } from '../components/agent/EventFilter';
import { EventSearch } from '../components/agent/EventSearch';
import { agentClient } from '../api/agent-client';
import {
  AgentEventType,
  isPlanProposedEvent,
  type AgentEvent,
} from '../types/agent-events';

// Add available characters constant
const availableCharacters: Character[] = [
  { id: 526379435, name: 'Artallus' },
  { id: 1117367444, name: 'Cytrex' },
  { id: 110592475, name: 'Cytricia' },
];

export default function AgentDashboard() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [pendingPlan, setPendingPlan] = useState<{
    planId: string;
    event: AgentEvent;
  } | null>(null);
  const [selectedCharacter, setSelectedCharacter] = useState<number | null>(526379435); // Default to Artallus
  const [autonomyLevel, setAutonomyLevel] = useState<string>('RECOMMENDATIONS');
  const [isCreatingSession, setIsCreatingSession] = useState(false);
  const [eventFilters, setEventFilters] = useState<string[]>([]);
  const [searchQuery, setSearchQuery] = useState('');

  const { events, isConnected, error, clearEvents } = useAgentWebSocket({
    sessionId: sessionId || '',
    onEvent: (event) => {
      // Check for plan approval required
      if (isPlanProposedEvent(event) && !event.payload.auto_executing && event.plan_id) {
        setPendingPlan({
          planId: event.plan_id,
          event,
        });
      }

      // Clear pending plan when approved/rejected
      if (
        event.type === AgentEventType.PLAN_APPROVED ||
        event.type === AgentEventType.PLAN_REJECTED
      ) {
        setPendingPlan(null);
      }
    },
  });

  const handleCreateSession = async () => {
    setIsCreatingSession(true);
    try {
      const response = await agentClient.createSession({
        character_id: selectedCharacter ?? undefined,
        autonomy_level: autonomyLevel as any,
      });
      setSessionId(response.session_id);
      clearEvents();
      setPendingPlan(null);
    } catch (error) {
      console.error('Failed to create session:', error);
      alert('Failed to create session. Please check the console for details.');
    } finally {
      setIsCreatingSession(false);
    }
  };

  const handleApprovePlan = async (planId: string) => {
    if (!sessionId) return;

    try {
      await agentClient.executePlan({ session_id: sessionId, plan_id: planId });
      setPendingPlan(null);
    } catch (error) {
      console.error('Failed to approve plan:', error);
      alert('Failed to approve plan. Please check the console for details.');
    }
  };

  const handleRejectPlan = async (planId: string, reason?: string) => {
    if (!sessionId) return;

    try {
      await agentClient.rejectPlan({ session_id: sessionId, plan_id: planId, reason });
      setPendingPlan(null);
    } catch (error) {
      console.error('Failed to reject plan:', error);
      alert('Failed to reject plan. Please check the console for details.');
    }
  };

  const handleEndSession = async () => {
    if (!sessionId) return;

    try {
      await agentClient.deleteSession(sessionId);
      setSessionId(null);
      clearEvents();
      setPendingPlan(null);
    } catch (error) {
      console.error('Failed to end session:', error);
      // Even if delete fails, reset local state
      setSessionId(null);
      clearEvents();
      setPendingPlan(null);
    }
  };

  // Filter events based on selected types and search query
  const filteredEvents = events.filter((event) => {
    // Filter by type
    if (eventFilters.length > 0 && !eventFilters.includes(event.type)) {
      return false;
    }

    // Filter by search query
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      const matchesType = event.type.toLowerCase().includes(query);
      const matchesPayload = JSON.stringify(event.payload).toLowerCase().includes(query);
      return matchesType || matchesPayload;
    }

    return true;
  });

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold text-gray-100 mb-8">Agent Dashboard</h1>

      {!sessionId ? (
        <div className="bg-gray-800 p-6 rounded border border-gray-700 max-w-2xl">
          <h2 className="text-xl font-semibold text-gray-100 mb-4">
            Create Agent Session
          </h2>

          <div className="mb-4">
            <CharacterSelector
              characters={availableCharacters}
              selectedId={selectedCharacter}
              onChange={setSelectedCharacter}
            />
          </div>

          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Autonomy Level
            </label>
            <select
              value={autonomyLevel}
              onChange={(e) => setAutonomyLevel(e.target.value)}
              className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100"
              disabled={isCreatingSession}
            >
              <option value="READ_ONLY">Read Only - Always require approval</option>
              <option value="RECOMMENDATIONS">Recommendations - Auto-execute read-only</option>
              <option value="ASSISTED">Assisted - Auto-execute low-risk writes</option>
              <option value="SUPERVISED">Supervised - Auto-execute all (future)</option>
            </select>
            <p className="text-xs text-gray-500 mt-2">
              Controls what actions the agent can perform automatically without your approval
            </p>
          </div>

          <button
            onClick={handleCreateSession}
            disabled={isCreatingSession}
            className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 disabled:cursor-not-allowed text-white font-semibold py-3 px-6 rounded transition"
          >
            {isCreatingSession ? 'Creating Session...' : 'Create Session'}
          </button>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Session Info */}
          <div className="bg-gray-800 p-4 rounded border border-gray-700">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold text-gray-100">
                  Session: {sessionId}
                </h2>
                <p className="text-sm text-gray-400">
                  Autonomy Level: {autonomyLevel}
                </p>
              </div>
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-2">
                  <div
                    className={`w-3 h-3 rounded-full ${
                      isConnected ? 'bg-green-500' : 'bg-red-500'
                    }`}
                  />
                  <span className="text-sm text-gray-400">
                    {isConnected ? 'Connected' : 'Disconnected'}
                  </span>
                </div>
                <button
                  onClick={handleEndSession}
                  className="text-sm text-red-400 hover:text-red-300"
                >
                  End Session
                </button>
              </div>
            </div>
          </div>

          {/* Error Display */}
          {error && (
            <div className="bg-red-900 bg-opacity-20 border border-red-600 rounded p-4">
              <p className="text-red-400">Warning: {error}</p>
            </div>
          )}

          {/* Pending Plan Approval */}
          {pendingPlan && isPlanProposedEvent(pendingPlan.event) && (
            <PlanApprovalCard
              planId={pendingPlan.planId}
              payload={pendingPlan.event.payload}
              onApprove={handleApprovePlan}
              onReject={handleRejectPlan}
            />
          )}

          {/* Event Stream */}
          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold text-gray-100">Event Stream</h2>
              <div className="flex gap-2">
                <EventSearch value={searchQuery} onChange={setSearchQuery} />
                <EventFilter
                  selectedTypes={eventFilters}
                  onChange={setEventFilters}
                />
                <button
                  onClick={clearEvents}
                  className="text-sm text-gray-400 hover:text-gray-300"
                >
                  Clear Events
                </button>
              </div>
            </div>
            <EventStreamDisplay events={filteredEvents} />
          </div>
        </div>
      )}
    </div>
  );
}
