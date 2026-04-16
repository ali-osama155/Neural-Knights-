import { useState, useRef, useEffect } from 'react'
import { Send, Paperclip, Bot } from 'lucide-react'

const initialMessages = [
  {
    id: 1,
    role: 'ai',
    text: "Hi Mariam! 👋 I'm your AI Recruitment Assistant. I can help you improve your CV, prepare for interviews, and find job opportunities. How can I help you today?",
    time: '09:00 AM',
  },
]

const aiResponses = [
  "That's a great question! Based on your CV score of 87, you're in a strong position. I'd recommend focusing on cloud-related technologies to boost it further. ☁️",
  "I can help you prepare for that! Let's start with some common interview questions for frontend developers. Ready to begin? 🎯",
  "Your CV looks solid! The main areas to improve are: adding measurable achievements, including a portfolio link, and using more ATS-friendly keywords. 💡",
  "For React interviews, make sure you understand hooks (useState, useEffect), component lifecycle, and performance optimization techniques. 🚀",
]

let aiIndex = 0

export default function Chatbot() {
  const [messages, setMessages] = useState(initialMessages)
  const [input, setInput] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const bottomRef = useRef()

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isTyping])

  const sendMessage = () => {
    if (!input.trim()) return

    const userMsg = {
      id: Date.now(),
      role: 'user',
      text: input,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    }

    setMessages((prev) => [...prev, userMsg])
    setInput('')
    setIsTyping(true)

    setTimeout(() => {
      const aiMsg = {
        id: Date.now() + 1,
        role: 'ai',
        text: aiResponses[aiIndex % aiResponses.length],
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      }
      aiIndex++
      setIsTyping(false)
      setMessages((prev) => [...prev, aiMsg])
    }, 1500)
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
          style={{
            ...styles.sendBtn,
            background: input.trim() ? '#4fa3e0' : '#e2e8f0',
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
