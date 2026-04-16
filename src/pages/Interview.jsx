import { useState } from 'react'
import { Circle, SkipForward, Video, VideoOff, Mic, MicOff } from 'lucide-react'

const questions = [
  "Tell me about yourself and your background in software development.",
  "Describe a challenging project you worked on and how you overcame obstacles.",
  "What is your experience with React.js and modern frontend development?",
  "How do you approach debugging a complex bug in production?",
  "Where do you see yourself in the next 3-5 years?",
]

export default function Interview() {
  const [currentQ, setCurrentQ] = useState(0)
  const [recording, setRecording] = useState(false)
  const [camOn, setCamOn] = useState(true)
  const [micOn, setMicOn] = useState(true)
  const [finished, setFinished] = useState(false)
  const [seconds, setSeconds] = useState(0)
  const [timerInterval, setTimerInterval] = useState(null)

  const toggleRecord = () => {
    if (!recording) {
      setRecording(true)
      setSeconds(0)
      const interval = setInterval(() => setSeconds((s) => s + 1), 1000)
      setTimerInterval(interval)
    } else {
      setRecording(false)
      clearInterval(timerInterval)
      setTimerInterval(null)
    }
  }

  const nextQuestion = () => {
    if (recording) {
      setRecording(false)
      clearInterval(timerInterval)
      setTimerInterval(null)
    }
    if (currentQ < questions.length - 1) {
      setCurrentQ((q) => q + 1)
      setSeconds(0)
    } else {
      setFinished(true)
    }
  }

  const formatTime = (s) => {
    const m = Math.floor(s / 60)
    const sec = s % 60
    return `${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`
  }

  if (finished) {
    return (
      <div style={styles.finishedPage}>
        <div className="card" style={styles.finishedCard}>
          <div style={{ fontSize: 56, marginBottom: 16 }}>🎉</div>
          <h2 style={{ fontSize: 24, fontWeight: 700, color: '#0f172a', marginBottom: 8 }}>
            Interview Complete!
          </h2>
          <p style={{ color: '#64748b', fontSize: 15, marginBottom: 24 }}>
            Great job! Your responses have been recorded and analyzed.
          </p>
          <div style={styles.resultRow}>
            <ResultChip label="Questions Answered" value={questions.length} />
            <ResultChip label="AI Score" value="88%" />
            <ResultChip label="Confidence" value="High" />
          </div>
          <button
            className="btn-primary"
            onClick={() => { setFinished(false); setCurrentQ(0) }}
            style={{ marginTop: 24 }}
          >
            Start New Interview
          </button>
        </div>
      </div>
    )
  }

  return (
    <div>
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <h1 style={styles.pageTitle}>AI Interview Session 🎥</h1>
        <p style={{ color: '#64748b', fontSize: 14, marginTop: 4 }}>
          Answer each question naturally. The AI will analyze your response.
        </p>
      </div>

      {/* Progress bar */}
      <div style={styles.progressBar}>
        <div
          style={{
            ...styles.progressFill,
            width: `${((currentQ) / questions.length) * 100}%`,
          }}
        />
      </div>
      <p style={styles.progressText}>
        Question {currentQ + 1} of {questions.length}
      </p>

      <div style={styles.interviewLayout}>
        {/* Camera feed */}
        <div style={styles.cameraCard}>
          <div style={styles.cameraFeed}>
            {camOn ? (
              <div style={styles.cameraPlaceholder}>
                <div style={{ fontSize: 56 }}>👤</div>
                <p style={{ color: '#94a3b8', fontSize: 13, marginTop: 8 }}>Camera Feed</p>
                {recording && (
                  <div style={styles.recIndicator}>
                    <span style={styles.recDot} />
                    <span style={{ fontSize: 12, color: '#ef4444', fontWeight: 600 }}>
                      REC {formatTime(seconds)}
                    </span>
                  </div>
                )}
              </div>
            ) : (
              <div style={styles.cameraOff}>
                <VideoOff size={40} color="#64748b" />
                <p style={{ color: '#94a3b8', marginTop: 8, fontSize: 13 }}>Camera off</p>
              </div>
            )}
          </div>

          {/* Camera controls */}
          <div style={styles.camControls}>
            <button
              onClick={() => setCamOn(!camOn)}
              style={{
                ...styles.ctrlBtn,
                background: camOn ? '#1e293b' : '#fee2e2',
                color: camOn ? 'white' : '#dc2626',
              }}
            >
              {camOn ? <Video size={16} /> : <VideoOff size={16} />}
              <span>{camOn ? 'Camera On' : 'Camera Off'}</span>
            </button>
            <button
              onClick={() => setMicOn(!micOn)}
              style={{
                ...styles.ctrlBtn,
                background: micOn ? '#1e293b' : '#fee2e2',
                color: micOn ? 'white' : '#dc2626',
              }}
            >
              {micOn ? <Mic size={16} /> : <MicOff size={16} />}
              <span>{micOn ? 'Mic On' : 'Mic Off'}</span>
            </button>
          </div>
        </div>

        {/* Question & controls */}
        <div style={styles.rightSide}>
          {/* Question card */}
          <div className="card" style={styles.questionCard}>
            <span style={styles.qBadge}>Question {currentQ + 1}</span>
            <p style={styles.questionText}>{questions[currentQ]}</p>
            <p style={{ fontSize: 12, color: '#94a3b8', marginTop: 12 }}>
              💡 Take your time — there's no time limit
            </p>
          </div>

          {/* Record button */}
          <div style={styles.recordArea}>
            <button
              onClick={toggleRecord}
              style={{
                ...styles.recordBtn,
                background: recording
                  ? 'linear-gradient(135deg, #ef4444, #dc2626)'
                  : 'linear-gradient(135deg, #4fa3e0, #2980c4)',
              }}
            >
              <Circle
                size={20}
                color="white"
                fill={recording ? 'white' : 'transparent'}
              />
              <span>{recording ? `Stop Recording  •  ${formatTime(seconds)}` : 'Start Recording'}</span>
            </button>

            <button onClick={nextQuestion} className="btn-outline" style={styles.skipBtn}>
              <SkipForward size={16} />
              {currentQ < questions.length - 1 ? 'Next Question' : 'Finish Interview'}
            </button>
          </div>

          {/* Tips */}
          <div className="card" style={styles.tipsCard}>
            <p style={{ fontSize: 13, fontWeight: 600, color: '#0f172a', marginBottom: 8 }}>
              💬 Tips for this answer:
            </p>
            <ul style={{ paddingLeft: 16, fontSize: 13, color: '#64748b', lineHeight: 1.8 }}>
              <li>Be specific and use real examples</li>
              <li>Use the STAR method (Situation, Task, Action, Result)</li>
              <li>Keep your answer between 2–3 minutes</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Pulse animation */}
      <style>{`
        @keyframes pulse-ring {
          0% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.4); }
          70% { box-shadow: 0 0 0 12px rgba(239, 68, 68, 0); }
          100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }
        }
      `}</style>
    </div>
  )
}

