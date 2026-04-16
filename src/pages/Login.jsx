import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Zap, Eye, EyeOff } from 'lucide-react'

export default function Login() {
  const [isLogin, setIsLogin] = useState(true)
  const [showPass, setShowPass] = useState(false)
  const navigate = useNavigate()

  const handleSubmit = (e) => {
    e.preventDefault()
    navigate('/dashboard')
  }

  return (
    <div style={styles.page}>
      {/* Background blobs */}
      <div style={styles.blob1} />
      <div style={styles.blob2} />

      {/* Card */}
      <div style={styles.card} className="glass">
        {/* Logo */}
        <div style={styles.logoRow}>
          <div style={styles.logoIcon}>
            <Zap size={22} color="white" />
          </div>
          <span style={styles.logoText}>RecruitAI</span>
        </div>

        <h2 style={styles.title}>
          {isLogin ? 'Welcome back 👋' : 'Create account 🚀'}
        </h2>
        <p style={styles.subtitle}>
          {isLogin ? 'Sign in to your account' : 'Start your AI recruitment journey'}
        </p>

        <form onSubmit={handleSubmit} style={styles.form}>
          {!isLogin && (
            <div style={styles.field}>
              <label style={styles.label}>Full Name</label>
              <input
                className="input-field"
                type="text"
                placeholder="Mariam Samir"
                required
              />
            </div>
          )}

          <div style={styles.field}>
            <label style={styles.label}>Email</label>
            <input
              className="input-field"
              type="email"
              placeholder="mariam@example.com"
              required
            />
          </div>

          <div style={styles.field}>
            <label style={styles.label}>Password</label>
            <div style={{ position: 'relative' }}>
              <input
                className="input-field"
                type={showPass ? 'text' : 'password'}
                placeholder="••••••••"
                required
                style={{ paddingRight: 44 }}
              />
              <button
                type="button"
                onClick={() => setShowPass(!showPass)}
                style={styles.eyeBtn}
              >
                {showPass ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>

          {isLogin && (
            <p style={styles.forgot}>Forgot password?</p>
          )}

          <button className="btn-primary" type="submit" style={{ width: '100%', marginTop: 8 }}>
            {isLogin ? 'Sign In' : 'Create Account'}
          </button>
        </form>

        {/* Divider */}
        <div style={styles.divider}>
          <hr style={styles.line} />
          <span style={styles.orText}>or continue with</span>
          <hr style={styles.line} />
        </div>

        {/* Social buttons */}
        <div style={styles.socialRow}>
          <button style={styles.socialBtn}> Google</button>
          <button style={styles.socialBtn}> LinkedIn</button>
        </div>

        {/* Toggle */}
        <p style={styles.toggle}>
          {isLogin ? "Don't have an account? " : 'Already have an account? '}
          <span
            onClick={() => setIsLogin(!isLogin)}
            style={styles.toggleLink}
          >
            {isLogin ? 'Sign up' : 'Sign in'}
          </span>
        </p>
      </div>
    </div>
  )
}

const styles = {
  page: {
    minHeight: '100vh',
    background: 'linear-gradient(135deg, #dbeafe 0%, #eff6ff 50%, #e0f2fe 100%)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    position: 'relative',
    overflow: 'hidden',
  },
  blob1: {
    position: 'absolute',
    width: 400,
    height: 400,
    background: 'rgba(79,163,224,0.15)',
    borderRadius: '50%',
    top: -100,
    right: -100,
    filter: 'blur(60px)',
  },
  blob2: {
    position: 'absolute',
    width: 350,
    height: 350,
    background: 'rgba(79,163,224,0.1)',
    borderRadius: '50%',
    bottom: -80,
    left: -80,
    filter: 'blur(60px)',
  },
  card: {
    width: '100%',
    maxWidth: 420,
    borderRadius: 20,
    padding: '40px 36px',
    position: 'relative',
    zIndex: 1,
    boxShadow: '0 8px 48px rgba(0,0,0,0.1)',
  },
  logoRow: {
    display: 'flex',
    alignItems: 'center',
    gap: 10,
    marginBottom: 28,
    justifyContent: 'center',
  },
  logoIcon: {
    width: 38,
    height: 38,
    background: '#4fa3e0',
    borderRadius: 10,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  logoText: {
    fontSize: 20,
    fontWeight: 700,
    color: '#0f172a',
  },
  title: {
    fontSize: 24,
    fontWeight: 700,
    color: '#0f172a',
    textAlign: 'center',
    marginBottom: 6,
  },
  subtitle: {
    fontSize: 14,
    color: '#64748b',
    textAlign: 'center',
    marginBottom: 28,
  },
  form: {
    display: 'flex',
    flexDirection: 'column',
    gap: 16,
  },
  field: {
    display: 'flex',
    flexDirection: 'column',
    gap: 6,
  },
  label: {
    fontSize: 13,
    fontWeight: 600,
    color: '#374151',
  },
  eyeBtn: {
    position: 'absolute',
    right: 12,
    top: '50%',
    transform: 'translateY(-50%)',
    background: 'none',
    border: 'none',
    cursor: 'pointer',
    color: '#94a3b8',
    display: 'flex',
  },
  forgot: {
    fontSize: 13,
    color: '#4fa3e0',
    textAlign: 'right',
    cursor: 'pointer',
    fontWeight: 500,
  },
  divider: {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
    margin: '20px 0',
  },
  line: {
    flex: 1,
    border: 'none',
    borderTop: '1px solid #e2e8f0',
  },
  orText: {
    fontSize: 12,
    color: '#94a3b8',
    whiteSpace: 'nowrap',
  },
  socialRow: {
    display: 'flex',
    gap: 12,
  },
  socialBtn: {
    flex: 1,
    padding: '10px',
    borderRadius: 10,
    border: '1.5px solid #e2e8f0',
    background: 'white',
    cursor: 'pointer',
    fontSize: 13,
    fontWeight: 600,
    fontFamily: 'Inter, sans-serif',
    transition: 'all 0.2s',
  },
  toggle: {
    textAlign: 'center',
    fontSize: 13,
    color: '#64748b',
    marginTop: 20,
  },
  toggleLink: {
    color: '#4fa3e0',
    fontWeight: 600,
    cursor: 'pointer',
  },
}
