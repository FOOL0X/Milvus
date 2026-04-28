import ReactMarkdown from 'react-markdown'
import { Message } from '../stores/chatStore'

interface Props {
  message: Message
}

export default function MessageBubble({ message }: Props) {
  const isUser = message.role === 'user'

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      <div
        className={`max-w-[70%] rounded-2xl px-4 py-3 ${
          isUser
            ? 'bg-blue-500 text-white rounded-br-sm'
            : 'bg-white text-gray-800 rounded-bl-sm shadow'
        }`}
      >
        <ReactMarkdown
          className={`prose prose-sm max-w-none ${
            isUser ? 'text-white' : 'text-gray-800'
          }`}
          components={{
            p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
            ul: ({ children }) => (
              <ul className="list-disc ml-4 mb-2">{children}</ul>
            ),
            ol: ({ children }) => (
              <ol className="list-decimal ml-4 mb-2">{children}</ol>
            ),
            li: ({ children }) => <li className="mb-1">{children}</li>,
            code: ({ children, className }) => {
              const isInline = !className
              return isInline ? (
                <code
                  className={`${
                    isUser ? 'bg-blue-400' : 'bg-gray-100'
                  } rounded px-1 py-0.5 text-sm`}
                >
                  {children}
                </code>
              ) : (
                <code className={`block bg-gray-100 rounded p-2 text-sm overflow-x-auto`}>
                  {children}
                </code>
              )
            },
          }}
        >
          {message.content}
        </ReactMarkdown>

        {/* Source Documents */}
        {message.sources && message.sources.length > 0 && (
          <div className="mt-3 pt-2 border-t border-gray-200">
            <p className="text-xs text-gray-500 mb-2">参考文档：</p>
            <div className="flex flex-wrap gap-2">
              {message.sources.map((source, i) => (
                <div
                  key={i}
                  className="text-xs bg-gray-100 px-2 py-1 rounded flex items-center gap-1"
                >
                  <svg
                    className="w-3 h-3"
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
                  <span className="truncate max-w-[150px]">{source.source}</span>
                  {source.score !== undefined && (
                    <span className="text-gray-400">
                      ({(source.score * 100).toFixed(0)}%)
                    </span>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
