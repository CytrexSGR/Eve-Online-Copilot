interface RetryIndicatorProps {
  retryCount: number;
  maxRetries: number;
  tool: string;
  error: string;
}

export function RetryIndicator({ retryCount, maxRetries, tool, error }: RetryIndicatorProps) {
  return (
    <div className="bg-yellow-900 bg-opacity-20 border border-yellow-600 rounded p-3">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-yellow-400">🔄</span>
        <span className="text-sm font-semibold text-yellow-400">
          Retrying: {tool}
        </span>
      </div>

      <div className="text-xs text-gray-400 mb-2">
        Error: {error}
      </div>

      <div className="flex gap-1">
        {Array.from({ length: maxRetries + 1 }).map((_, index) => (
          <div
            key={index}
            className={`flex-1 h-1.5 rounded ${
              index < retryCount
                ? 'bg-red-500'
                : index === retryCount
                ? 'bg-yellow-500 animate-pulse'
                : 'bg-gray-700'
            }`}
          />
        ))}
      </div>

      <div className="text-xs text-gray-500 mt-2">
        Attempt {retryCount + 1} of {maxRetries + 1}
      </div>
    </div>
  );
}
