import { create } from 'zustand'

export interface SourceDoc {
  content: string
  source: string
  score?: number
}

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  sources?: SourceDoc[]
  timestamp: Date
}

interface ChatStore {
  messages: Message[]
  sessionId: string | null
  isLoading: boolean
  addMessage: (msg: Message) => void
  setLoading: (loading: boolean) => void
  setSessionId: (sessionId: string) => void
  resetChat: () => void
}

export const useChatStore = create<ChatStore>((set) => ({
  messages: [],
  sessionId: null,
  isLoading: false,
  addMessage: (msg) => set((state) => ({
    messages: [...state.messages, msg]
  })),
  setLoading: (loading) => set({ isLoading: loading }),
  setSessionId: (sessionId) => set({ sessionId }),
  resetChat: () => set({ messages: [], sessionId: null }),
}))
