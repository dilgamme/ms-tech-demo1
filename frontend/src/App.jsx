import { useState, useEffect } from 'react'
import { routePrompt } from './services/api'
import { MessageList } from './components/MessageList'
import { ChatInput } from './components/ChatInput'
import './index.css'

const STORAGE_KEY = 'mstech_chat_history'

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
    // Add user message
    const userMessage = {
      role: 'user',
      content: prompt,
    }
    setMessages(prev => [...prev, userMessage])
    setIsLoading(true)

    try {
      const response = await routePrompt(prompt, messages)
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
    <div className="h-screen flex flex-col bg-gray-900">
      <header className="bg-gradient-to-r from-blue-600 to-purple-600 p-4 text-white shadow-lg">
        <h1 className="text-2xl font-bold">🤖 MS Tech Summit Demo</h1>
        <p className="text-sm text-blue-100">Multi-model AI routing on Azure</p>
      </header>

      <MessageList messages={messages} isLoading={isLoading} />

      <ChatInput
        onSend={handleSendMessage}
        isLoading={isLoading}
        onNewChat={handleNewChat}
      />
    </div>
  )
}

export default App
