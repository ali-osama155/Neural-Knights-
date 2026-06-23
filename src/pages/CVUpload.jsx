import { useState, useRef, useEffect } from 'react'
import { Upload, FileText, CheckCircle, X, AlertCircle, Loader } from 'lucide-react'
import { useCV } from '../contexts/CVContext'

const MAX_FILE_SIZE_MB = 50
const ALLOWED_EXTENSIONS = ['.pdf', '.doc', '.docx', '.txt']

export default function CVUpload() {
  const { uploadCV, pollAnalysisResults, clearCV, getAnalysisData, loading, error, isPolling, cvData } = useCV()
  const [file, setFile] = useState(null)
  const [isDragging, setIsDragging] = useState(false)
  const [analyzed, setAnalyzed] = useState(false)
  const [validationError, setValidationError] = useState(null)
  const [token, setToken] = useState(localStorage.getItem('token'))
  const inputRef = useRef()

  // Check if user is authenticated
  useEffect(() => {
    // === DEV MODE - Bypass login ===
    const devToken = "dev-test-token"; // or any string
    setToken(devToken);
    setValidationError(null);
    
    // Uncomment below if you still want real login to work
    // const storedToken = localStorage.getItem('token')
    // if (storedToken) {
    //   setToken(storedToken)
    // }
  }, [])
  // Validate file before upload
  const validateFile = (f) => {
    setValidationError(null)

    if (!f) {
      setValidationError('No file selected')
      return false
    }

    // Check file size
    const fileSizeMB = f.size / (1024 * 1024)
    if (fileSizeMB > MAX_FILE_SIZE_MB) {
      setValidationError(`File size exceeds ${MAX_FILE_SIZE_MB}MB limit. Your file: ${fileSizeMB.toFixed(1)}MB`)
      return false
    }

    // Check file type
    const ext = '.' + f.name.split('.').pop().toLowerCase()
    if (!ALLOWED_EXTENSIONS.includes(ext)) {
      setValidationError(`Invalid file type. Allowed: ${ALLOWED_EXTENSIONS.join(', ')}`)
      return false
    }

    return true
  }

  // Handle file upload
  const handleFile = async (f) => {
    if (!validateFile(f)) return
    if (!token) {
      setValidationError('Authentication required')
      return
    }

    setFile(f)
    setAnalyzed(false)

    try {
      // Step 1: Upload file
      await uploadCV(f, token)
      
      // Step 2: Poll for results (max 30 seconds)
      const result = await pollAnalysisResults(token, 60)
      
      // Step 3: Mark as analyzed
      setAnalyzed(true)
    } catch (err) {
      console.error('Upload/analysis error:', err)
      // Error is already set in context
    }
  }

  const handleDrop = (e) => {
    e.preventDefault()
    setIsDragging(false)
    const f = e.dataTransfer.files[0]
    if (f) handleFile(f)
  }

  const handleRemoveFile = () => {
    setFile(null)
    setAnalyzed(false)
    setValidationError(null)
    clearCV()
  }

  const analysisData = getAnalysisData()
  const isProcessing = loading || isPolling

  return (
    <div>
      <div style={{ marginBottom: 28 }}>
        <h1 style={styles.pageTitle}>CV Upload & Analysis 📄</h1>
        <p style={{ color: '#64748b', fontSize: 14, marginTop: 4 }}>
          Upload your CV and let our AI analyze it instantly.
        </p>
      </div>

      {/* Global error message */}
      {error && (
        <div style={styles.errorBanner}>
          <AlertCircle size={18} color="#dc2626" />
          <span>{error}</span>
          <button onClick={() => clearCV()} style={styles.dismissBtn}>×</button>
        </div>
      )}

      {/* Validation error message */}
      {validationError && !token && (
        <div style={styles.errorBanner}>
          <AlertCircle size={18} color="#dc2626" />
          <span>{validationError}</span>
        </div>
      )}

      <div style={styles.twoCol}>
        {/* Left — Upload */}
        <div style={{ flex: 1 }}>
          <div
            className="card"
            style={{
              ...styles.dropZone,
              borderColor: isDragging ? '#4fa3e0' : '#cbd5e1',
              background: isDragging ? '#ebf5ff' : '#fafcff',
              opacity: !token ? 0.6 : 1,
              pointerEvents: !token ? 'none' : 'auto',
            }}
            onClick={() => token && inputRef.current.click()}
            onDragOver={(e) => { e.preventDefault(); setIsDragging(true) }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={handleDrop}
          >
            <input
              ref={inputRef}
              type="file"
              accept={ALLOWED_EXTENSIONS.join(',')}
              style={{ display: 'none' }}
              onChange={(e) => e.target.files[0] && handleFile(e.target.files[0])}
              disabled={!token}
            />
            <div style={styles.uploadIcon}>
              <Upload size={32} color="#4fa3e0" />
            </div>
            <h3 style={{ fontSize: 16, fontWeight: 600, color: '#0f172a', marginBottom: 6 }}>
              {!token ? '🔒 Please Log In' : 'Drop your CV here'}
            </h3>
            <p style={{ fontSize: 13, color: '#94a3b8', marginBottom: 16 }}>
              Supports PDF, DOC, DOCX, TXT — Max {MAX_FILE_SIZE_MB}MB
            </p>
            <button 
              className="btn-primary" 
              type="button" 
              style={{ pointerEvents: 'none' }}
              disabled={!token}
            >
              Browse File
            </button>
          </div>

          {/* File Preview */}
          {file && (
            <div className="card" style={styles.filePreview}>
              <FileText size={24} color="#4fa3e0" />
              <div style={{ flex: 1 }}>
                <p style={{ fontWeight: 600, fontSize: 14, color: '#0f172a' }}>{file.name}</p>
                <p style={{ fontSize: 12, color: '#94a3b8' }}>
                  {(file.size / 1024).toFixed(1)} KB
                </p>
              </div>
              {isProcessing ? (
                <div style={styles.analyzingBadge}>
                  <Loader size={14} style={{ animation: 'spin 1s linear infinite' }} />
                  <span>{isPolling ? 'Analyzing...' : 'Uploading...'}</span>
                </div>
              ) : (
                <CheckCircle size={20} color="#16a34a" />
              )}
              <button
                onClick={handleRemoveFile}
                style={styles.removeBtn}
                disabled={isProcessing}
              >
                <X size={14} />
              </button>
            </div>
          )}

          {/* Validation/File upload errors */}
          {validationError && token && (
            <div style={styles.validationError}>
              <AlertCircle size={16} color="#dc2626" />
              <p>{validationError}</p>
            </div>
          )}
        </div>

        {/* Right — Results */}
        <div style={{ flex: 1 }}>
          {!analyzed ? (
            <div className="card" style={styles.emptyResults}>
              <div style={{ fontSize: 48, marginBottom: 12 }}>📊</div>
              <p style={{ fontWeight: 600, color: '#0f172a', marginBottom: 6 }}>
                {file && isProcessing ? 'Analyzing your CV...' : 'No Analysis Yet'}
              </p>
              <p style={{ fontSize: 13, color: '#94a3b8' }}>
                {file && isProcessing 
                  ? 'This may take a moment. Our AI is extracting skills and scoring your CV.'
                  : 'Upload your CV to see AI-powered results'}
              </p>
              {isProcessing && (
                <div style={{ marginTop: 16 }}>
                  <div style={styles.progressBar}>
                    <div style={styles.progressFill} />
                  </div>
                </div>
              )}
            </div>
          ) : analysisData ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              {/* Score Card */}
              <div className="card" style={styles.scoreCard}>
                <div style={styles.scoreCircle}>
                  <span style={styles.scoreNumber}>{Math.round(analysisData.score)}</span>
                  <span style={styles.scoreMax}>/100</span>
                </div>
                <div>
                  <h3 style={{ fontWeight: 700, fontSize: 18, color: '#0f172a' }}>
                    {analysisData.score >= 80 ? '🎉 Excellent CV!' : analysisData.score >= 60 ? '👍 Good CV' : '📈 Room to improve'}
                  </h3>
                  <p style={{ fontSize: 13, color: '#64748b', marginTop: 4 }}>
                    {analysisData.score >= 80 
                      ? 'Your CV is above average. You\'re well-positioned for opportunities.'
                      : analysisData.score >= 60
                      ? 'Your CV is decent. A few tweaks can make it stronger.'
                      : 'Your CV has potential. Consider the recommendations below.'}
                  </p>
                </div>
              </div>

              {/* Best Fit Role */}
              {analysisData.bestFitRole && (
                <div className="card" style={styles.roleCard}>
                  <div style={styles.roleBadge}>💼</div>
                  <div>
                    <p style={{ fontSize: 12, color: '#64748b', fontWeight: 600, marginBottom: 4 }}>
                      Recommended Role
                    </p>
                    <p style={{ fontSize: 16, fontWeight: 700, color: '#0f172a' }}>
                      {analysisData.bestFitRole}
                    </p>
                  </div>
                </div>
              )}

              {/* Skills */}
              {analysisData.skills.length > 0 && (
                <div className="card">
                  <h3 style={styles.sectionTitle}>✨ Detected Skills</h3>
                  <div style={{ marginTop: 10 }}>
                    {analysisData.skills.map((s, i) => (
                      <span key={i} className="skill-tag">{s}</span>
                    ))}
                  </div>
                </div>
              )}

              {/* Strengths */}
              {analysisData.strengths.length > 0 && (
                <div className="card">
                  <h3 style={styles.sectionTitle}>💪 Your Strengths</h3>
                  <ul style={styles.recList}>
                    {analysisData.strengths.map((s, i) => (
                      <li key={i} style={styles.recItem}>
                        <span style={styles.recDot} />
                        {s}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Recommendations */}
              {analysisData.recommendations.length > 0 && (
                <div className="card">
                  <h3 style={styles.sectionTitle}>💡 Recommendations</h3>
                  <ul style={styles.recList}>
                    {analysisData.recommendations.map((r, i) => (
                      <li key={i} style={styles.recItem}>
                        <span style={styles.recDot} />
                        {r}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Proceed Button */}
              <button 
                style={styles.proceedBtn}
                onClick={() => {
                  // Navigate to interview or next stage
                  window.location.href = '/interview'
                }}
              >
                ✅ Proceed to Interview
              </button>
            </div>
          ) : (
            <div className="card" style={styles.emptyResults}>
              <AlertCircle size={48} color="#dc2626" />
              <p style={{ fontWeight: 600, color: '#0f172a', marginBottom: 6 }}>
                Analysis Failed
              </p>
              <p style={{ fontSize: 13, color: '#94a3b8' }}>
                Please try uploading again or contact support.
              </p>
              <button 
                onClick={handleRemoveFile}
                style={{ marginTop: 12, ...styles.retryBtn }}
              >
                Try Again
              </button>
            </div>
          )}
        </div>
      </div>

      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  )
}

const styles = {
  pageTitle: { fontSize: 26, fontWeight: 700, color: '#0f172a' },
  twoCol: { display: 'flex', gap: 24, flexWrap: 'wrap' },
  
  dropZone: {
    border: '2px dashed',
    borderRadius: 16,
    padding: 48,
    textAlign: 'center',
    cursor: 'pointer',
    transition: 'all 0.2s ease',
    marginBottom: 16,
  },
  
  uploadIcon: {
    width: 68,
    height: 68,
    background: '#ebf5ff',
    borderRadius: '50%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    margin: '0 auto 16px',
  },
  
  filePreview: {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
    padding: 16,
  },
  
  analyzingBadge: {
    fontSize: 12,
    background: '#ebf5ff',
    color: '#2980c4',
    padding: '4px 10px',
    borderRadius: 99,
    fontWeight: 600,
    display: 'flex',
    alignItems: 'center',
    gap: 6,
  },
  
  removeBtn: {
    background: '#fee2e2',
    border: 'none',
    borderRadius: 6,
    color: '#dc2626',
    cursor: 'pointer',
    width: 26,
    height: 26,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    transition: 'background 0.2s',
  },
  
  validationError: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    background: '#fee2e2',
    border: '1px solid #fca5a5',
    borderRadius: 8,
    padding: 12,
    marginTop: 12,
  },
  
  errorBanner: {
    display: 'flex',
    alignItems: 'center',
    gap: 10,
    background: '#fee2e2',
    border: '1px solid #fca5a5',
    borderRadius: 8,
    padding: 12,
    marginBottom: 16,
    color: '#991b1b',
  },
  
  dismissBtn: {
    marginLeft: 'auto',
    background: 'none',
    border: 'none',
    fontSize: 18,
    cursor: 'pointer',
    color: '#dc2626',
  },
  
  emptyResults: {
    textAlign: 'center',
    padding: 60,
  },
  
  scoreCard: {
    display: 'flex',
    alignItems: 'center',
    gap: 20,
    background: 'linear-gradient(135deg, #ebf5ff, #dbeafe)',
    borderColor: '#bfdbfe',
  },
  
  scoreCircle: {
    width: 80,
    height: 80,
    background: '#4fa3e0',
    borderRadius: '50%',
    display: 'flex',
    alignItems: 'baseline',
    justifyContent: 'center',
    flexShrink: 0,
  },
  
  scoreNumber: { fontSize: 26, fontWeight: 700, color: 'white' },
  scoreMax: { fontSize: 12, color: 'rgba(255,255,255,0.7)', marginLeft: 1 },
  
  roleCard: {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
    background: '#f0fdf4',
    borderColor: '#bbf7d0',
    padding: 16,
  },
  
  roleBadge: {
    fontSize: 28,
    flexShrink: 0,
  },
  
  sectionTitle: { fontSize: 15, fontWeight: 700, color: '#0f172a' },
  
  recList: {
    listStyle: 'none',
    display: 'flex',
    flexDirection: 'column',
    gap: 10,
    marginTop: 12,
  },
  
  recItem: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: 10,
    fontSize: 13,
    color: '#374151',
    lineHeight: 1.5,
  },
  
  recDot: {
    width: 7,
    height: 7,
    background: '#4fa3e0',
    borderRadius: '50%',
    flexShrink: 0,
    marginTop: 5,
  },
  
  progressBar: {
    width: '100%',
    height: 4,
    background: '#e2e8f0',
    borderRadius: 2,
    overflow: 'hidden',
  },
  
  progressFill: {
    width: '30%',
    height: '100%',
    background: 'linear-gradient(90deg, #4fa3e0, #2563eb)',
    animation: 'progress 2s ease-in-out infinite',
  },
  
  proceedBtn: {
    width: '100%',
    padding: 14,
    background: 'linear-gradient(135deg, #10b981, #059669)',
    color: 'white',
    border: 'none',
    borderRadius: 8,
    fontSize: 15,
    fontWeight: 600,
    cursor: 'pointer',
    transition: 'all 0.2s',
    marginTop: 8,
  },
  
  retryBtn: {
    padding: 10,
    background: '#4fa3e0',
    color: 'white',
    border: 'none',
    borderRadius: 6,
    fontSize: 13,
    fontWeight: 600,
    cursor: 'pointer',
  },
}

