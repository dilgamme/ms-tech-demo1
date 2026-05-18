import { useState, useEffect } from 'react'
import { routePrompt } from './services/api'
import { MessageList } from './components/MessageList'
import { ChatInput } from './components/ChatInput'
import './index.css'

const STORAGE_KEY = 'mstech_chat_history'
const MAX_CONTEXT_MESSAGES = 6
const MAX_CONTEXT_CHARS = 1200

function App() {
  const [messages, setMessages] = useState([])
  const [isLoading, setIsLoading] = useState(false)

  // Load chat history on mount
  useEffect(() => {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved) {
      try {
        setMessages(JSON.parse(saved))
      } catch (e) {
        console.error('Failed to load chat history:', e)
      }
    }
  }, [])

  // Save chat history whenever it changes
  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(messages))
  }, [messages])

  const handleSendMessage = async (prompt) => {
    if (!prompt?.trim() || isLoading) {
      return
    }

    // Add user message
    const userMessage = {
      role: 'user',
      content: prompt,
    }
    setMessages(prev => [...prev, userMessage])
    setIsLoading(true)

    try {
      const contextMessages = messages.slice(-MAX_CONTEXT_MESSAGES).map(msg => ({
        role: msg.role,
        content: msg.content.slice(0, MAX_CONTEXT_CHARS),
      }))
      const response = await routePrompt(prompt, contextMessages)
      const assistantMessage = {
        role: 'assistant',
        content: response.answer,
        modelUsed: response.modelUsed,
        reason: response.reason,
      }
      setMessages(prev => [...prev, assistantMessage])
    } catch (error) {
      const errorMessage = {
        role: 'assistant',
        content: `Error: ${error.response?.data?.detail || error.message || 'Failed to get response'}`,
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  const handleNewChat = () => {
    if (messages.length > 0 && confirm('Clear chat history?')) {
      setMessages([])
      localStorage.removeItem(STORAGE_KEY)
    }
  }

  return (
    <div className="flex h-screen flex-col bg-slate-950 text-slate-100">
      <header className="border-b border-slate-800 bg-slate-950/95">
        <div className="mx-auto flex w-full max-w-5xl items-center justify-between gap-4 px-4 py-3 sm:px-6">
          <div>
            <h1 className="text-base font-semibold tracking-normal sm:text-lg">MS Tech Demo</h1>
            <p className="text-xs text-slate-400 sm:text-sm">Multi-model AI routing on Azure</p>
          </div>
          <button
            type="button"
            onClick={handleNewChat}
            disabled={isLoading}
            className="inline-flex h-9 items-center justify-center rounded-lg border border-slate-700 bg-slate-900 px-3 text-sm font-medium text-slate-200 transition hover:border-slate-600 hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
          >
            New chat
          </button>
        </div>
      </header>

      <main className="min-h-0 flex-1">
        <MessageList
          messages={messages}
          isLoading={isLoading}
          onSuggestionSelect={handleSendMessage}
        />
      </main>

      <ChatInput
        onSend={handleSendMessage}
        isLoading={isLoading}
      />
    </div>
  )
}

export default App
