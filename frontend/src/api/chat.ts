import { useMutation } from '@tanstack/react-query'
import { useChatStore, SourceDoc } from '../stores/chatStore'

interface ChatRequest {
  question: string
  session_id?: string
  top_k?: number
}

interface ChatResponse {
  answer: string
  sources: SourceDoc[]
  session_id: string
}

export interface SessionInfo {
  session_id: string
  title: string
  created_at: number
  updated_at: number
}

const API_BASE = import.meta.env.VITE_API_URL || '/api'

export const sendMessage = async (req: ChatRequest): Promise<ChatResponse> => {
  const res = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  })

  if (!res.ok) {
    throw new Error('Failed to send message')
  }

  return res.json()
}

export async function fetchSessions(): Promise<SessionInfo[]> {
  const res = await fetch(`${API_BASE}/chat/sessions`)
  if (!res.ok) throw new Error('Failed to fetch sessions')
  const data = await res.json()
  return data.sessions
}

export async function fetchChatHistory(sessionId: string): Promise<{ session_id: string; history: { role: string; content: string }[] }> {
  const res = await fetch(`${API_BASE}/chat/history/${sessionId}`)
  if (!res.ok) throw new Error('Failed to fetch chat history')
  return res.json()
}

export async function deleteChatHistory(sessionId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/chat/history/${sessionId}`, { method: 'DELETE' })
  if (!res.ok) throw new Error('Failed to delete chat history')
}

export function useChat() {
  const { addMessage, setLoading, setSessionId } = useChatStore()

  return useMutation({
    mutationFn: sendMessage,
    onMutate: () => {
      setLoading(true)
    },
    onSuccess: (data) => {
      addMessage({
        id: crypto.randomUUID(),
        role: 'assistant',
        content: data.answer,
        sources: data.sources,
        timestamp: new Date(),
      })

      if (data.session_id) {
        setSessionId(data.session_id)
      }

      setLoading(false)
    },
    onError: () => {
      setLoading(false)
    },
  })
}
