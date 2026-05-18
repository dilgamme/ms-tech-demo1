import { useEffect, useRef } from 'react'
import { ModelIndicator } from './ModelIndicator'

export const LoadingDots = () => (
  <span className="loading-dots" aria-label="Loading">
    <span></span>
    <span></span>
    <span></span>
  </span>
)

export const MessageList = ({ messages, isLoading }) => {
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
              <div className="rounded-lg border border-slate-800 bg-slate-900/70 p-4">
                <div className="text-sm font-medium text-slate-100">Quick</div>
                <p className="mt-2 text-sm text-slate-400">What is Microsoft Azure?</p>
              </div>
              <div className="rounded-lg border border-slate-800 bg-slate-900/70 p-4">
                <div className="text-sm font-medium text-slate-100">Realtime</div>
                <p className="mt-2 text-sm text-slate-400">What is the weather in Warsaw today?</p>
              </div>
              <div className="rounded-lg border border-slate-800 bg-slate-900/70 p-4">
                <div className="text-sm font-medium text-slate-100">Reasoning</div>
                <p className="mt-2 text-sm text-slate-400">Analyze this Azure architecture and tradeoffs.</p>
              </div>
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
