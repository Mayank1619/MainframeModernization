import { type FormEvent, useEffect, useRef, useState } from 'react'
import { Crosshair, LoaderCircle, MessageCircle, Send, Trash2, X } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import {
  askCodeAssistant,
  type CodeAssistantHistoryItem,
  type CodeAssistantSource,
} from '../../api/codeAssistantClient'
import './CodeAssistantOverlay.css'

interface ChatMessage {
  id: number
  role: 'user' | 'assistant'
  content: string
  sources?: CodeAssistantSource[]
}

interface FailedRequest {
  question: string
  history: CodeAssistantHistoryItem[]
}

let nextMessageId = 1

export function CodeAssistantOverlay() {
  const [isOpen, setIsOpen] = useState(false)
  const [question, setQuestion] = useState('')
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [failedRequest, setFailedRequest] = useState<FailedRequest | null>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const conversationRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (isOpen) {
      inputRef.current?.focus()
    }
  }, [isOpen])

  useEffect(() => {
    const latestMessage = messages.at(-1)
    if (conversationRef.current && latestMessage?.role === 'user') {
      conversationRef.current.scrollTop = conversationRef.current.scrollHeight
    }
  }, [messages])

  useEffect(() => {
    function closeOnEscape(event: KeyboardEvent): void {
      if (event.key === 'Escape' && isOpen) {
        setIsOpen(false)
      }
    }

    window.addEventListener('keydown', closeOnEscape)
    return () => window.removeEventListener('keydown', closeOnEscape)
  }, [isOpen])

  async function runQuestion(
    submittedQuestion: string,
    history: CodeAssistantHistoryItem[],
    appendUserMessage: boolean,
  ): Promise<void> {
    if (appendUserMessage) {
      setMessages((current) => [
        ...current,
        { id: nextMessageId++, role: 'user', content: submittedQuestion },
      ])
    }

    setIsLoading(true)
    setError(null)
    setFailedRequest(null)

    try {
      const response = await askCodeAssistant(submittedQuestion, history)
      setMessages((current) => [
        ...current,
        {
          id: nextMessageId++,
          role: 'assistant',
          content: response.answer,
          sources: response.sources,
        },
      ])
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'The code assistant is unavailable.')
      setFailedRequest({ question: submittedQuestion, history })
    } finally {
      setIsLoading(false)
    }
  }

  function submitQuestion(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault()
    const submittedQuestion = question.trim()
    if (!submittedQuestion || isLoading) {
      return
    }

    const history: CodeAssistantHistoryItem[] = messages.map(({ role, content }) => ({ role, content }))
    setQuestion('')
    void runQuestion(submittedQuestion, history, true)
  }

  function clearConversation(): void {
    setMessages([])
    setError(null)
    setFailedRequest(null)
    inputRef.current?.focus()
  }

  return (
    <>
      {!isOpen ? (
        <button
          type="button"
          className="rag-assistant-launcher"
          onClick={() => setIsOpen(true)}
          aria-label="Open code assistant"
          title="Open code assistant"
        >
          <MessageCircle aria-hidden="true" size={23} />
          <span>Ask</span>
        </button>
      ) : null}

      <aside
        className={`rag-assistant-panel${isOpen ? ' rag-assistant-panel-open' : ''}`}
        aria-label="Code assistant"
        aria-hidden={!isOpen}
      >
        <header className="rag-assistant-header">
          <div className="rag-assistant-title-group">
            <span className="rag-assistant-mark" aria-hidden="true">
              <MessageCircle size={18} />
            </span>
            <div>
              <p>Bank of Z</p>
              <h2>Code Assistant</h2>
            </div>
          </div>

          <div className="rag-assistant-header-actions">
            <button
              type="button"
              className="rag-assistant-icon-button"
              disabled
              aria-label="Annotation mode is not available yet"
              title="Annotation mode coming next"
            >
              <Crosshair size={18} aria-hidden="true" />
            </button>
            <button
              type="button"
              className="rag-assistant-icon-button"
              onClick={clearConversation}
              disabled={messages.length === 0 && !error}
              aria-label="Clear conversation"
              title="Clear conversation"
            >
              <Trash2 size={18} aria-hidden="true" />
            </button>
            <button
              type="button"
              className="rag-assistant-icon-button"
              onClick={() => setIsOpen(false)}
              aria-label="Close code assistant"
              title="Close code assistant"
            >
              <X size={20} aria-hidden="true" />
            </button>
          </div>
        </header>

        <div className="rag-assistant-conversation" ref={conversationRef} aria-live="polite">
          {messages.length === 0 && !isLoading ? (
            <div className="rag-assistant-empty-state">
              <span aria-hidden="true">
                <MessageCircle size={27} />
              </span>
              <h3>How can I help you?</h3>
            </div>
          ) : null}

          {messages.map((message) => (
            <article
              key={message.id}
              className={`rag-assistant-message rag-assistant-message-${message.role}`}
            >
              <p className="rag-assistant-message-label">
                {message.role === 'user' ? 'You' : 'Code Assistant'}
              </p>
              {message.role === 'assistant' ? (
                <div className="rag-assistant-markdown">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
                </div>
              ) : (
                <p className="rag-assistant-user-text">{message.content}</p>
              )}

              {message.sources && message.sources.length > 0 ? (
                <details className="rag-assistant-sources">
                  <summary>{message.sources.length} retrieved chunks</summary>
                  <ol>
                    {message.sources.map((source, index) => (
                      <li key={`${source.file_id}:${source.start_line}:${index}`}>
                        <code>{source.file_id}</code>
                        <span>
                          Lines {source.start_line}-{source.end_line} · {source.cosine_similarity.toFixed(3)}
                        </span>
                      </li>
                    ))}
                  </ol>
                </details>
              ) : null}
            </article>
          ))}

          {isLoading ? (
            <div className="rag-assistant-loading" role="status">
              <LoaderCircle size={18} aria-hidden="true" />
              <span>Searching the codebase...</span>
            </div>
          ) : null}
        </div>

        <footer className="rag-assistant-composer-wrap">
          {error ? (
            <div className="rag-assistant-error" role="alert">
              <span>{error}</span>
              {failedRequest ? (
                <button
                  type="button"
                  onClick={() => void runQuestion(failedRequest.question, failedRequest.history, false)}
                >
                  Retry
                </button>
              ) : null}
            </div>
          ) : null}

          <form className="rag-assistant-composer" onSubmit={submitQuestion}>
            <textarea
              ref={inputRef}
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === 'Enter' && !event.shiftKey) {
                  event.preventDefault()
                  event.currentTarget.form?.requestSubmit()
                }
              }}
              rows={2}
              maxLength={2000}
              placeholder="Ask about the codebase"
              aria-label="Codebase question"
              disabled={isLoading}
            />
            <button
              type="submit"
              className="rag-assistant-send-button"
              disabled={isLoading || !question.trim()}
              aria-label="Send question"
              title="Send question"
            >
              <Send size={19} aria-hidden="true" />
            </button>
          </form>
        </footer>
      </aside>
    </>
  )
}
