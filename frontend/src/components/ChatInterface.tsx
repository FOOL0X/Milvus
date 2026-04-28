import { useState } from 'react'
import { useChat } from '../api/chat'
import { useChatStore } from '../stores/chatStore'
import MessageList from './MessageList'
import ChatInput from './ChatInput'

export default function ChatInterface() {
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const { messages, sessionId, resetChat } = useChatStore()
  const chatMutation = useChat()

  const handleSend = async (question: string) => {
    useChatStore.getState().addMessage({
      id: crypto.randomUUID(),
      role: 'user',
      content: question,
      timestamp: new Date(),
    })

    try {
      await chatMutation.mutateAsync({
        question,
        session_id: sessionId || undefined,
      })
    } catch (error) {
      console.error('Chat error:', error)
    }
  }

  return (
    <div className="flex h-screen bg-gray-100">
      {/* Sidebar */}
      <div
        className={`${
          sidebarOpen ? 'w-64' : 'w-0'
        } bg-white border-r transition-all duration-300 overflow-hidden`}
      >
        <div className="p-4 border-b">
          <h2 className="text-lg font-semibold">历史对话</h2>
        </div>
        <div className="p-4">
          <button
            onClick={resetChat}
            className="w-full px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg text-sm"
          >
            新建对话
          </button>
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <header className="bg-white border-b px-4 py-3 flex items-center justify-between">
          <div className="flex items-center">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="p-2 hover:bg-gray-100 rounded-lg mr-2"
            >
              <svg
                className="w-5 h-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 6h16M4 12h16M4 18h16"
                />
              </svg>
            </button>
            <h1 className="text-lg font-semibold">智能客服助手</h1>
          </div>
          {sessionId && (
            <span className="text-xs text-gray-400">会话ID: {sessionId.slice(0, 8)}...</span>
          )}
        </header>

        {/* Messages */}
        <MessageList messages={messages} isLoading={chatMutation.isPending} />

        {/* Input */}
        <ChatInput onSend={handleSend} disabled={chatMutation.isPending} />
      </div>
    </div>
  )
}
