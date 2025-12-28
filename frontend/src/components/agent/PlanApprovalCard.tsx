import React, { useState } from 'react';
import type { PlanProposedEventPayload } from '../../types/agent-events';

interface PlanApprovalCardProps {
  planId: string;
  sessionId: string;
  payload: PlanProposedEventPayload;
  onApprove: (planId: string) => Promise<void>;
  onReject: (planId: string, reason?: string) => Promise<void>;
}

export function PlanApprovalCard({
  planId,
  sessionId,
  payload,
  onApprove,
  onReject,
}: PlanApprovalCardProps) {
  const [loading, setLoading] = useState(false);
  const [showRejectReason, setShowRejectReason] = useState(false);
  const [rejectReason, setRejectReason] = useState('');

  const handleApprove = async () => {
    setLoading(true);
    try {
      await onApprove(planId);
    } catch (error) {
      console.error('Failed to approve plan:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleReject = async () => {
    setLoading(true);
    try {
      await onReject(planId, rejectReason || undefined);
      setShowRejectReason(false);
      setRejectReason('');
    } catch (error) {
      console.error('Failed to reject plan:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-yellow-900 bg-opacity-20 border border-yellow-600 rounded p-4">
      <div className="flex items-start gap-3 mb-4">
        <span className="text-3xl">⏸️</span>
        <div className="flex-1">
          <h3 className="text-xl font-bold text-yellow-400 mb-2">
            Plan Approval Required
          </h3>
          <p className="text-gray-300 mb-4">{payload.purpose}</p>

          <div className="bg-gray-800 p-3 rounded mb-4">
            <div className="text-sm text-gray-400 mb-2">
              <strong>Tool Count:</strong> {payload.tool_count}
            </div>
            <div className="text-sm text-gray-400 mb-2">
              <strong>Risk Level:</strong>{' '}
              <span className={`font-semibold ${
                payload.max_risk_level === 'READ_ONLY' ? 'text-green-400' :
                payload.max_risk_level === 'WRITE_LOW_RISK' ? 'text-yellow-400' :
                'text-red-400'
              }`}>
                {payload.max_risk_level}
              </span>
            </div>

            <div className="mt-3">
              <strong className="text-sm text-gray-400">Steps:</strong>
              <ol className="list-decimal list-inside space-y-1 mt-2">
                {payload.steps.map((step, index) => (
                  <li key={index} className="text-sm text-gray-300">
                    <code className="bg-gray-900 px-2 py-1 rounded">
                      {step.tool}
                    </code>
                    {Object.keys(step.arguments).length > 0 && (
                      <span className="text-xs text-gray-500 ml-2">
                        ({Object.keys(step.arguments).length} args)
                      </span>
                    )}
                  </li>
                ))}
              </ol>
            </div>
          </div>

          {!showRejectReason ? (
            <div className="flex gap-3">
              <button
                onClick={handleApprove}
                disabled={loading}
                className="flex-1 bg-green-600 hover:bg-green-700 disabled:bg-gray-700 text-white font-semibold py-2 px-4 rounded transition"
              >
                {loading ? 'Approving...' : '✓ Approve & Execute'}
              </button>
              <button
                onClick={() => setShowRejectReason(true)}
                disabled={loading}
                className="flex-1 bg-red-600 hover:bg-red-700 disabled:bg-gray-700 text-white font-semibold py-2 px-4 rounded transition"
              >
                ✗ Reject
              </button>
            </div>
          ) : (
            <div className="space-y-3">
              <textarea
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
                placeholder="Optional: Provide a reason for rejection"
                className="w-full bg-gray-800 border border-gray-700 rounded p-2 text-gray-300"
                rows={3}
              />
              <div className="flex gap-3">
                <button
                  onClick={handleReject}
                  disabled={loading}
                  className="flex-1 bg-red-600 hover:bg-red-700 disabled:bg-gray-700 text-white font-semibold py-2 px-4 rounded transition"
                >
                  {loading ? 'Rejecting...' : 'Confirm Rejection'}
                </button>
                <button
                  onClick={() => {
                    setShowRejectReason(false);
                    setRejectReason('');
                  }}
                  disabled={loading}
                  className="px-4 py-2 text-gray-400 hover:text-gray-300"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
