import { useState, useRef, useEffect } from 'react'
import { Send, Paperclip, Bot } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'

const BACKEND = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function buildInitialMessages(firstName) {
  return [
    {
      id: 'welcome',
      role: 'ai',
      text: `Hi ${firstName}! 👋 I'm your AI Recruitment Assistant. I can help you improve your CV, prepare for interviews, and find job opportunities. How can I help you today?`,
      time: '',
    },
  ]
}

function formatTime(iso) {
  const d = iso ? new Date(iso) : new Date()
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

export default function Chatbot() {
  const { user, loading, getToken } = useAuth()
  const firstName = user?.full_name?.split(' ')[0] || user?.email?.split('@')[0] || 'there'
  const [messages, setMessages] = useState(() => buildInitialMessages('there'))
  const [input, setInput] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const [historyLoaded, setHistoryLoaded] = useState(false)
  const [error, setError] = useState(null)
  const bottomRef = useRef()

  function authFetch(path, opts = {}) {
    const token = getToken()
    return fetch(`${BACKEND}${path}`, {
      ...opts,
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(opts.headers || {}),
      },
    })
  }

  // Once the real user profile loads, personalize the greeting (only if the
  // conversation hasn't started yet, so we don't overwrite an active chat).
  useEffect(() => {
    if (!loading && user) {
      setMessages((prev) => (prev.length === 1 && prev[0].id === 'welcome'
        ? buildInitialMessages(firstName)
        : prev))
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loading, user])

  // Load prior chat history from the backend once the user is known.
  useEffect(() => {
    async function loadHistory() {
      if (loading || !user || historyLoaded) return
      setHistoryLoaded(true)
      try {
        const res = await authFetch('/api/v1/chat/history')
        if (res.ok) {
          const data = await res.json()
          if (data.length > 0) {
            setMessages(data.map((m) => ({
              id: m.id,
              role: m.role === 'assistant' ? 'ai' : 'user',
              text: m.content,
              time: formatTime(m.created_at),
            })))
          }
        }
      } catch (e) {
        console.warn('[Chat] failed to load history:', e)
      }
    }
    loadHistory()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loading, user, historyLoaded])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isTyping])

  const sendMessage = async () => {
    const content = input.trim()
    if (!content || isTyping) return

    const userMsg = {
      id: `local-${Date.now()}`,
      role: 'user',
      text: content,
      time: formatTime(),
    }

    setMessages((prev) => [...prev, userMsg])
    setInput('')
    setIsTyping(true)
    setError(null)

    try {
      const res = await authFetch('/api/v1/chat/message', {
        method: 'POST',
        body: JSON.stringify({ content }),
      })

      if (!res.ok) {
        let detail = ''
        try {
          const body = await res.json()
          detail = body?.detail || ''
        } catch (_) { /* not JSON */ }
        throw new Error(detail || `Chat request failed (${res.status})`)
      }

      const data = await res.json()
      const aiMsg = {
        id: data.ai_message.id,
        role: 'ai',
        text: data.ai_message.content,
        time: formatTime(data.ai_message.created_at),
      }
      setMessages((prev) => [...prev, aiMsg])
    } catch (e) {
      console.warn('[Chat] send failed:', e)
      setError(e.message || 'Something went wrong sending your message.')
      setMessages((prev) => [...prev, {
        id: `error-${Date.now()}`,
        role: 'ai',
        text: "Sorry, I couldn't process that — please try again in a moment.",
        time: formatTime(),
      }])
    } finally {
      setIsTyping(false)
    }
  }

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <div style={styles.container}>
      {/* Header */}
      <div className="card" style={styles.header}>
        <div style={styles.botAvatar}>
          <Bot size={20} color="white" />
        </div>
        <div>
          <h2 style={styles.headerTitle}>AI Recruitment Assistant</h2>
          <p style={styles.onlineText}>🟢 Online — Ready to help</p>
        </div>
      </div>

      {error && (
        <div style={styles.errorBanner}>{error}</div>
      )}

      {/* Messages */}
      <div style={styles.messagesArea}>
        {messages.map((msg) => (
          <div
            key={msg.id}
            style={{
              ...styles.msgRow,
              justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
            }}
          >
            {msg.role === 'ai' && (
              <div style={styles.aiBubbleIcon}>
                <Bot size={14} color="white" />
              </div>
            )}
            <div>
              <div
                style={{
                  ...styles.bubble,
                  ...(msg.role === 'user' ? styles.userBubble : styles.aiBubble),
                }}
              >
                {msg.text}
              </div>
              <p style={{
                ...styles.timeText,
                textAlign: msg.role === 'user' ? 'right' : 'left',
              }}>
                {msg.time}
              </p>
            </div>
          </div>
        ))}

        {/* Typing indicator */}
        {isTyping && (
          <div style={{ ...styles.msgRow, justifyContent: 'flex-start' }}>
            <div style={styles.aiBubbleIcon}>
              <Bot size={14} color="white" />
            </div>
            <div style={{ ...styles.bubble, ...styles.aiBubble }}>
              <div style={styles.typingDots}>
                <span style={styles.dot} />
                <span style={{ ...styles.dot, animationDelay: '0.2s' }} />
                <span style={{ ...styles.dot, animationDelay: '0.4s' }} />
              </div>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div style={styles.inputArea}>
        <button style={styles.attachBtn}>
          <Paperclip size={18} color="#94a3b8" />
        </button>
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKey}
          placeholder="Ask me anything about your job search..."
          style={styles.textarea}
          rows={1}
        />
        <button
          onClick={sendMessage}
          disabled={isTyping}
          style={{
            ...styles.sendBtn,
            background: input.trim() ? '#4fa3e0' : '#e2e8f0',
            cursor: isTyping ? 'default' : 'pointer',
          }}
        >
          <Send size={18} color={input.trim() ? 'white' : '#94a3b8'} />
        </button>
      </div>

      {/* Typing animation CSS */}
      <style>{`
        @keyframes bounce {
          0%, 60%, 100% { transform: translateY(0); }
          30% { transform: translateY(-6px); }
        }
      `}</style>
    </div>
  )
}

