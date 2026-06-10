import { useEffect, useRef, useState } from 'react'
import { useIsAuthenticated, useMsal } from '@azure/msal-react'
import { loginRequest, msalEnabled } from './auth'
import { analyzeImage, deleteConversation, generateImage, getConversation, listConversations, ragPrompt, routePrompt } from './services/api'
import { createPcmPlayer, createPcmRecorder, createVoiceLiveSocket } from './services/voiceLive'
import { MessageList } from './components/MessageList'
import { ChatInput } from './components/ChatInput'
import './index.css'

const MAX_CONTEXT_MESSAGES = 6
const MAX_CONTEXT_CHARS = 1200
const VOICE_MODEL = 'Azure-Speech-Voice-Live'
const VOICE_REASON = 'Microphone input -> Voice Live realtime session'
const FAST_MODE_KEY = 'mstech_fast_response_mode'

const createMessageId = () => `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`

const isImageGenerationPrompt = (prompt = '') => (
  /\b(create|generate|draw|make|design|illustrate)\b.*\b(image|picture|photo|logo|poster|diagram|illustration)\b/i.test(prompt)
  || /^\s*(create|generate|draw|make|design|illustrate)\b/i.test(prompt)
  || /\b(image|picture|photo|logo|poster|diagram|illustration)\b.*\b(of|showing|with)\b/i.test(prompt)
)

const readImageAsDataUrl = (file) => new Promise((resolve, reject) => {
  const reader = new FileReader()
  reader.onload = () => resolve(reader.result)
  reader.onerror = () => reject(reader.error)
  reader.readAsDataURL(file)
})

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
  const [conversations, setConversations] = useState([])
  const [activeConversationId, setActiveConversationId] = useState(null)
  const [isHistoryLoading, setIsHistoryLoading] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [isRagMode, setIsRagMode] = useState(false)
  const [isFastMode, setIsFastMode] = useState(
    () => localStorage.getItem(FAST_MODE_KEY) === 'true',
  )
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

  useEffect(() => {
    refreshConversations()
  }, [isAuthenticated])

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
        response = await ragPrompt(prompt, 5, isFastMode)
      } else if (isImageGenerationPrompt(prompt)) {
        response = await generateImage(prompt)
      } else {
        const contextMessages = messages.slice(-MAX_CONTEXT_MESSAGES).map(msg => ({
          role: msg.role,
          content: msg.content.slice(0, MAX_CONTEXT_CHARS),
        }))
        response = await routePrompt(
          prompt,
          contextMessages,
          activeConversationId,
          isFastMode,
        )
      }
      const assistantMessage = {
        id: createMessageId(),
        role: 'assistant',
        content: response.answer,
        imageDataUrl: response.imageDataUrl,
        modelUsed: response.modelUsed,
        reason: response.reason || (isRagMode ? `RAG: Azure AI Search index ${response.indexUsed}` : undefined),
        metrics: response.metrics,
        sources: response.sources,
      }
      setMessages(prev => [...prev, assistantMessage])
      if (response.conversationId) {
        setActiveConversationId(response.conversationId)
        setIsLoading(false)
        refreshConversations()
      }
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

  const handleImageSelected = async (file, prompt) => {
    const question = prompt?.trim()
    if (!file || !question || isLoading) {
      return
    }
    setIsLoading(true)
    try {
      const imageDataUrl = await readImageAsDataUrl(file)
      setMessages(prev => [...prev, {
        id: createMessageId(),
        role: 'user',
        content: question,
        imageDataUrl,
      }])
      const response = await analyzeImage(question, imageDataUrl)
      setMessages(prev => [...prev, {
        id: createMessageId(),
        role: 'assistant',
        content: response.answer,
        modelUsed: response.modelUsed,
        reason: response.reason,
      }])
    } catch (error) {
      setMessages(prev => [...prev, {
        id: createMessageId(),
        role: 'assistant',
        content: `Error: ${error.response?.data?.detail || error.message || 'Image analysis failed'}`,
      }])
    } finally {
      setIsLoading(false)
    }
  }

  const handleNewChat = () => {
    if (messages.length === 0 || confirm('Start a new conversation?')) {
      setMessages([])
      setActiveConversationId(null)
    }
  }

  const toggleFastMode = () => {
    setIsFastMode((current) => {
      const next = !current
      localStorage.setItem(FAST_MODE_KEY, String(next))
      return next
    })
  }

  const refreshConversations = async () => {
    try {
      setConversations(await listConversations())
    } catch (error) {
      console.error('Failed to load conversations:', error)
    }
  }

  const handleSelectConversation = async (conversationId) => {
    setIsHistoryLoading(true)
    try {
      const conversation = await getConversation(conversationId)
      setActiveConversationId(conversation.id)
      setMessages(conversation.messages || [])
    } catch (error) {
      console.error('Failed to load conversation:', error)
    } finally {
      setIsHistoryLoading(false)
    }
  }

  const handleDeleteConversation = async (event, conversationId) => {
    event.stopPropagation()
    if (!confirm('Delete this conversation?')) {
      return
    }
    await deleteConversation(conversationId)
    if (activeConversationId === conversationId) {
      setMessages([])
      setActiveConversationId(null)
    }
    await refreshConversations()
  }

  const handleMicrosoftSignIn = async () => {
    await instance.loginRedirect(loginRequest)
  }

  const handleMicrosoftSignOut = async () => {
    await instance.logoutRedirect({
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

      <div className="flex min-h-0 flex-1">
        <aside className="hidden w-64 shrink-0 border-r border-slate-800 bg-slate-950/70 p-3 md:block">
          <p className="mb-2 px-2 text-xs font-semibold uppercase tracking-wider text-slate-500">Conversations</p>
          <div className="space-y-1">
            {conversations.map(conversation => (
              <button
                key={conversation.id}
                type="button"
                onClick={() => handleSelectConversation(conversation.id)}
                className={`group flex w-full items-center gap-2 rounded-lg px-2 py-2 text-left text-sm transition ${
                  activeConversationId === conversation.id
                    ? 'bg-slate-800 text-white'
                    : 'text-slate-400 hover:bg-slate-900 hover:text-slate-200'
                }`}
              >
                <span className="min-w-0 flex-1 truncate">{conversation.title}</span>
                <span
                  role="button"
                  tabIndex={0}
                  onClick={(event) => handleDeleteConversation(event, conversation.id)}
                  className="opacity-0 transition group-hover:opacity-100"
                  aria-label="Delete conversation"
                >
                  ×
                </span>
              </button>
            ))}
            {!conversations.length && (
              <p className="px-2 py-3 text-xs text-slate-600">Your conversations will appear here.</p>
            )}
          </div>
        </aside>

        <main className="min-h-0 min-w-0 flex-1">
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
            isLoading={isLoading || isHistoryLoading}
            onSuggestionSelect={handleSendMessage}
          />
        </main>
      </div>

      <ChatInput
        onSend={handleSendMessage}
        isLoading={isLoading}
        isVoiceActive={isVoiceActive}
        voiceStatus={voiceStatus}
        onToggleVoice={startVoiceSession}
        isRagMode={isRagMode}
        onToggleRag={() => setIsRagMode(prev => !prev)}
        isFastMode={isFastMode}
        onToggleFastMode={toggleFastMode}
        onImageSend={handleImageSelected}
      />
    </div>
  )
}

export default App
