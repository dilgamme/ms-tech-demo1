import { useEffect, useRef } from 'react'
import { ModelIndicator } from './ModelIndicator'

export const LoadingDots = () => (
  <span className="loading-dots" aria-label="Loading">
    <span></span>
    <span></span>
    <span></span>
  </span>
)

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
              <div key={idx} className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
                <article className={`message-bubble ${isUser ? 'message-user' : 'message-assistant'}`}>
                  <div className="whitespace-pre-wrap leading-7">{msg.content}</div>
                  {!isUser && <ModelIndicator modelUsed={msg.modelUsed} reason={msg.reason} />}
                </article>
              </div>
            )
          })}

          {isLoading && (
            <div className="flex justify-start">
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