function ResultChip({ label, value }) {
  return (
    <div style={{
      textAlign: 'center',
      padding: '16px 24px',
      background: '#ebf5ff',
      borderRadius: 12,
      minWidth: 110,
    }}>
      <p style={{ fontSize: 22, fontWeight: 700, color: '#2980c4' }}>{value}</p>
      <p style={{ fontSize: 12, color: '#64748b', marginTop: 2 }}>{label}</p>
    </div>
  )
}

const styles = {
  pageTitle: { fontSize: 26, fontWeight: 700, color: '#0f172a' },
  progressBar: {
    height: 6,
    background: '#e2e8f0',
    borderRadius: 99,
    overflow: 'hidden',
    marginBottom: 6,
  },
  progressFill: {
    height: '100%',
    background: 'linear-gradient(90deg, #4fa3e0, #2980c4)',
    borderRadius: 99,
    transition: 'width 0.4s ease',
  },
  progressText: { fontSize: 12, color: '#94a3b8', marginBottom: 24 },
  interviewLayout: {
    display: 'flex',
    gap: 24,
    flexWrap: 'wrap',
  },
  cameraCard: {
    flex: 1,
    minWidth: 280,
    display: 'flex',
    flexDirection: 'column',
    gap: 12,
  },
  cameraFeed: {
    background: '#0f172a',
    borderRadius: 16,
    overflow: 'hidden',
    aspectRatio: '16/9',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    border: '1px solid #1e293b',
  },
  cameraPlaceholder: {
    textAlign: 'center',
    position: 'relative',
    width: '100%',
    height: '100%',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
  },
  cameraOff: {
    textAlign: 'center',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
  },
  recIndicator: {
    position: 'absolute',
    top: 12,
    right: 12,
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    background: 'rgba(0,0,0,0.6)',
    padding: '4px 10px',
    borderRadius: 99,
  },
  recDot: {
    width: 8,
    height: 8,
    background: '#ef4444',
    borderRadius: '50%',
    display: 'inline-block',
    animation: 'pulse-ring 1.5s infinite',
  },
  camControls: { display: 'flex', gap: 10 },
  ctrlBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    padding: '9px 16px',
    borderRadius: 10,
    border: 'none',
    cursor: 'pointer',
    fontSize: 13,
    fontWeight: 600,
    fontFamily: 'Inter, sans-serif',
    flex: 1,
    justifyContent: 'center',
    transition: 'all 0.2s',
  },
  rightSide: {
    flex: 1.2,
    minWidth: 280,
    display: 'flex',
    flexDirection: 'column',
    gap: 16,
  },
  questionCard: {
    background: 'linear-gradient(135deg, #ffffff, #f0f9ff)',
    borderColor: '#bfdbfe',
  },
  qBadge: {
    fontSize: 11,
    fontWeight: 700,
    color: '#4fa3e0',
    textTransform: 'uppercase',
    letterSpacing: '0.08em',
    display: 'block',
    marginBottom: 10,
  },
  questionText: {
    fontSize: 18,
    fontWeight: 600,
    color: '#0f172a',
    lineHeight: 1.6,
  },
  recordArea: { display: 'flex', flexDirection: 'column', gap: 12 },
  recordBtn: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 10,
    padding: '14px 24px',
    borderRadius: 12,
    border: 'none',
    color: 'white',
    fontSize: 15,
    fontWeight: 700,
    cursor: 'pointer',
    fontFamily: 'Inter, sans-serif',
    transition: 'all 0.2s',
    boxShadow: '0 4px 16px rgba(79,163,224,0.3)',
  },
  skipBtn: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
  },
  tipsCard: {
    background: '#fffbeb',
    borderColor: '#fde68a',
  },
  finishedPage: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: 'calc(100vh - 200px)',
  },
  finishedCard: {
    textAlign: 'center',
    maxWidth: 480,
    padding: 48,
  },
  resultRow: {
    display: 'flex',
    gap: 12,
    justifyContent: 'center',
    flexWrap: 'wrap',
  },
}
