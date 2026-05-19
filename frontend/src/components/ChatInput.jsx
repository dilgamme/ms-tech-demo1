import { useState, useRef, useEffect } from 'react'

export const ChatInput = ({ onSend, isLoading, isVoiceActive, voiceStatus, onToggleVoice }) => {
  const [input, setInput] = useState('')
  const inputRef = useRef(null)

  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  const handleSubmit = (e) => {
    e.preventDefault()
    if (input.trim() && !isLoading) {
      onSend(input.trim())
      setInput('')
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  return (
    <div className="border-t border-slate-800 bg-slate-950 px-4 py-4 sm:px-6">
      <div className="mx-auto w-full max-w-4xl">
        <form onSubmit={handleSubmit} className="rounded-lg border border-slate-800 bg-slate-900 p-2 shadow-2xl shadow-black/20">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Message the Azure AI router"
            disabled={isLoading}
            rows={1}
            className="max-h-36 min-h-12 w-full resize-none bg-transparent px-3 py-3 text-sm leading-6 text-white outline-none placeholder:text-slate-500 disabled:opacity-60 sm:text-base"
          />

          <div className="flex items-center justify-between gap-3 border-t border-slate-800 pt-2">
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={onToggleVoice}
                disabled={isLoading}
                className={isVoiceActive ? 'control-button-active' : 'control-button'}
                title={isVoiceActive ? 'Stop voice session' : 'Start voice session'}
                aria-label="Microphone"
              >
                <svg viewBox="0 0 24 24" aria-hidden="true" className="h-4 w-4">
                  <path d="M12 14a3 3 0 0 0 3-3V6a3 3 0 1 0-6 0v5a3 3 0 0 0 3 3Z" fill="none" stroke="currentColor" strokeWidth="2" />
                  <path d="M5 11a7 7 0 0 0 14 0M12 18v3M9 21h6" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                </svg>
              </button>
              {voiceStatus && (
                <span className="hidden text-xs text-emerald-300 sm:inline">
                  {voiceStatus}
                </span>
              )}
              <button
                type="button"
                disabled
                className="control-button-disabled"
                title="Image upload coming later"
                aria-label="Image upload"
              >
                <svg viewBox="0 0 24 24" aria-hidden="true" className="h-4 w-4">
                  <rect x="4" y="5" width="16" height="14" rx="2" fill="none" stroke="currentColor" strokeWidth="2" />
                  <path d="m7 16 4-4 3 3 2-2 3 3" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                  <circle cx="9" cy="9" r="1.5" fill="currentColor" />
                </svg>
              </button>
            </div>

            <button
              type="submit"
              disabled={isLoading || !input.trim()}
              className="inline-flex h-10 items-center justify-center rounded-lg bg-blue-600 px-4 text-sm font-medium text-white transition hover:bg-blue-500 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-400"
            >
              {isLoading ? 'Sending' : 'Send'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
