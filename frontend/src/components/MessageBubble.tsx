import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { Message } from '../stores/chatStore'

interface Props {
  message: Message
}

export default function MessageBubble({ message }: Props) {
  const isUser = message.role === 'user'
  const [sourcesExpanded, setSourcesExpanded] = useState(false)

  return (
    <div className={`flex gap-3 py-3 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
      {/* Avatar */}
      <div className="shrink-0 mt-0.5">
        {isUser ? (
          <div className="w-8 h-8 rounded-xl gradient-primary flex items-center justify-center shadow-md shadow-primary-500/20">
            <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" />
            </svg>
          </div>
        ) : (
          <div className="w-8 h-8 rounded-xl bg-white shadow-md border border-surface-100 flex items-center justify-center">
            <svg className="w-4 h-4 text-primary-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15.3M14.25 3.104c.251.023.501.05.75.082M19.8 15.3l-1.57.393A9.065 9.065 0 0112 15a9.065 9.065 0 00-6.23.693L5 14.5m14.8.8l1.402 1.402c1.232 1.232.65 3.318-1.067 3.611A48.309 48.309 0 0112 21c-2.773 0-5.491-.235-8.135-.687-1.718-.293-2.3-2.379-1.067-3.61L5 14.5" />
            </svg>
          </div>
        )}
      </div>

      {/* Bubble Content */}
      <div className={`max-w-[75%] min-w-0 ${isUser ? 'items-end' : 'items-start'}`}>
        <div
          className={`rounded-2xl px-4 py-3 ${
            isUser
              ? 'gradient-primary text-white rounded-tr-md shadow-md shadow-primary-500/15'
              : 'glass rounded-tl-md shadow-sm'
          }`}
        >
          <ReactMarkdown
            className={`prose prose-sm max-w-none ${
              isUser ? 'prose-invert' : 'text-surface-700'
            }`}
            components={{
              p: ({ children }) => <p className="mb-2 last:mb-0 leading-relaxed">{children}</p>,
              ul: ({ children }) => <ul className="list-disc ml-4 mb-2 space-y-0.5">{children}</ul>,
              ol: ({ children }) => <ol className="list-decimal ml-4 mb-2 space-y-0.5">{children}</ol>,
              li: ({ children }) => <li className="mb-0.5">{children}</li>,
              strong: ({ children }) => <strong className={isUser ? 'text-white' : 'text-surface-900'}>{children}</strong>,
              code: ({ children, className }) => {
                const isInline = !className
                return isInline ? (
                  <code
                    className={`${
                      isUser ? 'bg-white/20' : 'bg-surface-100'
                    } rounded px-1.5 py-0.5 text-xs font-mono`}
                  >
                    {children}
                  </code>
                ) : (
                  <pre className={`${isUser ? 'bg-white/10' : 'bg-surface-50'} rounded-lg p-3 my-2 overflow-x-auto`}>
                    <code className="text-xs font-mono">{children}</code>
                  </pre>
                )
              },
            }}
          >
            {message.content}
          </ReactMarkdown>
        </div>

        {/* Source Documents */}
        {message.sources && message.sources.length > 0 && (
          <div className="mt-2">
            <button
              onClick={() => setSourcesExpanded(!sourcesExpanded)}
              className="flex items-center gap-1.5 text-xs text-surface-400 hover:text-primary-500 transition-colors px-1"
            >
              <svg
                className={`w-3.5 h-3.5 transition-transform ${sourcesExpanded ? 'rotate-90' : ''}`}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
              <span>参考文档 ({message.sources.length})</span>
            </button>

            {sourcesExpanded && (
              <div className="mt-2 space-y-2 animate-fade-in">
                {message.sources.map((source, i) => (
                  <div
                    key={i}
                    className="glass rounded-lg px-3 py-2 flex items-start gap-2 group hover:shadow-sm transition-shadow"
                  >
                    <svg
                      className="w-4 h-4 text-primary-400 mt-0.5 shrink-0"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                      />
                    </svg>
                    <div className="min-w-0 flex-1">
                      <p className="text-xs text-surface-600 truncate">{source.source}</p>
                      <p className="text-xs text-surface-400 mt-0.5 line-clamp-2">{source.content}</p>
                    </div>
                    {source.score !== undefined && (
                      <span className={`text-xs font-medium px-1.5 py-0.5 rounded-full shrink-0 ${
                        source.score > 0.8 ? 'bg-emerald-50 text-emerald-600' :
                        source.score > 0.5 ? 'bg-amber-50 text-amber-600' :
                        'bg-surface-100 text-surface-500'
                      }`}>
                        {(source.score * 100).toFixed(0)}%
                      </span>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
