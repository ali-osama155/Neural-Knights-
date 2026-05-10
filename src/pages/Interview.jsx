import { useState, useRef, useEffect } from 'react'
import { Circle, Video, VideoOff, Mic, MicOff, ChevronRight, Clock, CheckCircle } from 'lucide-react'

const MAX_SECONDS = 10 * 60 // 10 minutes

const questions = [
  "Tell me about yourself and your background in software development.",
  "Describe a challenging project you worked on and how you overcame obstacles.",
  "What is your experience with React.js and modern frontend development?",
  "How do you approach debugging a complex bug in production?",
  "Where do you see yourself in the next 3–5 years?",
]

export default function Interview() {
  // Session state
  const [phase, setPhase] = useState('idle') // idle | countdown | recording | finished
  const [seconds, setSeconds] = useState(0)
  const [countdown, setCountdown] = useState(3)
  const [currentQ, setCurrentQ] = useState(0)
  const [camOn, setCamOn] = useState(true)
  const [micOn, setMicOn] = useState(true)

  // Media
  const videoRef = useRef(null)
  const streamRef = useRef(null)
  const mediaRecorderRef = useRef(null)
  const chunksRef = useRef([])
  const timerRef = useRef(null)
  const countdownRef = useRef(null)

  // Start camera preview on mount
  useEffect(() => {
    startCamera()
    return () => stopCamera()
  }, [])

  // Sync video track with camOn toggle
  useEffect(() => {
    if (streamRef.current) {
      streamRef.current.getVideoTracks().forEach((t) => (t.enabled = camOn))
    }
  }, [camOn])

  // Sync audio track with micOn toggle
  useEffect(() => {
    if (streamRef.current) {
      streamRef.current.getAudioTracks().forEach((t) => (t.enabled = micOn))
    }
  }, [micOn])

  // Auto-stop when 10 min reached
  useEffect(() => {
    if (seconds >= MAX_SECONDS && phase === 'recording') {
      stopSession(true)
    }
  }, [seconds])

  async function startCamera() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true })
      streamRef.current = stream
      if (videoRef.current) {
        videoRef.current.srcObject = stream
      }
    } catch (err) {
      console.warn('Camera access denied:', err)
    }
  }

  function stopCamera() {
    streamRef.current?.getTracks().forEach((t) => t.stop())
    clearInterval(timerRef.current)
    clearInterval(countdownRef.current)
  }

  function beginCountdown() {
    setCountdown(3)
    setPhase('countdown')
    let c = 3
    countdownRef.current = setInterval(() => {
      c -= 1
      setCountdown(c)
      if (c === 0) {
        clearInterval(countdownRef.current)
        startRecording()
      }
    }, 1000)
  }

  function startRecording() {
    chunksRef.current = []
    if (streamRef.current) {
      const mr = new MediaRecorder(streamRef.current)
      mr.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data)
      }
      mr.start(1000) // collect every second
      mediaRecorderRef.current = mr
    }
    setSeconds(0)
    setPhase('recording')
    timerRef.current = setInterval(() => setSeconds((s) => s + 1), 1000)
  }

  function stopSession(autoStopped = false) {
    clearInterval(timerRef.current)
    if (mediaRecorderRef.current?.state !== 'inactive') {
      mediaRecorderRef.current?.stop()
    }
    setPhase('finished')

    // Build downloadable blob
    setTimeout(() => {
      const blob = new Blob(chunksRef.current, { type: 'video/webm' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `interview-session-${Date.now()}.webm`
      // Don't auto-download — just store for button
      window._interviewBlob = url
    }, 500)
  }

  function downloadRecording() {
    if (window._interviewBlob) {
      const a = document.createElement('a')
      a.href = window._interviewBlob
      a.download = `interview-session-${Date.now()}.webm`
      a.click()
    }
  }

  function restart() {
    setPhase('idle')
    setSeconds(0)
    setCurrentQ(0)
    startCamera()
  }

  const formatTime = (s) => {
    const m = Math.floor(s / 60)
    const sec = s % 60
    return `${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`
  }

  const remaining = MAX_SECONDS - seconds
  const progressPct = (seconds / MAX_SECONDS) * 100

  // ─── FINISHED SCREEN ───────────────────────────────────────────
  if (phase === 'finished') {
    return (
      <div style={styles.finishedPage}>
        <div className="card" style={styles.finishedCard}>
          <div style={{ fontSize: 56, marginBottom: 12 }}>🎉</div>
          <h2 style={{ fontSize: 24, fontWeight: 700, color: '#0f172a', marginBottom: 8 }}>
            Interview Complete!
          </h2>
          <p style={{ color: '#64748b', fontSize: 15, marginBottom: 24 }}>
            Your full session has been recorded and is ready for AI analysis.
          </p>
          <div style={styles.resultRow}>
            <ResultChip label="Questions" value={questions.length} />
            <ResultChip label="Duration" value={formatTime(seconds)} />
            <ResultChip label="AI Score" value="—" />
          </div>

          <div style={{ display: 'flex', gap: 12, marginTop: 28, justifyContent: 'center', flexWrap: 'wrap' }}>
            <button
              className="btn-primary"
              onClick={downloadRecording}
              style={{ display: 'flex', alignItems: 'center', gap: 8 }}
            >
              ⬇ Download Recording
            </button>
            <button className="btn-outline" onClick={restart}>
              Start New Interview
            </button>
          </div>

          <div style={styles.submitNote}>
            <CheckCircle size={14} color="#16a34a" />
            <span>Recording saved — submit to backend for AI analysis</span>
          </div>
        </div>
      </div>
    )
  }

  // ─── MAIN SESSION ───────────────────────────────────────────────
  return (
    <div>
      {/* Header */}
      <div style={{ marginBottom: 20 }}>
        <h1 style={styles.pageTitle}>AI Interview Session 🎥</h1>
        <p style={{ color: '#64748b', fontSize: 14, marginTop: 4 }}>
          One continuous 10-minute recording covering all questions.
        </p>
      </div>

      {/* Global time bar */}
      {phase === 'recording' && (
        <div style={styles.timeBarWrap}>
          <div style={styles.timeBarTrack}>
            <div
              style={{
                ...styles.timeBarFill,
                width: `${progressPct}%`,
                background: progressPct > 85
                  ? 'linear-gradient(90deg, #ef4444, #dc2626)'
                  : 'linear-gradient(90deg, #4fa3e0, #2980c4)',
              }}
            />
          </div>
          <div style={styles.timeBarLabels}>
            <span style={{ fontSize: 12, color: '#64748b' }}>
              <Clock size={11} style={{ marginRight: 4, verticalAlign: 'middle' }} />
              Elapsed: <b>{formatTime(seconds)}</b>
            </span>
            <span style={{ fontSize: 12, color: remaining < 60 ? '#ef4444' : '#94a3b8', fontWeight: 600 }}>
              {formatTime(remaining)} left
            </span>
          </div>
        </div>
      )}

      <div style={styles.layout}>
        {/* LEFT — Camera */}
        <div style={styles.cameraCol}>
          <div style={styles.cameraFeed}>
            {/* Countdown overlay */}
            {phase === 'countdown' && (
              <div style={styles.countdownOverlay}>
                <div style={styles.countdownNum}>{countdown}</div>
                <p style={{ color: 'rgba(255,255,255,0.7)', fontSize: 14, marginTop: 8 }}>
                  Get ready…
                </p>
              </div>
            )}

            {/* REC badge */}
            {phase === 'recording' && (
              <div style={styles.recBadge}>
                <span style={styles.recDot} />
                <span style={{ fontSize: 12, color: '#ef4444', fontWeight: 700 }}>
                  REC {formatTime(seconds)}
                </span>
              </div>
            )}

            {/* Video element */}
            <video
              ref={videoRef}
              autoPlay
              muted
              playsInline
              style={{
                width: '100%',
                height: '100%',
                objectFit: 'cover',
                display: camOn ? 'block' : 'none',
                borderRadius: 16,
              }}
            />

            {!camOn && (
              <div style={styles.camOff}>
                <VideoOff size={40} color="#64748b" />
                <p style={{ color: '#94a3b8', marginTop: 8, fontSize: 13 }}>Camera off</p>
              </div>
            )}
          </div>

          {/* Controls */}
          <div style={styles.camControls}>
            <button
              onClick={() => setCamOn(!camOn)}
              style={{
                ...styles.ctrlBtn,
                background: camOn ? '#1e293b' : '#fee2e2',
                color: camOn ? 'white' : '#dc2626',
              }}
            >
              {camOn ? <Video size={15} /> : <VideoOff size={15} />}
              {camOn ? 'Camera On' : 'Camera Off'}
            </button>
            <button
              onClick={() => setMicOn(!micOn)}
              style={{
                ...styles.ctrlBtn,
                background: micOn ? '#1e293b' : '#fee2e2',
                color: micOn ? 'white' : '#dc2626',
              }}
            >
              {micOn ? <Mic size={15} /> : <MicOff size={15} />}
              {micOn ? 'Mic On' : 'Mic Off'}
            </button>
          </div>

          {/* Main action button */}
          {phase === 'idle' && (
            <button onClick={beginCountdown} style={styles.startBtn}>
              <Circle size={18} color="white" />
              Start 10-Min Interview
            </button>
          )}
          {phase === 'recording' && (
            <button onClick={() => stopSession(false)} style={styles.stopBtn}>
              <Circle size={18} color="white" fill="white" />
              End & Save Session
            </button>
          )}
        </div>

        {/* RIGHT — Questions panel */}
        <div style={styles.rightCol}>
          <div className="card" style={styles.questionsCard}>
            <h3 style={styles.qPanelTitle}>Interview Questions</h3>
            <p style={{ fontSize: 12, color: '#94a3b8', marginBottom: 16 }}>
              Navigate at your own pace during the session
            </p>

            {questions.map((q, i) => (
              <button
                key={i}
                onClick={() => phase === 'recording' && setCurrentQ(i)}
                style={{
                  ...styles.qItem,
                  ...(currentQ === i ? styles.qItemActive : {}),
                  cursor: phase === 'recording' ? 'pointer' : 'default',
                }}
              >
                <div style={{
                  ...styles.qNumber,
                  background: currentQ === i ? '#4fa3e0' : '#e2e8f0',
                  color: currentQ === i ? 'white' : '#64748b',
                }}>
                  {i + 1}
                </div>
                <span style={{
                  fontSize: 13,
                  color: currentQ === i ? '#0f172a' : '#64748b',
                  fontWeight: currentQ === i ? 600 : 400,
                  textAlign: 'left',
                  lineHeight: 1.5,
                  flex: 1,
                }}>
                  {q}
                </span>
                {currentQ === i && phase === 'recording' && (
                  <ChevronRight size={14} color="#4fa3e0" />
                )}
              </button>
            ))}
          </div>

          {/* Active question highlight */}
          {phase === 'recording' && (
            <div className="card" style={styles.activeQCard}>
              <span style={styles.qBadge}>Now Answering — Q{currentQ + 1}</span>
              <p style={styles.activeQText}>{questions[currentQ]}</p>
              {currentQ < questions.length - 1 && (
                <button
                  onClick={() => setCurrentQ((q) => q + 1)}
                  style={styles.nextQBtn}
                >
                  <ChevronRight size={14} />
                  Next Question
                </button>
              )}
            </div>
          )}

          {/* Tips */}
          <div className="card" style={styles.tipsCard}>
            <p style={{ fontSize: 13, fontWeight: 600, color: '#0f172a', marginBottom: 8 }}>
              💬 Interview Tips
            </p>
            <ul style={{ paddingLeft: 16, fontSize: 13, color: '#64748b', lineHeight: 1.9 }}>
              <li>Use the STAR method (Situation, Task, Action, Result)</li>
              <li>Aim 2–3 min per question — total 10 min session</li>
              <li>Click a question number to jump to it</li>
              <li>Camera & mic can be toggled anytime</li>
            </ul>
          </div>
        </div>
      </div>

      <style>{`
        @keyframes pulse-rec {
          0% { opacity: 1; }
          50% { opacity: 0.3; }
          100% { opacity: 1; }
        }
        @keyframes countdown-pop {
          0% { transform: scale(0.5); opacity: 0; }
          60% { transform: scale(1.15); opacity: 1; }
          100% { transform: scale(1); }
        }
      `}</style>
    </div>
  )
}

function ResultChip({ label, value }) {
  return (
    <div style={{
      textAlign: 'center',
      padding: '14px 22px',
      background: '#ebf5ff',
      borderRadius: 12,
      minWidth: 100,
    }}>
      <p style={{ fontSize: 20, fontWeight: 700, color: '#2980c4' }}>{value}</p>
      <p style={{ fontSize: 12, color: '#64748b', marginTop: 2 }}>{label}</p>
    </div>
  )
}

const styles = {
  pageTitle: { fontSize: 26, fontWeight: 700, color: '#0f172a' },

  timeBarWrap: { marginBottom: 20 },
  timeBarTrack: {
    height: 8,
    background: '#e2e8f0',
    borderRadius: 99,
    overflow: 'hidden',
    marginBottom: 6,
  },
  timeBarFill: {
    height: '100%',
    borderRadius: 99,
    transition: 'width 1s linear, background 0.5s',
  },
  timeBarLabels: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },

  layout: { display: 'flex', gap: 24, flexWrap: 'wrap' },

  cameraCol: {
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
    position: 'relative',
  },
  camOff: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    width: '100%',
    height: '100%',
  },
  countdownOverlay: {
    position: 'absolute',
    inset: 0,
    background: 'rgba(15,23,42,0.85)',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 10,
    borderRadius: 16,
  },
  countdownNum: {
    fontSize: 96,
    fontWeight: 800,
    color: '#4fa3e0',
    lineHeight: 1,
    animation: 'countdown-pop 0.8s ease',
  },
  recBadge: {
    position: 'absolute',
    top: 12,
    right: 12,
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    background: 'rgba(0,0,0,0.65)',
    padding: '5px 12px',
    borderRadius: 99,
    zIndex: 5,
  },
  recDot: {
    width: 8,
    height: 8,
    background: '#ef4444',
    borderRadius: '50%',
    display: 'inline-block',
    animation: 'pulse-rec 1.2s infinite',
  },
  camControls: { display: 'flex', gap: 10 },
  ctrlBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: 7,
    padding: '9px 14px',
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
  startBtn: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 10,
    padding: '14px',
    borderRadius: 12,
    border: 'none',
    background: 'linear-gradient(135deg, #4fa3e0, #2980c4)',
    color: 'white',
    fontSize: 15,
    fontWeight: 700,
    cursor: 'pointer',
    fontFamily: 'Inter, sans-serif',
    boxShadow: '0 4px 16px rgba(79,163,224,0.35)',
    transition: 'all 0.2s',
  },
  stopBtn: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 10,
    padding: '14px',
    borderRadius: 12,
    border: 'none',
    background: 'linear-gradient(135deg, #ef4444, #dc2626)',
    color: 'white',
    fontSize: 15,
    fontWeight: 700,
    cursor: 'pointer',
    fontFamily: 'Inter, sans-serif',
    boxShadow: '0 4px 16px rgba(239,68,68,0.3)',
    transition: 'all 0.2s',
  },

  rightCol: {
    flex: 1.2,
    minWidth: 280,
    display: 'flex',
    flexDirection: 'column',
    gap: 16,
  },
  questionsCard: { padding: 20 },
  qPanelTitle: { fontSize: 15, fontWeight: 700, color: '#0f172a', marginBottom: 4 },
  qItem: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: 12,
    padding: '10px 8px',
    borderRadius: 10,
    border: 'none',
    background: 'transparent',
    width: '100%',
    transition: 'background 0.15s',
    marginBottom: 4,
  },
  qItemActive: { background: '#f0f9ff' },
  qNumber: {
    width: 26,
    height: 26,
    borderRadius: 8,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: 12,
    fontWeight: 700,
    flexShrink: 0,
    transition: 'all 0.2s',
  },

  activeQCard: {
    background: 'linear-gradient(135deg, #ffffff, #f0f9ff)',
    borderColor: '#bfdbfe',
  },
  qBadge: {
    fontSize: 10,
    fontWeight: 700,
    color: '#4fa3e0',
    textTransform: 'uppercase',
    letterSpacing: '0.08em',
    display: 'block',
    marginBottom: 8,
  },
  activeQText: {
    fontSize: 16,
    fontWeight: 600,
    color: '#0f172a',
    lineHeight: 1.6,
  },
  nextQBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: 4,
    marginTop: 12,
    padding: '7px 14px',
    borderRadius: 8,
    border: '1.5px solid #bfdbfe',
    background: 'white',
    color: '#2980c4',
    fontSize: 13,
    fontWeight: 600,
    cursor: 'pointer',
    fontFamily: 'Inter, sans-serif',
  },

  tipsCard: { background: '#fffbeb', borderColor: '#fde68a' },

  // Finished screen
  finishedPage: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: 'calc(100vh - 200px)',
  },
  finishedCard: {
    textAlign: 'center',
    maxWidth: 500,
    padding: 48,
  },
  resultRow: {
    display: 'flex',
    gap: 12,
    justifyContent: 'center',
    flexWrap: 'wrap',
  },
  submitNote: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    justifyContent: 'center',
    marginTop: 16,
    fontSize: 12,
    color: '#64748b',
  },
}