import { useEffect, useRef, useState } from 'react'
import { useIsAuthenticated, useMsal } from '@azure/msal-react'
import { loginRequest, msalEnabled } from './auth'
import { ragPrompt, routePrompt } from './services/api'
import { createPcmPlayer, createPcmRecorder, createVoiceLiveSocket } from './services/voiceLive'
import { MessageList } from './components/MessageList'
import { ChatInput } from './components/ChatInput'
import './index.css'

const STORAGE_KEY = 'mstech_chat_history'
const MAX_CONTEXT_MESSAGES = 6
const MAX_CONTEXT_CHARS = 1200
const VOICE_MODEL = 'Azure-Speech-Voice-Live'
const VOICE_REASON = 'Microphone input -> Voice Live realtime session'

const createMessageId = () => `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`

const extractUsageMetrics = (payload) => {
  const usage = payload?.response?.usage || payload?.usage
  if (!usage) {
    return null
  }

  return {
    inputTokens: usage.input_tokens ?? usage.prompt_tokens,
    outputTokens: usage.output_tokens ?? usage.completion_tokens,
    totalTokens: usage.total_tokens,
  }
}

function App() {
  const { instance, accounts } = useMsal()
  const isAuthenticated = useIsAuthenticated()
  const [messages, setMessages] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [isRagMode, setIsRagMode] = useState(false)
  const [isVoiceActive, setIsVoiceActive] = useState(false)
  const [voiceStatus, setVoiceStatus] = useState('')
  const voiceSocketRef = useRef(null)
  const voiceRecorderRef = useRef(null)
  const voicePlayerRef = useRef(null)
  const voiceAnswerRef = useRef('')
  const voiceTranscriptTargetRef = useRef('')
  const voiceTranscriptDisplayedRef = useRef('')
  const voiceTranscriptTimerRef = useRef(null)
  const voicePendingMetricsRef = useRef(null)
  const voiceUserTranscriptRef = useRef('')
  const voiceResponseStartedRef = useRef(false)
  const voiceStoppingRef = useRef(false)
  const voiceAssistantMessageIdRef = useRef(null)
  const voiceUserMessageIdRef = useRef(null)
  const voiceResponseStartedAtRef = useRef(null)
  const [voiceStartedAt, setVoiceStartedAt] = useState(null)
  const [voiceElapsedSeconds, setVoiceElapsedSeconds] = useState(0)

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

  useEffect(() => {
    if (!isVoiceActive || !voiceStartedAt) {
      setVoiceElapsedSeconds(0)
      return undefined
    }

    const interval = window.setInterval(() => {
      setVoiceElapsedSeconds(Math.floor((Date.now() - voiceStartedAt) / 1000))
    }, 1000)

    return () => window.clearInterval(interval)
  }, [isVoiceActive, voiceStartedAt])

  const handleSendMessage = async (prompt) => {
    if (!prompt?.trim() || isLoading) {
      return
    }

    // Add user message
    const userMessage = {
      id: createMessageId(),
      role: 'user',
      content: prompt,
    }
    setMessages(prev => [...prev, userMessage])
    setIsLoading(true)

    try {
      let response
      if (isRagMode) {
        response = await ragPrompt(prompt, 5)
      } else {
        const contextMessages = messages.slice(-MAX_CONTEXT_MESSAGES).map(msg => ({
          role: msg.role,
          content: msg.content.slice(0, MAX_CONTEXT_CHARS),
        }))
        response = await routePrompt(prompt, contextMessages)
      }
      const assistantMessage = {
        id: createMessageId(),
        role: 'assistant',
        content: response.answer,
        modelUsed: response.modelUsed,
        reason: response.reason || (isRagMode ? `RAG: Azure AI Search index ${response.indexUsed}` : undefined),
        metrics: response.metrics,
        sources: response.sources,
      }
      setMessages(prev => [...prev, assistantMessage])
    } catch (error) {
      const errorMessage = {
        id: createMessageId(),
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

  const handleMicrosoftSignIn = async () => {
    const result = await instance.loginPopup(loginRequest)
    instance.setActiveAccount(result.account)
  }

  const handleMicrosoftSignOut = async () => {
    await instance.logoutPopup({
      account: instance.getActiveAccount() || accounts[0],
      postLogoutRedirectUri: window.location.origin,
    })
  }

  const startVoiceSession = async () => {
    if (isVoiceActive) {
      await stopVoiceSession()
      return
    }

    setVoiceStatus('Connecting')
    voiceAnswerRef.current = ''
    voiceTranscriptTargetRef.current = ''
    voiceTranscriptDisplayedRef.current = ''
    voicePendingMetricsRef.current = null
    voiceUserTranscriptRef.current = ''
    voiceResponseStartedRef.current = false
    voiceStoppingRef.current = false
    voiceAssistantMessageIdRef.current = null
    voiceUserMessageIdRef.current = null
    voiceUserTranscriptRef.current = ''
    voiceResponseStartedAtRef.current = null

    if (voiceTranscriptTimerRef.current) {
      window.clearInterval(voiceTranscriptTimerRef.current)
      voiceTranscriptTimerRef.current = null
    }

    try {
      const socket = createVoiceLiveSocket()
      const player = createPcmPlayer()
      voiceSocketRef.current = socket
      voicePlayerRef.current = player

      socket.onopen = async () => {
        setIsVoiceActive(true)
        setVoiceStartedAt(Date.now())
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
        id: createMessageId(),
        role: 'assistant',
        content: `Voice error: ${error.message || 'Unable to start microphone session'}`,
        modelUsed: VOICE_MODEL,
        reason: VOICE_REASON,
      }])
      await cleanupVoiceSession()
    }
  }

  const stopVoiceSession = async () => {
    const socket = voiceSocketRef.current
    voiceStoppingRef.current = true
    setVoiceStatus('Ending')
    if (socket?.readyState === WebSocket.OPEN) {
      if (voiceRecorderRef.current) {
        await voiceRecorderRef.current.stop()
        voiceRecorderRef.current = null
      }
      socket.send(JSON.stringify({ type: 'voice.stop' }))
      socket.close()
      return
    }
    await cleanupVoiceSession()
  }

  const cleanupVoiceSession = async () => {
    setIsVoiceActive(false)
    setVoiceStatus('')
    setVoiceStartedAt(null)

    if (voiceRecorderRef.current) {
      await voiceRecorderRef.current.stop()
      voiceRecorderRef.current = null
    }
    if (voicePlayerRef.current) {
      await voicePlayerRef.current.close()
      voicePlayerRef.current = null
    }
    voiceSocketRef.current = null
    voiceStoppingRef.current = false
    voiceAssistantMessageIdRef.current = null
    voiceUserMessageIdRef.current = null
    voiceResponseStartedAtRef.current = null
    voiceTranscriptTargetRef.current = ''
    voiceTranscriptDisplayedRef.current = ''
    voicePendingMetricsRef.current = null

    if (voiceTranscriptTimerRef.current) {
      window.clearInterval(voiceTranscriptTimerRef.current)
      voiceTranscriptTimerRef.current = null
    }
  }

  const upsertVoiceUserMessage = (content, isStreaming = true) => {
    const trimmed = content?.trim()
    if (!trimmed) {
      return
    }

    if (!voiceUserMessageIdRef.current) {
      const id = createMessageId()
      voiceUserMessageIdRef.current = id
      setMessages(prev => [...prev, {
        id,
        role: 'user',
        content: trimmed,
        isStreaming,
      }])
      return
    }

    const id = voiceUserMessageIdRef.current
    setMessages(prev => prev.map(msg => (
      msg.id === id ? { ...msg, content: trimmed, isStreaming } : msg
    )))
  }

  const upsertVoiceAssistantMessage = (content, isStreaming = true, metrics = null) => {
    if (!content) {
      return
    }

    if (!voiceAssistantMessageIdRef.current) {
      const id = createMessageId()
      voiceAssistantMessageIdRef.current = id
      setMessages(prev => [...prev, {
        id,
        role: 'assistant',
        content,
        modelUsed: VOICE_MODEL,
        reason: VOICE_REASON,
        isStreaming,
        metrics,
      }])
      return
    }

    const id = voiceAssistantMessageIdRef.current
    setMessages(prev => prev.map(msg => (
      msg.id === id
        ? {
            ...msg,
            content,
            isStreaming,
            metrics: metrics || msg.metrics,
          }
        : msg
    )))
  }

  const finalizeVoiceAssistantMessage = (metrics = null) => {
    const id = voiceAssistantMessageIdRef.current
    if (!id) {
      return
    }
    setMessages(prev => prev.map(msg => (
      msg.id === id
        ? {
            ...msg,
            isStreaming: false,
            metrics: metrics || msg.metrics,
          }
        : msg
    )))
    voiceAssistantMessageIdRef.current = null
  }

  const finishVoiceTranscriptReveal = () => {
    if (voiceTranscriptTimerRef.current) {
      window.clearInterval(voiceTranscriptTimerRef.current)
      voiceTranscriptTimerRef.current = null
    }

    if (voicePendingMetricsRef.current) {
      finalizeVoiceAssistantMessage(voicePendingMetricsRef.current)
      voicePendingMetricsRef.current = null
      voiceAnswerRef.current = ''
      voiceTranscriptTargetRef.current = ''
      voiceTranscriptDisplayedRef.current = ''
    }
  }

  const revealNextVoiceTranscriptWord = () => {
    const target = voiceTranscriptTargetRef.current
    const displayed = voiceTranscriptDisplayedRef.current

    if (!target || displayed.length >= target.length) {
      finishVoiceTranscriptReveal()
      return
    }

    const remaining = target.slice(displayed.length)
    const nextWord = remaining.match(/^\s*\S+\s*/)
    const nextText = nextWord?.[0] || remaining.slice(0, 1)
    const updated = displayed + nextText

    voiceTranscriptDisplayedRef.current = updated
    upsertVoiceAssistantMessage(updated.trimStart(), true)
  }

  const startVoiceTranscriptReveal = () => {
    if (voiceTranscriptTimerRef.current) {
      return
    }

    revealNextVoiceTranscriptWord()
    voiceTranscriptTimerRef.current = window.setInterval(revealNextVoiceTranscriptWord, 90)
  }

  const queueVoiceTranscript = (text) => {
    if (!text) {
      return
    }

    voiceTranscriptTargetRef.current += text
    startVoiceTranscriptReveal()
  }

  const handleVoiceEvent = async (payload) => {
    if (payload.type === 'voice.connected') {
      setVoiceStatus('Listening')
      return
    }

    if (payload.type === 'voice.error' || payload.type === 'error') {
      setMessages(prev => [...prev, {
        id: createMessageId(),
        role: 'assistant',
        content: `Voice error: ${payload.message || payload.error?.message || 'Voice Live request failed'}`,
        modelUsed: VOICE_MODEL,
        reason: VOICE_REASON,
      }])
      setVoiceStatus('Voice error')
      return
    }

    if (payload.type === 'input_audio_buffer.speech_started') {
      if (voiceResponseStartedRef.current) {
        voicePlayerRef.current?.interrupt()
        if (voiceSocketRef.current?.readyState === WebSocket.OPEN) {
          voiceSocketRef.current.send(JSON.stringify({ type: 'response.cancel' }))
        }
        finalizeVoiceAssistantMessage()
        finishVoiceTranscriptReveal()
        voiceTranscriptTargetRef.current = ''
        voiceTranscriptDisplayedRef.current = ''
        voicePendingMetricsRef.current = null
        voiceResponseStartedRef.current = false
      }
      voiceUserMessageIdRef.current = null
      voiceUserTranscriptRef.current = ''
      setVoiceStatus('Listening')
      return
    }

    if (payload.type === 'input_audio_buffer.speech_stopped') {
      setVoiceStatus('Thinking')
      return
    }

    if (payload.type === 'response.created') {
      voiceResponseStartedAtRef.current = Date.now()
      setVoiceStatus('Thinking')
      return
    }

    if (
      (payload.type === 'conversation.item.input_audio_transcription.delta' ||
        payload.type === 'input_audio_transcription.delta') &&
      payload.delta
    ) {
      voiceUserTranscriptRef.current += payload.delta
      upsertVoiceUserMessage(voiceUserTranscriptRef.current, true)
      return
    }

    if (payload.type === 'conversation.item.input_audio_transcription.completed' && payload.transcript) {
      upsertVoiceUserMessage(payload.transcript, false)
      voiceUserMessageIdRef.current = null
      voiceUserTranscriptRef.current = ''
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
      queueVoiceTranscript(payload.delta)
      return
    }

    if (payload.type === 'response.audio_transcript.done') {
      const answer = voiceAnswerRef.current.trim()
      if (answer) {
        const missingText = answer.slice(voiceTranscriptTargetRef.current.trimStart().length)
        queueVoiceTranscript(missingText)
      }
      return
    }

    if (payload.type === 'response.done') {
      const answer = voiceAnswerRef.current.trim()
      const usageMetrics = extractUsageMetrics(payload)
      const latencyMs = voiceResponseStartedAtRef.current ? Date.now() - voiceResponseStartedAtRef.current : null
      const metrics = {
        ...(usageMetrics || {}),
        ...(latencyMs ? { latencyMs } : {}),
      }
      if (answer) {
        const missingText = answer.slice(voiceTranscriptTargetRef.current.trimStart().length)
        queueVoiceTranscript(missingText)
      }
      voicePendingMetricsRef.current = metrics
      voiceResponseStartedAtRef.current = null
      if (!voiceTranscriptTimerRef.current) {
        finishVoiceTranscriptReveal()
      }
      if (voiceResponseStartedRef.current && !voiceStoppingRef.current) {
        await voicePlayerRef.current?.waitUntilDone()
        voiceResponseStartedRef.current = false
        setVoiceStatus('Listening')
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
          <div className="flex items-center gap-2">
            {msalEnabled && (
              <button
                type="button"
                onClick={isAuthenticated ? handleMicrosoftSignOut : handleMicrosoftSignIn}
                className="inline-flex h-9 items-center justify-center rounded-lg border border-sky-700 bg-sky-950 px-3 text-sm font-medium text-sky-100 transition hover:border-sky-500 hover:bg-sky-900"
              >
                {isAuthenticated ? `Sign out ${accounts[0]?.name || ''}` : 'Sign in with Microsoft'}
              </button>
            )}
            <button
              type="button"
              onClick={handleNewChat}
              disabled={isLoading}
              className="inline-flex h-9 items-center justify-center rounded-lg border border-slate-700 bg-slate-900 px-3 text-sm font-medium text-slate-200 transition hover:border-slate-600 hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
            >
              New chat
            </button>
          </div>
        </div>
      </header>

      <main className="min-h-0 flex-1">
        {isVoiceActive && (
          <div className="mx-auto flex w-full max-w-5xl px-4 pt-3 sm:px-6">
            <div className={`voice-live-banner ${voiceStatus === 'Speaking' ? 'voice-live-speaking' : ''}`}>
              <span className="voice-live-orb" aria-hidden="true" />
              <div>
                <p className="text-sm font-medium text-slate-100">Voice Live is on</p>
                <p className="text-xs text-slate-400">
                  {voiceStatus || 'Listening'} until you stop it · {Math.floor(voiceElapsedSeconds / 60)}:{String(voiceElapsedSeconds % 60).padStart(2, '0')}
                </p>
              </div>
              <button
                type="button"
                onClick={stopVoiceSession}
                className="voice-end-button"
              >
                End conversation
              </button>
              <div className="voice-live-wave" aria-hidden="true">
                <span />
                <span />
                <span />
                <span />
              </div>
            </div>
          </div>
        )}
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
        isRagMode={isRagMode}
        onToggleRag={() => setIsRagMode(prev => !prev)}
      />
    </div>
  )
}

export default App