const styles = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    height: 'calc(100vh - 128px)',
    gap: 16,
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    gap: 14,
    padding: '16px 20px',
  },
  botAvatar: {
    width: 42,
    height: 42,
    background: 'linear-gradient(135deg, #4fa3e0, #2980c4)',
    borderRadius: 12,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  headerTitle: { fontSize: 16, fontWeight: 700, color: '#0f172a' },
  onlineText: { fontSize: 12, color: '#64748b', marginTop: 2 },
  errorBanner: {
    background: '#fef2f2',
    border: '1px solid #fecaca',
    color: '#dc2626',
    borderRadius: 10,
    padding: '8px 14px',
    fontSize: 13,
  },
  messagesArea: {
    flex: 1,
    overflowY: 'auto',
    display: 'flex',
    flexDirection: 'column',
    gap: 16,
    padding: '4px 4px',
  },
  msgRow: {
    display: 'flex',
    alignItems: 'flex-end',
    gap: 10,
  },
  aiBubbleIcon: {
    width: 30,
    height: 30,
    background: '#4fa3e0',
    borderRadius: 8,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  bubble: {
    maxWidth: 480,
    padding: '12px 16px',
    borderRadius: 16,
    fontSize: 14,
    lineHeight: 1.6,
  },
  aiBubble: {
    background: 'white',
    border: '1px solid #e2e8f0',
    borderBottomLeftRadius: 4,
    color: '#0f172a',
    boxShadow: '0 2px 8px rgba(0,0,0,0.05)',
  },
  userBubble: {
    background: '#4fa3e0',
    color: 'white',
    borderBottomRightRadius: 4,
  },
  timeText: {
    fontSize: 11,
    color: '#94a3b8',
    marginTop: 4,
    paddingLeft: 4,
    paddingRight: 4,
  },
  typingDots: { display: 'flex', gap: 5, padding: '2px 4px' },
  dot: {
    width: 8,
    height: 8,
    background: '#94a3b8',
    borderRadius: '50%',
    display: 'inline-block',
    animation: 'bounce 1.2s infinite',
  },
  inputArea: {
    display: 'flex',
    alignItems: 'center',
    gap: 10,
    background: 'white',
    borderRadius: 14,
    border: '1.5px solid #e2e8f0',
    padding: '10px 14px',
    boxShadow: '0 2px 12px rgba(0,0,0,0.06)',
  },
  attachBtn: {
    background: 'none',
    border: 'none',
    cursor: 'pointer',
    display: 'flex',
    padding: 4,
  },
  textarea: {
    flex: 1,
    border: 'none',
    outline: 'none',
    resize: 'none',
    fontSize: 14,
    fontFamily: 'Inter, sans-serif',
    color: '#0f172a',
    lineHeight: 1.5,
  },
  sendBtn: {
    width: 38,
    height: 38,
    borderRadius: 10,
    border: 'none',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    transition: 'all 0.2s',
    flexShrink: 0,
  },
}
