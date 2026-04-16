import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, PieChart, Pie, Cell
} from 'recharts'
import { TrendingUp, Award, Video, Target } from 'lucide-react'

const lineData = [
  { month: 'Jan', score: 60 },
  { month: 'Feb', score: 68 },
  { month: 'Mar', score: 72 },
  { month: 'Apr', score: 78 },
  { month: 'May', score: 85 },
  { month: 'Jun', score: 87 },
]

const pieData = [
  { name: 'React', value: 35 },
  { name: 'Python', value: 25 },
  { name: 'Design', value: 20 },
  { name: 'Other', value: 20 },
]

const COLORS = ['#4fa3e0', '#2980c4', '#93c5fd', '#bfdbfe']

const recentActivity = [
  { date: 'Jun 12', job: 'Frontend Dev @ Google', score: 92, status: 'Passed' },
  { date: 'Jun 10', job: 'React Dev @ Meta', score: 87, status: 'Passed' },
  { date: 'Jun 8', job: 'UI Engineer @ Apple', score: 74, status: 'Pending' },
  { date: 'Jun 5', job: 'Full Stack @ Stripe', score: 65, status: 'Failed' },
]

const statusColor = {
  Passed: { bg: '#dcfce7', color: '#16a34a' },
  Pending: { bg: '#fef9c3', color: '#ca8a04' },
  Failed: { bg: '#fee2e2', color: '#dc2626' },
}

function StatCard({ icon, label, value, change, positive }) {
  return (
    <div className="card" style={styles.statCard}>
      <div style={styles.statTop}>
        <div style={styles.statIconWrap}>{icon}</div>
        <span style={{
          fontSize: 12,
          color: positive ? '#16a34a' : '#ca8a04',
          fontWeight: 500,
          background: positive ? '#dcfce7' : '#fef9c3',
          padding: '3px 8px',
          borderRadius: 99,
        }}>
          {change}
        </span>
      </div>
      <p style={styles.statValue}>{value}</p>
      <p style={styles.statLabel}>{label}</p>
    </div>
  )
}

export default function Dashboard() {
  return (
    <div>
      {/* Header */}
      <div style={{ marginBottom: 28 }}>
        <h1 style={styles.pageTitle}>Good morning, Mariam 👋</h1>
        <p style={{ color: '#64748b', fontSize: 14, marginTop: 4 }}>
          Here's what's happening with your job search today.
        </p>
      </div>

      {/* Overview Cards */}
      <div style={styles.cardsGrid}>
        <StatCard
          icon={<Award size={22} color="#4fa3e0" />}
          label="CV Score"
          value="87/100"
          change="+5 this week"
          positive
        />
        <StatCard
          icon={<Video size={22} color="#4fa3e0" />}
          label="Interviews Done"
          value="12"
          change="+2 this week"
          positive
        />
        <StatCard
          icon={<Target size={22} color="#4fa3e0" />}
          label="Performance"
          value="94%"
          change="+8% vs last month"
          positive
        />
        <StatCard
          icon={<TrendingUp size={22} color="#4fa3e0" />}
          label="Jobs Applied"
          value="28"
          change="4 pending review"
          positive={false}
        />
      </div>

      {/* Charts Row */}
      <div style={styles.chartsRow}>
        {/* Line chart */}
        <div className="card" style={{ flex: 2 }}>
          <h3 style={styles.cardTitle}>CV Score Progress</h3>
          <p style={styles.cardSub}>Your improvement over the last 6 months</p>
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
        </div>

        {/* Pie chart */}
        <div className="card" style={{ flex: 1 }}>
          <h3 style={styles.cardTitle}>Skills Breakdown</h3>
          <p style={styles.cardSub}>Top skills detected in your CV</p>
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
                <div style={{ ...styles.legendDot, background: COLORS[i] }} />
                <span style={{ fontSize: 12, color: '#64748b' }}>{entry.name}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Activity Table */}
      <div className="card" style={{ marginTop: 24 }}>
        <h3 style={styles.cardTitle}>Recent Activity</h3>
        <p style={{ ...styles.cardSub, marginBottom: 16 }}>Your latest interview sessions</p>
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
                <td style={styles.td}>{row.job}</td>
                <td style={styles.td}>
                  <span style={styles.scoreChip}>{row.score}%</span>
                </td>
                <td style={styles.td}>
                  <span style={{
                    ...styles.statusChip,
                    background: statusColor[row.status].bg,
                    color: statusColor[row.status].color,
                  }}>
                    {row.status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
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
