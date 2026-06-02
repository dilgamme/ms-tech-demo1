import axios from 'axios'

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

api.interceptors.request.use((config) => {
  config.headers['X-Memory-User-ID'] = getMemoryUserId()
  return config
})

export const routePrompt = async (prompt, messages = []) => {
  try {
    const response = await api.post('/api/routePrompt', {
      prompt,
      messages,
    })
    return response.data
  } catch (error) {
    console.error('API Error:', error)
    throw error
  }
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

export const resetMemory = async () => {
  const response = await api.post('/api/memory/reset')
  return response.data
}

export default api
