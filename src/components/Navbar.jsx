import { Bell, Search, ChevronDown } from 'lucide-react'

export default function Navbar() {
  return (
    <header style={styles.navbar}>
      {/* Search */}
      <div style={styles.searchBox}>
        <Search size={16} color="#94a3b8" />
        <input
          type="text"
          placeholder="Search anything..."
          style={styles.searchInput}
        />
      </div>

      {/* Right side */}
      <div style={styles.right}>
        {/* Notification bell */}
        <button style={styles.iconBtn}>
          <Bell size={18} color="#64748b" />
          <span style={styles.badge}>3</span>
        </button>

        {/* User avatar */}
        <div style={styles.user}>
          <div style={styles.avatar}>M</div>
          <div>
            <p style={styles.userName}>Mariam</p>
            <p style={styles.userRole}>Pro Member</p>
          </div>
          <ChevronDown size={14} color="#71a7f2" />
        </div>
      </div>
    </header>
  )
}

const styles = {
  navbar: {
    height: 64,
    background: 'rgba(255,255,255,0.85)',
    backdropFilter: 'blur(12px)',
    borderBottom: '1px solid #e2e8f0',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '0 28px',
    gap: 16,
    flexShrink: 0,
  },
  searchBox: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    background: '#f1f5f9',
    borderRadius: 10,
    padding: '8px 14px',
    minWidth: 280,
  },
  searchInput: {
    border: 'none',
    background: 'transparent',
    outline: 'none',
    fontSize: 14,
    color: '#0f172a',
    fontFamily: 'Inter, sans-serif',
    width: '100%',
  },
  right: {
    display: 'flex',
    alignItems: 'center',
    gap: 16,
  },
  iconBtn: {
    background: '#f1f5f9',
    border: 'none',
    borderRadius: 10,
    width: 38,
    height: 38,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    cursor: 'pointer',
    position: 'relative',
  },
  badge: {
    position: 'absolute',
    top: 6,
    right: 6,
    width: 8,
    height: 8,
    background: '#ef4444',
    borderRadius: '50%',
    border: '1.5px solid white',
  },
  user: {
    display: 'flex',
    alignItems: 'center',
    gap: 10,
    cursor: 'pointer',
    padding: '6px 10px',
    borderRadius: 10,
    transition: 'background 0.2s ease',
  },
  avatar: {
    width: 34,
    height: 34,
    background: '#4fa3e0',
    borderRadius: '50%',
    color: 'white',
    fontWeight: 700,
    fontSize: 15,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  userName: {
    fontSize: 13,
    fontWeight: 600,
    color: '#0f172a',
    lineHeight: 1.2,
  },
  userRole: {
    fontSize: 11,
    color: '#94a3b8',
    lineHeight: 1.2,
  },
}
