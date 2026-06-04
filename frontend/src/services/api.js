import axios from 'axios'
import { getApiAccessToken } from '../auth'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const MEMORY_USER_KEY = 'mstech_memory_user_id'

const getMemoryUserId = () => {
  let memoryUserId = localStorage.getItem(MEMORY_USER_KEY)
  if (!memoryUserId) {
    memoryUserId = crypto.randomUUID()
    localStorage.setItem(MEMORY_USER_KEY, memoryUserId)
  }
  return memoryUserId
}

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

api.interceptors.request.use(async (config) => {
  const accessToken = config.skipOptionalAuth ? null : await getApiAccessToken()
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`
  }
  config.headers['X-Memory-User-ID'] = getMemoryUserId()
  return config
})

api.interceptors.response.use(
  response => response,
  async (error) => {
    const config = error.config
    if (
      error.response?.status === 401
      && config?.headers?.Authorization
      && !config.retriedWithoutOptionalAuth
    ) {
      delete config.headers.Authorization
      config.skipOptionalAuth = true
      config.retriedWithoutOptionalAuth = true
      console.warn('Microsoft token was rejected; retrying with anonymous demo access.')
      return api.request(config)
    }
    throw error
  },
)

export const routePrompt = async (prompt, messages = [], conversationId = null) => {
  try {
    const response = await api.post('/api/routePrompt', {
      prompt,
      messages,
      conversationId,
    })
    return response.data
  } catch (error) {
    console.error('API Error:', error)
    throw error
  }
}

export const listConversations = async () => {
  const response = await api.get('/api/conversations')
  return response.data.conversations
}

export const getConversation = async (conversationId) => {
  const response = await api.get(`/api/conversations/${conversationId}`)
  return response.data
}

export const deleteConversation = async (conversationId) => {
  const response = await api.delete(`/api/conversations/${conversationId}`)
  return response.data
}

export const ragPrompt = async (question, topK = 5) => {
  try {
    const response = await api.post('/api/rag', {
      question,
      topK,
    })
    return response.data
  } catch (error) {
    console.error('RAG API Error:', error)
    throw error
  }
}

export const generateImage = async (prompt) => {
  const response = await api.post('/api/images/generate', {
    prompt,
  })
  return response.data
}

export const analyzeImage = async (prompt, imageDataUrl) => {
  const response = await api.post('/api/images/analyze', {
    prompt,
    imageDataUrl,
  })
  return response.data
}

export const resetMemory = async () => {
  const response = await api.post('/api/memory/reset')
  return response.data
}

export default api
