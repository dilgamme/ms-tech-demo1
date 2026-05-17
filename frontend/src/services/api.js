import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
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

export default api
