import { useEffect, useRef, useState } from 'react'
import { routePrompt } from './services/api'
import { createPcmPlayer, createPcmRecorder, createVoiceLiveSocket } from './services/voiceLive'
import { MessageList } from './components/MessageList'
import { ChatInput } from './components/ChatInput'
import './index.css'

const STORAGE_KEY = 'mstech_chat_history'
const MAX_CONTEXT_MESSAGES = 6
const MAX_CONTEXT_CHARS = 1200

function App() {
  const [messages, setMessages] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [isVoiceActive, setIsVoiceActive] = useState(false)
  const [voiceStatus, setVoiceStatus] = useState('')
  const voiceSocketRef = useRef(null)
  const voiceRecorderRef = useRef(null)
  const voicePlayerRef = useRef(null)
  const voiceAnswerRef = useRef('')
  const voiceResponseStartedRef = useRef(false)

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

  useEffect(() => {
    return () => {
      stopVoiceSession()
    }
  }, [])

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

  const startVoiceSession = async () => {
    if (isVoiceActive) {
      await stopVoiceSession()
      return
    }

    setVoiceStatus('Connecting')
    voiceAnswerRef.current = ''
    voiceResponseStartedRef.current = false

    try {
      const socket = createVoiceLiveSocket()
      const player = createPcmPlayer()
      voiceSocketRef.current = socket
      voicePlayerRef.current = player

      socket.onopen = async () => {
        setIsVoiceActive(true)
        setVoiceStatus('Listening')
        voiceRecorderRef.current = await createPcmRecorder((base64Audio) => {
          if (socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({
              type: 'input_audio_buffer.append',
              audio: base64Audio,
            }))
          }
        })
      }

      socket.onmessage = async (event) => {
        const payload = JSON.parse(event.data)
        handleVoiceEvent(payload)
      }

      socket.onerror = () => {
        setVoiceStatus('Voice error')
      }

      socket.onclose = async () => {
        await cleanupVoiceSession()
      }
    } catch (error) {
      setVoiceStatus('')
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `Voice error: ${error.message || 'Unable to start microphone session'}`,
        modelUsed: 'Azure-Speech-Voice-Live',
        reason: 'Microphone input -> Voice Live realtime session',
      }])
      await cleanupVoiceSession()
    }
  }

  const stopVoiceSession = async () => {
    const socket = voiceSocketRef.current
    if (socket?.readyState === WebSocket.OPEN) {
      if (voiceRecorderRef.current) {
        await voiceRecorderRef.current.stop()
        voiceRecorderRef.current = null
      }
      setVoiceStatus('Thinking')
      voiceResponseStartedRef.current = true
      socket.send(JSON.stringify({ type: 'voice.stop' }))
      return
    }
    await cleanupVoiceSession()
  }

  const cleanupVoiceSession = async () => {
    setIsVoiceActive(false)
    setVoiceStatus('')

    if (voiceRecorderRef.current) {
      await voiceRecorderRef.current.stop()
      voiceRecorderRef.current = null
    }
    if (voicePlayerRef.current) {
      await voicePlayerRef.current.close()
      voicePlayerRef.current = null
    }
    voiceSocketRef.current = null
  }

  const handleVoiceEvent = async (payload) => {
    if (payload.type === 'voice.connected') {
      setVoiceStatus('Listening')
      return
    }

    if (payload.type === 'voice.error' || payload.type === 'error') {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `Voice error: ${payload.message || payload.error?.message || 'Voice Live request failed'}`,
        modelUsed: 'Azure-Speech-Voice-Live',
        reason: 'Microphone input -> Voice Live realtime session',
      }])
      return
    }

    if (payload.type === 'conversation.item.input_audio_transcription.completed' && payload.transcript) {
      setMessages(prev => [...prev, {
        role: 'user',
        content: payload.transcript,
      }])
      return
    }

    if (payload.type === 'response.audio.delta' && payload.delta) {
      voiceResponseStartedRef.current = true
      setVoiceStatus('Speaking')
      await voicePlayerRef.current?.play(payload.delta)
      return
    }

    if (payload.type === 'response.audio_transcript.delta' && payload.delta) {
      voiceResponseStartedRef.current = true
      voiceAnswerRef.current += payload.delta
      return
    }

    if (payload.type === 'response.audio_transcript.done' || payload.type === 'response.done') {
      const answer = voiceAnswerRef.current.trim()
      if (answer) {
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: answer,
          modelUsed: 'Azure-Speech-Voice-Live',
          reason: 'Microphone input -> Voice Live realtime session',
        }])
        voiceAnswerRef.current = ''
      }
      if (voiceResponseStartedRef.current) {
        voiceSocketRef.current?.close()
        await cleanupVoiceSession()
      }
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
        isVoiceActive={isVoiceActive}
        voiceStatus={voiceStatus}
        onToggleVoice={startVoiceSession}
      />
    </div>
  )
}

export default App
