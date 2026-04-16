import { useState, useRef } from 'react'
import { Upload, FileText, CheckCircle, X } from 'lucide-react'

const mockAnalysis = {
  score: 87,
  skills: ['React', 'JavaScript', 'Python', 'Figma', 'Node.js', 'CSS', 'Git'],
  recommendations: [
    'Add measurable achievements to your experience section',
    'Include a professional summary at the top',
    'Add more keywords related to cloud technologies',
    'Consider adding a portfolio or GitHub link',
  ],
  strengths: ['Strong technical skills', 'Clear layout', 'Good work history'],
}

export default function CVUpload() {
  const [file, setFile] = useState(null)
  const [isDragging, setIsDragging] = useState(false)
  const [analyzed, setAnalyzed] = useState(false)
  const [loading, setLoading] = useState(false)
  const inputRef = useRef()

  const handleFile = (f) => {
    setFile(f)
    setAnalyzed(false)
    setLoading(true)
    setTimeout(() => {
      setLoading(false)
      setAnalyzed(true)
    }, 2000)
  }

  const handleDrop = (e) => {
    e.preventDefault()
    setIsDragging(false)
    const f = e.dataTransfer.files[0]
    if (f) handleFile(f)
  }

  return (
    <div>
      <div style={{ marginBottom: 28 }}>
        <h1 style={styles.pageTitle}>CV Upload & Analysis 📄</h1>
        <p style={{ color: '#64748b', fontSize: 14, marginTop: 4 }}>
          Upload your CV and let our AI analyze it instantly.
        </p>
      </div>

      <div style={styles.twoCol}>
        {/* Left — Upload */}
        <div style={{ flex: 1 }}>
          <div
            className="card"
            style={{
              ...styles.dropZone,
              borderColor: isDragging ? '#4fa3e0' : '#cbd5e1',
              background: isDragging ? '#ebf5ff' : '#fafcff',
            }}
            onClick={() => inputRef.current.click()}
            onDragOver={(e) => { e.preventDefault(); setIsDragging(true) }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={handleDrop}
          >
            <input
              ref={inputRef}
              type="file"
              accept=".pdf,.doc,.docx"
              style={{ display: 'none' }}
              onChange={(e) => e.target.files[0] && handleFile(e.target.files[0])}
            />
            <div style={styles.uploadIcon}>
              <Upload size={32} color="#4fa3e0" />
            </div>
            <h3 style={{ fontSize: 16, fontWeight: 600, color: '#0f172a', marginBottom: 6 }}>
              Drop your CV here
            </h3>
            <p style={{ fontSize: 13, color: '#94a3b8', marginBottom: 16 }}>
              Supports PDF, DOC, DOCX — Max 10MB
            </p>
            <button className="btn-primary" type="button" style={{ pointerEvents: 'none' }}>
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
              {loading ? (
                <span style={styles.analyzingBadge}>🔄 Analyzing...</span>
              ) : (
                <CheckCircle size={20} color="#16a34a" />
              )}
              <button
                onClick={() => { setFile(null); setAnalyzed(false) }}
                style={styles.removeBtn}
              >
                <X size={14} />
              </button>
            </div>
          )}
        </div>

        {/* Right — Results */}
        <div style={{ flex: 1 }}>
          {!analyzed ? (
            <div className="card" style={styles.emptyResults}>
              <div style={{ fontSize: 48, marginBottom: 12 }}>📊</div>
              <p style={{ fontWeight: 600, color: '#0f172a', marginBottom: 6 }}>
                No Analysis Yet
              </p>
              <p style={{ fontSize: 13, color: '#94a3b8' }}>
                Upload your CV to see AI-powered results
              </p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              {/* Score Card */}
              <div className="card" style={styles.scoreCard}>
                <div style={styles.scoreCircle}>
                  <span style={styles.scoreNumber}>{mockAnalysis.score}</span>
                  <span style={styles.scoreMax}>/100</span>
                </div>
                <div>
                  <h3 style={{ fontWeight: 700, fontSize: 18, color: '#0f172a' }}>
                    Great CV! 🎉
                  </h3>
                  <p style={{ fontSize: 13, color: '#64748b', marginTop: 4 }}>
                    Your CV is above average. A few tweaks can push it further.
                  </p>
                </div>
              </div>

              {/* Skills */}
              <div className="card">
                <h3 style={styles.sectionTitle}>Detected Skills</h3>
                <div style={{ marginTop: 10 }}>
                  {mockAnalysis.skills.map((s) => (
                    <span key={s} className="skill-tag">{s}</span>
                  ))}
                </div>
              </div>

              {/* Recommendations */}
              <div className="card">
                <h3 style={styles.sectionTitle}>💡 Recommendations</h3>
                <ul style={styles.recList}>
                  {mockAnalysis.recommendations.map((r, i) => (
                    <li key={i} style={styles.recItem}>
                      <span style={styles.recDot} />
                      {r}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}
        </div>
      </div>
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
}
