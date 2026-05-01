import { useState, FormEvent, KeyboardEvent, useRef, useEffect } from 'react'

interface Props {
  onSend: (message: string) => void
  disabled?: boolean
}

export default function ChatInput({ onSend, disabled }: Props) {
  const [input, setInput] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const autoResize = () => {
    const el = textareaRef.current
    if (el) {
      el.style.height = 'auto'
      el.style.height = Math.min(el.scrollHeight, 160) + 'px'
    }
  }

  useEffect(() => {
    autoResize()
  }, [input])

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (input.trim() && !disabled) {
      onSend(input.trim())
      setInput('')
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto'
      }
    }
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  return (
    <div className="shrink-0 px-4 pb-4 pt-2">
      <div className="max-w-3xl mx-auto">
        <form onSubmit={handleSubmit} className="glass rounded-2xl shadow-lg shadow-black/5 p-2 flex items-end gap-2">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="输入您的问题..."
            disabled={disabled}
            rows={1}
            className="flex-1 resize-none bg-transparent px-3 py-2.5 text-sm text-surface-800 placeholder:text-surface-400 focus:outline-none disabled:cursor-not-allowed"
          />
          <button
            type="submit"
            disabled={!input.trim() || disabled}
            className="shrink-0 w-10 h-10 gradient-primary text-white rounded-xl flex items-center justify-center shadow-md shadow-primary-500/20 hover:shadow-lg hover:shadow-primary-500/30 disabled:opacity-40 disabled:shadow-none disabled:cursor-not-allowed transition-all duration-200"
          >
            {disabled ? (
              <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24">
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                  fill="none"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                />
              </svg>
            ) : (
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
              </svg>
            )}
          </button>
        </form>
        <p className="text-[11px] text-surface-400 text-center mt-2">
          按 Enter 发送，Shift + Enter 换行
        </p>
      </div>
    </div>
  )
}
