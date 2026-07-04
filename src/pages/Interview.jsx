import { useState, useRef, useEffect } from 'react'
import { useCV } from '../contexts/CVContext'
import {
  Circle, Video, VideoOff, Mic, MicOff, ChevronRight,
  Clock, CheckCircle, Download, Loader, AlertCircle, RotateCcw,
} from 'lucide-react'

// Each question gets a 10-minute countdown. When it hits 0 the answer is
// auto-submitted and further recording is locked out for that question.
const PER_QUESTION_SECONDS = 10 * 60 // 10 minutes

const BACKEND = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const FRAME_INTERVAL = 350

// Scores come from the backend as raw floats (e.g. 6.369319915771484).
// Round to 2 decimal places for display only — the underlying value is
// left untouched everywhere else (state, API payloads, etc.).
function formatScore(score) {
  const n = Number(score)
  return Number.isFinite(n) ? n.toFixed(2) : '—'
}

function authFetch(path, opts = {}) {
  const token = localStorage.getItem('access_token')
  const isFormData = opts.body instanceof FormData
  return fetch(`${BACKEND}${path}`, {
    ...opts,
    headers: {
      ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(opts.headers || {}),
    },
  })
}

export default function Interview() {
  // ─── Session-level state ────────────────────────────────────────
  // idle -> countdown -> recording -> processing -> reviewed -> ... -> completed
  const [phase, setPhase] = useState('idle')
  const [countdown, setCountdown] = useState(3)
  const [currentQ, setCurrentQ] = useState(0)
  const [camOn, setCamOn] = useState(true)
  const [micOn, setMicOn] = useState(true)
  const [seconds, setSeconds] = useState(0) // elapsed time for the *current* question only

  // Questions
  const [questions, setQuestions] = useState([])
  const [questionsLoading, setQuestionsLoading] = useState(true)
  const { getAnalysisData } = useCV()

  // Per-question results: { [index]: { transcript, score, feedback, status } }
  // status: 'recording' | 'transcribing' | 'evaluating' | 'done' | 'error'
  const [results, setResults] = useState({})
  const [finalReport, setFinalReport] = useState(null) // finalize() response
  const [finalizing, setFinalizing] = useState(false)

  // Media
  const videoRef = useRef(null)
  const streamRef = useRef(null)
  const mediaRecorderRef = useRef(null)
  const chunksRef = useRef([])
  const timerRef = useRef(null)
  const countdownRef = useRef(null)
  const questionsFetchedRef = useRef(false)
  const answerUrlsRef = useRef({}) // { [qIndex]: objectURL } — per-question downloadable clip

  // CV (behavioral) analysis
  const canvasRef = useRef(null)
  const frameIntervalRef = useRef(null)
  const sessionIdRef = useRef(null)
  const [faceDetected, setFaceDetected] = useState(false)
  const [cvResults, setCvResults] = useState(null)

  // Start camera preview on mount
  useEffect(() => {
    startCamera()
    return () => stopCamera()
  }, [])

  // Fetch questions once on mount
  useEffect(() => {
    async function fetchQuestions() {
      if (questionsFetchedRef.current) return
      questionsFetchedRef.current = true
      setQuestionsLoading(true)
      const analysis = getAnalysisData()
      const role = analysis?.bestFitRole || 'Software Developer'
      const skills = analysis?.skills?.length ? analysis.skills.join(', ') : 'general programming'

      try {
        const params = new URLSearchParams({ job_title: role, skills })
        const res = await authFetch(`/api/v1/interviews/generate-questions?${params.toString()}`, {
          method: 'POST',
        })
        if (res.ok) {
          const data = await res.json()
          setQuestions(data.questions || [])
        } else {
          console.warn('Failed to fetch questions, status:', res.status)
        }
      } catch (e) {
        console.warn('[Questions] fetch failed:', e)
      } finally {
        setQuestionsLoading(false)
      }
    }
    fetchQuestions()
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

  // Auto-submit the current answer once its 10-minute timer runs out —
  // the candidate can no longer continue recording after this fires.
  useEffect(() => {
    if (phase === 'recording' && seconds >= PER_QUESTION_SECONDS) {
      submitAnswer()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
    clearInterval(frameIntervalRef.current)
  }

  // ─── Interview lifecycle ─────────────────────────────────────────

  async function beginInterview() {
    // Create the interview session up front so every question can be scored against it.
    try {
      const res = await authFetch('/api/v1/interviews/sessions', {
        method: 'POST',
        body: JSON.stringify({ job_title: getAnalysisData()?.bestFitRole || 'General' }),
      })
      if (res.ok) {
        const sess = await res.json()
        sessionIdRef.current = sess.id
        await authFetch(`/api/v1/interviews/sessions/${sess.id}/cv-start`, {
          method: 'POST',
          body: JSON.stringify({ question_text: questions[0] }),
        })
        startFrameCapture(sess.id)
      }
    } catch (e) { console.warn('[CV] session start failed:', e) }

    beginCountdown()
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
        startQuestionRecording()
      }
    }, 1000)
  }

  function startQuestionRecording() {
    chunksRef.current = []
    setSeconds(0)
    setPhase('recording')
    setResults((prev) => ({ ...prev, [currentQ]: { status: 'recording' } }))
    timerRef.current = setInterval(() => setSeconds((s) => s + 1), 1000)

    if (streamRef.current) {
      const mr = new MediaRecorder(streamRef.current)
      mr.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data)
      }
      mr.start(1000)
      mediaRecorderRef.current = mr
    }
  }

  function stopQuestionRecording() {
    return new Promise((resolve) => {
      const mr = mediaRecorderRef.current
      if (!mr || mr.state === 'inactive') {
        resolve(null)
        return
      }
      mr.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' })
        resolve(blob)
      }
      mr.stop()
    })
  }

  /**
   * Stop recording the current question's answer, then run the full
   * pipeline: speech-to-text -> evaluate-answer (BERT score) -> display.
   * This is what actually unlocks the "Next Question" button.
   */
  async function submitAnswer() {
    clearInterval(timerRef.current)
    const qIndex = currentQ
    const blob = await stopQuestionRecording()

    if (blob && blob.size > 0) {
      answerUrlsRef.current[qIndex] = URL.createObjectURL(blob)
    }

    setPhase('processing')
    setResults((prev) => ({ ...prev, [qIndex]: { status: 'transcribing' } }))

    // Step 1: Speech-to-text
    let transcript = ''
    try {
      const formData = new FormData()
      formData.append('file', blob || new Blob(), `answer_q${qIndex}.webm`)
      const sttRes = await authFetch('/api/v1/interviews/speech-to-text', {
        method: 'POST',
        body: formData,
      })
      if (sttRes.ok) {
        const data = await sttRes.json()
        transcript = data.text || ''
      } else {
        let detail = ''
        try {
          const errBody = await sttRes.json()
          detail = errBody?.detail || ''
        } catch (_) { /* body wasn't JSON */ }
        throw new Error(detail || `STT failed (${sttRes.status})`)
      }
    } catch (e) {
      console.warn('[STT] failed:', e)
      setResults((prev) => ({
        ...prev,
        [qIndex]: {
          status: 'error',
          error: e.message && e.message !== 'Failed to fetch'
            ? e.message
            : 'Could not transcribe your answer.',
        },
      }))
      setPhase('reviewed')
      return
    }

    setResults((prev) => ({ ...prev, [qIndex]: { status: 'evaluating', transcript } }))

    // Step 2: Evaluate the answer with the BERT scoring model
    try {
      const evalRes = await authFetch('/api/v1/interviews/evaluate-answer', {
        method: 'POST',
        body: JSON.stringify({
          question: questions[qIndex],
          answer: transcript,
          session_id: sessionIdRef.current,
          question_index: qIndex,
        }),
      })
      if (evalRes.ok) {
        const data = await evalRes.json()

        // Step 3: CV (behavioral) feedback for this question
        let cvFeedback = null
        if (sessionIdRef.current) {
          try {
            const cvRes = await authFetch(
              `/api/v1/interviews/sessions/${sessionIdRef.current}/cv-question-feedback`,
              { method: 'POST' }
            )
            if (cvRes.ok) cvFeedback = await cvRes.json()
          } catch (e) {
            console.warn('[CV] cv-question-feedback failed:', e)
          }
        }

        setResults((prev) => ({
          ...prev,
          [qIndex]: {
            status: 'done',
            transcript,
            score: data.score,
            feedback: data.feedback,
            cvFeedback,
          },
        }))
      } else {
        throw new Error(`Evaluation failed (${evalRes.status})`)
      }
    } catch (e) {
      console.warn('[Evaluate] failed:', e)
      setResults((prev) => ({
        ...prev,
        [qIndex]: { status: 'error', transcript, error: 'Could not score your answer.' },
      }))
    } finally {
      setPhase('reviewed')
    }
  }

  /** Re-record the answer to the current question after an error. */
  function retryAnswer() {
    setResults((prev) => ({ ...prev, [currentQ]: undefined }))
    startQuestionRecording()
  }

  /** Locked until the current question has been submitted & evaluated. */
 async function goToNextQuestion() {
    if (currentQ < questions.length - 1) {
      const nextIndex = currentQ + 1
      if (sessionIdRef.current) {
        try {
          await authFetch(
            `/api/v1/interviews/sessions/${sessionIdRef.current}/cv-next-question`,
            {
              method: 'POST',
              body: JSON.stringify({ question_text: questions[nextIndex] }),
            }
          )
        } catch (e) {
          console.warn('[CV] cv-next-question failed:', e)
        }
      }
      setCurrentQ(nextIndex)
      startQuestionRecording()
    } else {
      await finishInterview()
    }
  }

  function startFrameCapture(sid) {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    frameIntervalRef.current = setInterval(() => {
      if (!videoRef.current) return
      ctx.drawImage(videoRef.current, 0, 0, canvas.width, canvas.height)
      const frame = canvas.toDataURL('image/jpeg', 0.85)
      authFetch(`/api/v1/interviews/sessions/${sid}/analyze-frame`, {
        method: 'POST',
        body: JSON.stringify({ frame }),
      }).then(r => r.ok ? r.json() : null)
        .then(d => { if (d) setFaceDetected(!!d.face_detected) })
        .catch(() => {})
    }, FRAME_INTERVAL)
  }

  /** Called once the final question has been evaluated — wraps up the whole session. */
  async function finishInterview() {
    setFinalizing(true)
    clearInterval(frameIntervalRef.current)

    // Aggregate per-question scores into the session's overall score
    if (sessionIdRef.current) {
      try {
        const res = await authFetch(
          `/api/v1/interviews/sessions/${sessionIdRef.current}/finalize`,
          { method: 'POST' }
        )
        if (res.ok) setFinalReport(await res.json())
      } catch (e) { console.warn('[Finalize] failed:', e) }

      // Wrap up the behavioral (CV) analysis too
      try {
        const r = await authFetch(
          `/api/v1/interviews/sessions/${sessionIdRef.current}/cv-end`,
          { method: 'POST' }
        )
        if (r.ok) setCvResults(await r.json())
      } catch (e) { console.warn('[CV] cv-end failed:', e) }
    }

    setFinalizing(false)
    setPhase('completed')
  }

  function downloadAnswer(qIndex) {
    const url = answerUrlsRef.current[qIndex]
    if (!url) return
    const a = document.createElement('a')
    a.href = url
    a.download = `interview-answer-q${qIndex + 1}.webm`
    a.click()
  }

  function restart() {
    setPhase('idle')
    setSeconds(0)
    setCurrentQ(0)
    setResults({})
    setFinalReport(null)
    setCvResults(null)
    setFaceDetected(false)
    sessionIdRef.current = null
    answerUrlsRef.current = {}
    startCamera()
  }

  const formatTime = (s) => {
    const m = Math.floor(s / 60)
    const sec = s % 60
    return `${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`
  }

  const remainingSeconds = Math.max(0, PER_QUESTION_SECONDS - seconds)
  const currentResult = results[currentQ]
  const isCurrentDone = currentResult?.status === 'done'
  const isCurrentError = currentResult?.status === 'error'
  const totalQuestions = questions.length
  const progressPct = totalQuestions ? ((currentQ + (isCurrentDone ? 1 : 0)) / totalQuestions) * 100 : 0

  // ─── FINAL REPORT SCREEN ─────────────────────────────────────────
  if (phase === 'completed') {
    const scoredQuestions = finalReport?.questions || []
    return (
      <div style={styles.finishedPage}>
        <div className="card" style={styles.finishedCard}>
          <div style={{ fontSize: 56, marginBottom: 12 }}>🎉</div>
          <h2 style={{ fontSize: 24, fontWeight: 700, color: '#0f172a', marginBottom: 8 }}>
            Interview Complete!
          </h2>
          <p style={{ color: '#64748b', fontSize: 15, marginBottom: 24 }}>
            Every question has been recorded, transcribed, and scored.
          </p>
          <div style={styles.resultRow}>
            <ResultChip label="Questions" value={totalQuestions} />
            <ResultChip label="Overall Score"
              value={finalReport?.overall_score != null ? `${formatScore(finalReport.overall_score)}/10` : '—'} />
          </div>

          {/* Per-question score breakdown */}
          {scoredQuestions.length > 0 && (
            <div style={{ marginTop: 24, textAlign: 'left' }}>
              <p style={{ fontSize: 13, fontWeight: 600, marginBottom: 10, color: '#0f172a' }}>
                Question-by-Question Scores
              </p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {scoredQuestions.map((q) => (
                  <div key={q.question_index} style={styles.qScoreRow}>
                    <span style={{ fontSize: 13, color: '#374151', flex: 1 }}>
                      Q{q.question_index + 1}. {q.question_text}
                    </span>
                    <span style={styles.qScoreChip}>
                      {q.score != null ? `${formatScore(q.score)}/10` : '—'}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div style={{ display: 'flex', gap: 12, marginTop: 28, justifyContent: 'center', flexWrap: 'wrap' }}>
            <button className="btn-outline" onClick={restart}>
              Start New Interview
            </button>
          </div>

          <div style={styles.submitNote}>
            <CheckCircle size={14} color="#16a34a" />
            <span>Recordings, transcripts, and scores saved to your profile</span>
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
          One question at a time — record, get scored, then move on.
        </p>
      </div>

      {/* Progress indicator */}
      {phase !== 'idle' && totalQuestions > 0 && (
        <div style={styles.progressWrap}>
          <div style={styles.progressTrack}>
            <div style={{ ...styles.progressFill, width: `${progressPct}%` }} />
          </div>
          <div style={styles.progressLabels}>
            <span style={{ fontSize: 12, fontWeight: 600, color: '#0f172a' }}>
              Question {currentQ + 1} / {totalQuestions}
            </span>
            {phase === 'recording' && (
              <span style={{
                fontSize: 12,
                fontWeight: 600,
                color: remainingSeconds <= 30 ? '#ef4444' : '#94a3b8',
              }}>
                <Clock size={11} style={{ marginRight: 4, verticalAlign: 'middle' }} />
                Time remaining: {formatTime(remainingSeconds)}
              </span>
            )}
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
                  REC {formatTime(remainingSeconds)}
                </span>
              </div>
            )}

            {/* Face detection ring */}
            {phase === 'recording' && (
              <div style={{
                position: 'absolute', top: '50%', left: '50%',
                transform: 'translate(-50%, -50%)',
                width: 190, height: 190, borderRadius: '50%',
                border: `2px solid ${faceDetected ? 'rgba(34,197,94,0.85)' : 'rgba(255,255,255,0.18)'}`,
                boxShadow: faceDetected ? '0 0 24px rgba(34,197,94,0.3)' : 'none',
                transition: 'border-color .3s, box-shadow .3s',
                pointerEvents: 'none', zIndex: 4,
              }} />
            )}

            {/* Hidden canvas for frame capture */}
            <canvas ref={canvasRef} width={640} height={480} style={{ display: 'none' }} />

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

          {/* Main action button(s) */}
          {phase === 'idle' && (
            <button
              onClick={beginInterview}
              style={styles.startBtn}
              disabled={questionsLoading || questions.length === 0}
            >
              <Circle size={18} color="white" />
              {questionsLoading ? 'Loading Questions…' : 'Start Interview'}
            </button>
          )}

          {phase === 'recording' && (
            <button
              onClick={submitAnswer}
              style={{ ...styles.stopBtn, opacity: remainingSeconds <= 0 ? 0.7 : 1 }}
              disabled={remainingSeconds <= 0}
            >
              <Circle size={18} color="white" fill="white" />
              {remainingSeconds <= 0 ? "Time's up — submitting…" : 'Stop & Submit Answer'}
            </button>
          )}

          {phase === 'processing' && (
            <button style={{ ...styles.stopBtn, opacity: 0.7, cursor: 'default' }} disabled>
              <Loader size={16} style={{ animation: 'spin 1s linear infinite' }} />
              Scoring your answer…
            </button>
          )}
        </div>

        {/* RIGHT — Current question only */}
        <div style={styles.rightCol}>
          <div className="card" style={styles.activeQCard}>
            <span style={styles.qBadge}>
              Question {currentQ + 1} of {totalQuestions || '—'}
            </span>
            <p style={styles.activeQText}>
              {questionsLoading ? 'Loading your personalized questions…' : questions[currentQ]}
            </p>

            {/* Processing state */}
            {phase === 'processing' && (
              <div style={styles.processingBox}>
                <Loader size={16} style={{ animation: 'spin 1s linear infinite' }} color="#4fa3e0" />
                <span>
                  {currentResult?.status === 'transcribing' && 'Transcribing your answer…'}
                  {currentResult?.status === 'evaluating' && 'Scoring with the BERT model…'}
                  {!currentResult && 'Processing…'}
                </span>
              </div>
            )}

            {/* Error state — allow retry */}
            {phase === 'reviewed' && isCurrentError && (
              <div style={styles.errorBox}>
                <AlertCircle size={16} color="#dc2626" />
                <span>{currentResult.error}</span>
                <button onClick={retryAnswer} style={styles.retryBtn}>
                  <RotateCcw size={13} /> Retry
                </button>
              </div>
            )}

            {/* Score + feedback once evaluated */}
            {phase === 'reviewed' && isCurrentDone && (
              <div style={styles.scoreBox}>
                <div style={styles.scoreBoxTop}>
                  <span style={styles.scoreBadgeNum}>{formatScore(currentResult.score)}/10</span>
                  <span style={styles.scoreBadgeLabel}>{currentResult.feedback}</span>
                </div>
                {currentResult.transcript && (
                  <p style={styles.transcriptText}>
                    "{currentResult.transcript}"
                  </p>
                )}

                {currentResult.cvFeedback && (
                  <div style={{
                    marginTop: 14,
                    paddingTop: 14,
                    borderTop: '1px solid #e2e8f0',
                  }}>
                    <p style={{ fontSize: 12, fontWeight: 700, color: '#4fa3e0', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 6 }}>
                      📹 Behavioral Feedback
                    </p>
                    <p style={{ fontSize: 13, color: '#374151', lineHeight: 1.6 }}>
                      {currentResult.cvFeedback.full_paragraph}
                    </p>
                  </div>
                )}
              </div>
            )}

            {/* Download this answer's recording */}
            {phase === 'reviewed' && answerUrlsRef.current[currentQ] && (
              <button onClick={() => downloadAnswer(currentQ)} style={styles.downloadBtn}>
                <Download size={13} /> Download This Answer
              </button>
            )}

            {/* Next / Finish — locked until the current answer is evaluated */}
            {phase === 'reviewed' && isCurrentDone && (
              <button onClick={goToNextQuestion} style={styles.nextQBtn} disabled={finalizing}>
                <ChevronRight size={14} />
                {currentQ < totalQuestions - 1
                  ? 'Next Question'
                  : (finalizing ? 'Finalizing…' : 'Finish Interview')}
              </button>
            )}
          </div>

          {/* Tips */}
          <div className="card" style={styles.tipsCard}>
            <p style={{ fontSize: 13, fontWeight: 600, color: '#0f172a', marginBottom: 8 }}>
              💬 Interview Tips
            </p>
            <ul style={{ paddingLeft: 16, fontSize: 13, color: '#64748b', lineHeight: 1.9 }}>
              <li>Use the STAR method (Situation, Task, Action, Result)</li>
              <li>You have up to 10 minutes per question — it auto-submits when time runs out</li>
              <li>Each question unlocks the next only once it's scored</li>
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
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  )
}

function ResultChip({ label, value, sublabel }) {
  return (
    <div style={{
      textAlign: 'center',
      padding: '14px 22px',
      background: '#ebf5ff',
      borderRadius: 12,
      minWidth: 100,
      maxWidth: sublabel ? 220 : undefined,
    }}>
      <p style={{ fontSize: 20, fontWeight: 700, color: '#2980c4' }}>{value}</p>
      <p style={{ fontSize: 12, color: '#64748b', marginTop: 2 }}>{label}</p>
      {sublabel && (
        <p style={{ fontSize: 11, color: '#94a3b8', marginTop: 6, lineHeight: 1.4 }}>
          {sublabel}
        </p>
      )}
    </div>
  )
}

function MiniStat({ label, value }) {
  return (
    <div style={{ background: 'white', borderRadius: 10, padding: '10px 16px',
      textAlign: 'center', minWidth: 100, border: '1px solid #e2e8f0' }}>
      <p style={{ fontSize: 18, fontWeight: 700, color: '#0f172a' }}>{value}</p>
      <p style={{ fontSize: 11, color: '#94a3b8', marginTop: 2 }}>{label}</p>
    </div>
  )
}

const styles = {
  pageTitle: { fontSize: 26, fontWeight: 700, color: '#0f172a' },

  progressWrap: { marginBottom: 20 },
  progressTrack: {
    height: 8,
    background: '#e2e8f0',
    borderRadius: 99,
    overflow: 'hidden',
    marginBottom: 6,
  },
  progressFill: {
    height: '100%',
    borderRadius: 99,
    background: 'linear-gradient(90deg, #4fa3e0, #2980c4)',
    transition: 'width 0.4s ease',
  },
  progressLabels: {
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

  activeQCard: {
    background: 'linear-gradient(135deg, #ffffff, #f0f9ff)',
    borderColor: '#bfdbfe',
    padding: 20,
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
  processingBox: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    marginTop: 14,
    fontSize: 13,
    color: '#4fa3e0',
    fontWeight: 600,
  },
  errorBox: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    marginTop: 14,
    fontSize: 13,
    color: '#dc2626',
    background: '#fef2f2',
    border: '1px solid #fecaca',
    borderRadius: 10,
    padding: '10px 12px',
    flexWrap: 'wrap',
  },
  retryBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: 4,
    marginLeft: 'auto',
    padding: '5px 10px',
    borderRadius: 8,
    border: '1px solid #fecaca',
    background: 'white',
    color: '#dc2626',
    fontSize: 12,
    fontWeight: 600,
    cursor: 'pointer',
  },
  scoreBox: {
    marginTop: 14,
    padding: 14,
    background: 'white',
    borderRadius: 12,
    border: '1px solid #dbeafe',
  },
  scoreBoxTop: {
    display: 'flex',
    alignItems: 'center',
    gap: 10,
    flexWrap: 'wrap',
  },
  scoreBadgeNum: {
    fontSize: 20,
    fontWeight: 800,
    color: '#2980c4',
    background: '#ebf5ff',
    padding: '4px 12px',
    borderRadius: 99,
  },
  scoreBadgeLabel: {
    fontSize: 13,
    fontWeight: 600,
    color: '#0f172a',
  },
  transcriptText: {
    fontSize: 13,
    color: '#64748b',
    marginTop: 10,
    lineHeight: 1.6,
    fontStyle: 'italic',
  },
  downloadBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    marginTop: 12,
    padding: '7px 14px',
    borderRadius: 8,
    border: '1.5px solid #e2e8f0',
    background: 'white',
    color: '#374151',
    fontSize: 13,
    fontWeight: 600,
    cursor: 'pointer',
    fontFamily: 'Inter, sans-serif',
  },
  nextQBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: 4,
    marginTop: 12,
    padding: '10px 16px',
    borderRadius: 8,
    border: 'none',
    background: 'linear-gradient(135deg, #4fa3e0, #2980c4)',
    color: 'white',
    fontSize: 13,
    fontWeight: 700,
    cursor: 'pointer',
    fontFamily: 'Inter, sans-serif',
    boxShadow: '0 2px 10px rgba(79,163,224,0.3)',
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
    maxWidth: 560,
    padding: 48,
  },
  resultRow: {
    display: 'flex',
    gap: 12,
    justifyContent: 'center',
    flexWrap: 'wrap',
  },
  qScoreRow: {
    display: 'flex',
    alignItems: 'center',
    gap: 10,
    padding: '8px 12px',
    background: '#f8fafc',
    borderRadius: 10,
    border: '1px solid #e2e8f0',
  },
  qScoreChip: {
    fontSize: 12,
    fontWeight: 700,
    color: '#2980c4',
    background: '#ebf5ff',
    padding: '3px 10px',
    borderRadius: 99,
    flexShrink: 0,
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