import { useState, useRef, useEffect } from 'react'

export const ChatInput = ({ onSend, isLoading, onNewChat }) => {
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

  return (
    <div className="border-t border-gray-700 bg-gray-800 p-4 space-y-2">
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          ref={inputRef}
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask something..."
          disabled={isLoading}
          className="flex-1 bg-gray-700 text-white px-4 py-3 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={isLoading || !input.trim()}
          className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 text-white px-6 py-3 rounded-lg font-medium transition"
        >
          {isLoading ? 'Sending...' : 'Send'}
        </button>
      </form>

      <div className="flex gap-2">
        <button
          onClick={onNewChat}
          disabled={isLoading}
          className="text-sm bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 text-gray-200 px-3 py-2 rounded transition"
        >
          ↻ New Chat
        </button>
        
        {/* Future feature placeholders */}
        <button
          disabled
          className="text-sm bg-gray-800 text-gray-500 px-3 py-2 rounded cursor-not-allowed opacity-50"
          title="Coming soon"
        >
          🎤 Microphone
        </button>
        <button
          disabled
          className="text-sm bg-gray-800 text-gray-500 px-3 py-2 rounded cursor-not-allowed opacity-50"
          title="Coming soon"
        >
          📷 Image Upload
        </button>
      </div>
    </div>
  )
}
