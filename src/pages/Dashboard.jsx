import { useEffect, useState } from 'react'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, PieChart, Pie, Cell
} from 'recharts'
import { TrendingUp, Award, Video, Target, Loader } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'

const BACKEND = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const COLORS = ['#4fa3e0', '#2980c4', '#93c5fd', '#bfdbfe', '#7dd3fc', '#38bdf8', '#0ea5e9', '#0284c7']

const statusColor = {
  Passed: { bg: '#dcfce7', color: '#16a34a' },
  Pending: { bg: '#fef9c3', color: '#ca8a04' },
  Failed: { bg: '#fee2e2', color: '#dc2626' },
}

function StatCard({ icon, label, value, sublabel }) {
  return (
    <div className="card" style={styles.statCard}>
      <div style={styles.statTop}>
        <div style={styles.statIconWrap}>{icon}</div>
      </div>
      <p style={styles.statValue}>{value}</p>
      <p style={styles.statLabel}>{label}</p>
      {sublabel && <p style={styles.statSublabel}>{sublabel}</p>}
    </div>
  )
}

export default function Dashboard() {
  const { user, loading: userLoading, getToken } = useAuth()
  const firstName = userLoading
    ? ''
    : (user?.full_name?.split(' ')[0] || user?.email?.split('@')[0] || 'there')

  const [stats, setStats] = useState(null)
  const [statsLoading, setStatsLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    async function loadDashboard() {
      if (userLoading || !user) return
      setStatsLoading(true)
      setError(null)
      try {
        const token = getToken()
        const res = await fetch(`${BACKEND}/api/v1/users/dashboard`, {
          headers: { Authorization: `Bearer ${token}` },
        })
        if (!res.ok) throw new Error(`Failed to load dashboard (${res.status})`)
        setStats(await res.json())
      } catch (e) {
        console.warn('[Dashboard] failed to load stats:', e)
        setError('Could not load your latest stats. Showing what we have.')
      } finally {
        setStatsLoading(false)
      }
    }
    loadDashboard()
  }, [userLoading, user, getToken])

  const lineData = (stats?.score_trend || []).map((p) => ({ month: p.date, score: p.score }))
  const pieData = (stats?.skills_breakdown || []).map((s) => ({ name: s.name, value: s.value }))
  const recentActivity = stats?.recent_activity || []

  return (
    <div>
      {/* Header */}
      <div style={{ marginBottom: 28 }}>
        <h1 style={styles.pageTitle}>
          {userLoading ? 'Good morning 👋' : `Good morning, ${firstName} 👋`}
        </h1>
        <p style={{ color: '#64748b', fontSize: 14, marginTop: 4 }}>
          Here's what's happening with your job search today.
        </p>
      </div>

      {error && <div style={styles.errorBanner}>{error}</div>}

      {statsLoading ? (
        <div style={styles.loadingRow}>
          <Loader size={18} style={{ animation: 'spin 1s linear infinite' }} />
          <span>Loading your dashboard…</span>
          <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
        </div>
      ) : (
        <>
          {/* Overview Cards */}
          <div style={styles.cardsGrid}>
            <StatCard
              icon={<Award size={22} color="#4fa3e0" />}
              label="CV Score"
              value={stats?.cv_score != null ? `${Math.round(stats.cv_score)}/100` : 'N/A'}
              sublabel={stats?.cv_score == null ? 'Upload a CV to get scored' : undefined}
            />
            <StatCard
              icon={<Video size={22} color="#4fa3e0" />}
              label="Interviews Done"
              value={stats?.interviews_done ?? 0}
            />
            <StatCard
              icon={<Target size={22} color="#4fa3e0" />}
              label="Performance"
              value={stats?.performance != null ? `${stats.performance}%` : 'N/A'}
              sublabel={stats?.performance == null ? 'Complete an interview to see this' : undefined}
            />
            <StatCard
              icon={<TrendingUp size={22} color="#4fa3e0" />}
              label="Jobs Applied"
              value={stats?.jobs_applied != null ? stats.jobs_applied : 'N/A'}
              sublabel={stats?.jobs_applied == null ? 'Not tracked yet' : undefined}
            />
          </div>

          {/* Charts Row */}
          <div style={styles.chartsRow}>
            {/* Line chart */}
            <div className="card" style={{ flex: 2 }}>
              <h3 style={styles.cardTitle}>CV Score Progress</h3>
              <p style={styles.cardSub}>Your uploaded CV scores over time</p>
              {lineData.length > 0 ? (
                <ResponsiveContainer width="100%" height={220}>
                  <LineChart data={lineData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                    <XAxis dataKey="month" tick={{ fontSize: 12, fill: '#94a3b8' }} />
                    <YAxis tick={{ fontSize: 12, fill: '#94a3b8' }} />
                    <Tooltip
                      contentStyle={{
                        borderRadius: 10,
                        border: '1px solid #e2e8f0',
                        fontSize: 13,
                      }}
                    />
                    <Line
                      type="monotone"
                      dataKey="score"
                      stroke="#4fa3e0"
                      strokeWidth={3}
                      dot={{ fill: '#4fa3e0', r: 5 }}
                      activeDot={{ r: 7 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <p style={styles.emptyState}>Upload a CV to start tracking your score over time.</p>
              )}
            </div>

            {/* Pie chart */}
            <div className="card" style={{ flex: 1 }}>
              <h3 style={styles.cardTitle}>Skills Breakdown</h3>
              <p style={styles.cardSub}>Top skills detected in your latest CV</p>
              {pieData.length > 0 ? (
                <>
                  <ResponsiveContainer width="100%" height={180}>
                    <PieChart>
                      <Pie
                        data={pieData}
                        cx="50%"
                        cy="50%"
                        innerRadius={50}
                        outerRadius={80}
                        dataKey="value"
                      >
                        {pieData.map((entry, index) => (
                          <Cell key={index} fill={COLORS[index % COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 8 }}>
                    {pieData.map((entry, i) => (
                      <div key={i} style={styles.legendItem}>
                        <div style={{ ...styles.legendDot, background: COLORS[i % COLORS.length] }} />
                        <span style={{ fontSize: 12, color: '#64748b' }}>{entry.name}</span>
                      </div>
                    ))}
                  </div>
                </>
              ) : (
                <p style={styles.emptyState}>No skills detected yet — upload a CV first.</p>
              )}
            </div>
          </div>

          {/* Activity Table */}
          <div className="card" style={{ marginTop: 24 }}>
            <h3 style={styles.cardTitle}>Recent Activity</h3>
            <p style={{ ...styles.cardSub, marginBottom: 16 }}>Your latest interview sessions</p>
            {recentActivity.length > 0 ? (
              <table style={styles.table}>
                <thead>
                  <tr>
                    {['Date', 'Job Position', 'AI Score', 'Status'].map((h) => (
                      <th key={h} style={styles.th}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {recentActivity.map((row, i) => (
                    <tr key={i}>
                      <td style={styles.td}>{row.date}</td>
                      <td style={styles.td}>{row.job_title}</td>
                      <td style={styles.td}>
                        <span style={styles.scoreChip}>{row.score != null ? `${row.score}%` : '—'}</span>
                      </td>
                      <td style={styles.td}>
                        <span style={{
                          ...styles.statusChip,
                          background: (statusColor[row.status] || statusColor.Pending).bg,
                          color: (statusColor[row.status] || statusColor.Pending).color,
                        }}>
                          {row.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p style={styles.emptyState}>No interviews yet — start one to see it here.</p>
            )}
          </div>
        </>
      )}
    </div>
  )
}

const styles = {
  pageTitle: { fontSize: 26, fontWeight: 700, color: '#0f172a' },
  cardsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
    gap: 20,
    marginBottom: 24,
  },
  statCard: { padding: 20 },
  statTop: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 12,
  },
  statIconWrap: {
    width: 44,
    height: 44,
    background: '#ebf5ff',
    borderRadius: 12,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  statValue: { fontSize: 28, fontWeight: 700, color: '#0f172a' },
  statLabel: { fontSize: 13, color: '#64748b', marginTop: 2 },
  statSublabel: { fontSize: 11, color: '#94a3b8', marginTop: 4 },
  errorBanner: {
    background: '#fef2f2',
    border: '1px solid #fecaca',
    color: '#dc2626',
    borderRadius: 10,
    padding: '10px 14px',
    fontSize: 13,
    marginBottom: 16,
  },
  loadingRow: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    color: '#64748b',
    fontSize: 14,
    padding: '40px 0',
    justifyContent: 'center',
  },
  emptyState: {
    fontSize: 13,
    color: '#94a3b8',
    textAlign: 'center',
    padding: '24px 0',
  },
  chartsRow: { display: 'flex', gap: 20, flexWrap: 'wrap' },
  cardTitle: { fontSize: 16, fontWeight: 700, color: '#0f172a', marginBottom: 4 },
  cardSub: { fontSize: 13, color: '#94a3b8', marginBottom: 16 },
  legendItem: { display: 'flex', alignItems: 'center', gap: 6 },
  legendDot: { width: 10, height: 10, borderRadius: '50%' },
  table: { width: '100%', borderCollapse: 'collapse' },
  th: {
    textAlign: 'left',
    padding: '10px 14px',
    fontSize: 12,
    fontWeight: 600,
    color: '#94a3b8',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
    borderBottom: '1px solid #e2e8f0',
  },
  td: {
    padding: '13px 14px',
    fontSize: 14,
    color: '#374151',
    borderBottom: '1px solid #f1f5f9',
  },
  scoreChip: {
    background: '#ebf5ff',
    color: '#2980c4',
    padding: '3px 10px',
    borderRadius: 99,
    fontSize: 13,
    fontWeight: 600,
  },
  statusChip: {
    padding: '4px 12px',
    borderRadius: 99,
    fontSize: 12,
    fontWeight: 600,
  },
}
