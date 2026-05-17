export const LoadingDots = () => (
  <span className="loading-dots">
    <span></span>
    <span></span>
    <span></span>
  </span>
)

export const MessageList = ({ messages, isLoading }) => {
  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-4">
      {messages.length === 0 && !isLoading && (
        <div className="text-center text-gray-400 mt-8">
          <h2 className="text-2xl font-bold mb-2">MS Tech Demo</h2>
          <p>Multi-model AI routing on Azure</p>
          <p className="text-sm mt-4">Start by asking a question...</p>
        </div>
      )}

      {messages.map((msg, idx) => (
        <div key={idx}>
          <div className={`chat-message ${msg.role}`}>
            <p className="whitespace-pre-wrap">{msg.content}</p>
            {msg.modelUsed && (
              <div className="mt-2 text-xs text-gray-300 space-y-1">
                <div className="text-gray-400">
                  🤖 Model: <span className="font-semibold">{msg.modelUsed}</span>
                </div>
                {msg.reason && (
                  <div className="text-gray-400">
                    📍 Route: <span className="font-semibold">{msg.reason}</span>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      ))}

      {isLoading && (
        <div className="chat-message assistant">
          <p>Thinking <LoadingDots /></p>
        </div>
      )}
    </div>
  )
}
