import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  FileText,
  MessageCircle,
  Video,
  User,
  Zap
} from 'lucide-react'

const navItems = [
  { to: '/dashboard', icon: <LayoutDashboard size={20} />, label: 'Dashboard' },
  { to: '/cv-upload', icon: <FileText size={20} />, label: 'CV Upload' },
  { to: '/chatbot', icon: <MessageCircle size={20} />, label: 'AI Chat' },
  { to: '/interview', icon: <Video size={20} />, label: 'Interview' },
  { to: '/profile', icon: <User size={20} />, label: 'Profile' },
]

export default function Sidebar() {
  return (
    <aside style={styles.sidebar}>
      {/* Logo */}
      <div style={styles.logo}>
        <div style={styles.logoIcon}>
          <Zap size={20} color="white" />
        </div>
        <span style={styles.logoText}>RecruitAI</span>
      </div>

      {/* Nav Items */}
      <nav style={styles.nav}>
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            style={({ isActive }) => ({
              ...styles.navItem,
              ...(isActive ? styles.navItemActive : {}),
            })}
          >
            <span style={{ display: 'flex', alignItems: 'center' }}>
              {item.icon}
            </span>
            <span style={styles.navLabel}>{item.label}</span>
          </NavLink>
        ))}
      </nav>

      {/* Bottom badge */}
      <div style={styles.proBadge}>
        <span style={{ fontSize: 13, fontWeight: 600, color: '#4fa3e0' }}>
          ✦ Pro Plan
        </span>
        <p style={{ fontSize: 11, color: '#94a3b8', marginTop: 2 }}>
          All features unlocked
        </p>
      </div>
    </aside>
  )
}

const styles = {
  sidebar: {
    width: 240,
    minHeight: '100vh',
    background: '#0f172a',
    display: 'flex',
    flexDirection: 'column',
    padding: '20px 12px',
    gap: 4,
    flexShrink: 0,
  },
  logo: {
    display: 'flex',
    alignItems: 'center',
    gap: 10,
    padding: '8px 12px 24px',
  },
  logoIcon: {
    width: 36,
    height: 36,
    background: '#4fa3e0',
    borderRadius: 10,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  logoText: {
    color: 'white',
    fontSize: 18,
    fontWeight: 700,
    letterSpacing: '-0.3px',
  },
  nav: {
    display: 'flex',
    flexDirection: 'column',
    gap: 4,
    flex: 1,
  },
  navItem: {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
    padding: '11px 14px',
    borderRadius: 10,
    color: '#94a3b8',
    textDecoration: 'none',
    fontSize: 14,
    fontWeight: 500,
    transition: 'all 0.2s ease',
  },
  navItemActive: {
    background: '#4fa3e0',
    color: 'white',
  },
  navLabel: {
    whiteSpace: 'nowrap',
  },
  proBadge: {
    background: 'rgba(79,163,224,0.1)',
    borderRadius: 10,
    padding: '12px 14px',
    marginTop: 'auto',
    border: '1px solid rgba(79,163,224,0.2)',
  },
}
