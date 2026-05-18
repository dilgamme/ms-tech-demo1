import { useEffect, useRef } from 'react'
import { ModelIndicator } from './ModelIndicator'

export const LoadingDots = () => (
  <span className="loading-dots" aria-label="Loading">
    <span></span>
    <span></span>
    <span></span>
  </span>
)

const SenderIcon = ({ role }) => {
  const isUser = role === 'user'

  return (
    <div className={`sender-icon ${isUser ? 'sender-icon-user' : 'sender-icon-assistant'}`} aria-hidden="true">
      {isUser ? (
        <svg viewBox="0 0 24 24" className="h-4 w-4">
          <path d="M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8Z" fill="none" stroke="currentColor" strokeWidth="2" />
          <path d="M4.5 20a7.5 7.5 0 0 1 15 0" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
        </svg>
      ) : (
        <svg viewBox="0 0 24 24" className="h-4 w-4">
          <rect x="5" y="7" width="14" height="11" rx="3" fill="none" stroke="currentColor" strokeWidth="2" />
          <path d="M9 11h.01M15 11h.01M10 15h4M12 7V4M8 4h8" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
        </svg>
      )}
    </div>
  )
}

const SUGGESTIONS = [
  {
    label: 'Quick',
    prompt: 'What is Microsoft Azure?',
  },
  {
    label: 'Realtime',
    prompt: 'What is the weather in Warsaw today?',
  },
  {
    label: 'Reasoning',
    prompt: 'Analyze this Azure architecture and tradeoffs.',
  },
]

export const MessageList = ({ messages, isLoading, onSuggestionSelect }) => {
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages, isLoading])

  return (
    <div className="h-full overflow-y-auto px-4 py-6 sm:px-6">
      <div className="mx-auto flex min-h-full w-full max-w-4xl flex-col">
        {messages.length === 0 && !isLoading && (
          <div className="mx-auto flex w-full max-w-2xl flex-1 flex-col justify-center py-12 text-center">
            <div className="mb-5 inline-flex self-center rounded-full border border-slate-800 bg-slate-900 px-3 py-1 text-xs text-slate-400">
              Azure AI model router
            </div>
            <h2 className="text-3xl font-semibold text-white sm:text-4xl">Ask anything. The router picks the model.</h2>
            <p className="mt-4 text-sm leading-6 text-slate-400 sm:text-base">
              Try a quick definition, a realtime question, or a deeper architecture prompt.
            </p>
            <div className="mt-8 grid gap-3 text-left sm:grid-cols-3">
              {SUGGESTIONS.map((item) => (
                <button
                  key={item.label}
                  type="button"
                  onClick={() => onSuggestionSelect?.(item.prompt)}
                  className="rounded-lg border border-slate-800 bg-slate-900/70 p-4 text-left transition hover:border-slate-700 hover:bg-slate-900"
                >
                  <div className="text-sm font-medium text-slate-100">{item.label}</div>
                  <p className="mt-2 text-sm text-slate-400">{item.prompt}</p>
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="space-y-5">
          {messages.map((msg, idx) => {
            const isUser = msg.role === 'user'
            return (
              <div key={idx} className={`flex items-start gap-3 ${isUser ? 'justify-end' : 'justify-start'}`}>
                {!isUser && <SenderIcon role={msg.role} />}
                <article className={`message-bubble ${isUser ? 'message-user' : 'message-assistant'}`}>
                  <div className="whitespace-pre-wrap leading-7">{msg.content}</div>
                  {!isUser && <ModelIndicator modelUsed={msg.modelUsed} reason={msg.reason} />}
                </article>
                {isUser && <SenderIcon role={msg.role} />}
              </div>
            )
          })}

          {isLoading && (
            <div className="flex items-start justify-start gap-3">
              <SenderIcon role="assistant" />
              <article className="message-bubble message-assistant">
                <div className="flex items-center gap-2 text-slate-300">
                  <span>Thinking</span>
                  <LoadingDots />
                </div>
              </article>
            </div>
          )}
        </div>

        <div ref={bottomRef} />
      </div>
    </div>
  )
}
