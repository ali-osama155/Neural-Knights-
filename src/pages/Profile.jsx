import { useState } from 'react'
import { User, Mail, MapPin, Phone, Shield, CreditCard, Bell } from 'lucide-react'

const tabs = ['Account', 'Subscription', 'Security', 'Notifications']

export default function Profile() {
  const [activeTab, setActiveTab] = useState('Account')
  const [editing, setEditing] = useState(false)
  const [form, setForm] = useState({
    name: 'Mariam Samir',
    email: 'mariam@example.com',
    phone: '+20 100 000 0000',
    location: 'Cairo, Egypt',
    bio: 'Frontend developer passionate about building great user experiences.',
  })

  return (
    <div>
      {/* Header */}
      <div style={{ marginBottom: 28 }}>
        <h1 style={styles.pageTitle}>Profile & Settings ⚙️</h1>
        <p style={{ color: '#64748b', fontSize: 14, marginTop: 4 }}>
          Manage your account, subscription, and preferences.
        </p>
      </div>

      {/* Profile Card */}
      <div className="card" style={styles.profileCard}>
        <div style={styles.avatarLarge}>K</div>
        <div style={{ flex: 1 }}>
          <h2 style={{ fontSize: 20, fontWeight: 700, color: '#0f172a' }}>{form.name}</h2>
          <p style={{ color: '#64748b', fontSize: 14, marginTop: 4 }}>{form.email}</p>
          <div style={styles.tagRow}>
            <span className="skill-tag">Frontend Developer</span>
            <span className="skill-tag">React.js</span>
            <span style={styles.proPill}>✦ Pro Plan</span>
          </div>
        </div>
        <button
          className={editing ? 'btn-outline' : 'btn-primary'}
          onClick={() => setEditing(!editing)}
        >
          {editing ? 'Cancel' : 'Edit Profile'}
        </button>
      </div>

      {/* Tabs */}
      <div style={styles.tabRow}>
        {tabs.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            style={{
              ...styles.tab,
              ...(activeTab === tab ? styles.tabActive : {}),
            }}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === 'Account' && (
        <div className="card" style={{ padding: 28 }}>
          <h3 style={styles.sectionTitle}>Personal Information</h3>
          <div style={styles.formGrid}>
            <FormField
              icon={<User size={16} />}
              label="Full Name"
              value={form.name}
              editing={editing}
              onChange={(v) => setForm({ ...form, name: v })}
            />
            <FormField
              icon={<Mail size={16} />}
              label="Email"
              value={form.email}
              editing={editing}
              onChange={(v) => setForm({ ...form, email: v })}
            />
            <FormField
              icon={<Phone size={16} />}
              label="Phone"
              value={form.phone}
              editing={editing}
              onChange={(v) => setForm({ ...form, phone: v })}
            />
            <FormField
              icon={<MapPin size={16} />}
              label="Location"
              value={form.location}
              editing={editing}
              onChange={(v) => setForm({ ...form, location: v })}
            />
          </div>
          <div style={{ marginTop: 16 }}>
            <label style={styles.label}>Bio</label>
            {editing ? (
              <textarea
                className="input-field"
                rows={3}
                value={form.bio}
                onChange={(e) => setForm({ ...form, bio: e.target.value })}
                style={{ marginTop: 6, resize: 'none' }}
              />
            ) : (
              <p style={styles.fieldValue}>{form.bio}</p>
            )}
          </div>
          {editing && (
            <button
              className="btn-primary"
              style={{ marginTop: 20 }}
              onClick={() => setEditing(false)}
            >
              Save Changes
            </button>
          )}
        </div>
      )}

      {activeTab === 'Subscription' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {/* Current Plan */}
          <div className="card" style={styles.planCard}>
            <div style={styles.planBadge}>Current Plan</div>
            <h3 style={{ fontSize: 22, fontWeight: 700, color: '#0f172a', marginBottom: 4 }}>
              Pro Plan 🚀
            </h3>
            <p style={{ color: '#64748b', fontSize: 14, marginBottom: 20 }}>
              $29/month — Billed monthly
            </p>
            <div style={styles.featureList}>
              {[
                'Unlimited CV uploads & analysis',
                'Unlimited AI interviews',
                'Priority support',
                'Advanced analytics',
                'Export reports as PDF',
              ].map((f) => (
                <div key={f} style={styles.featureItem}>
                  <span style={styles.checkMark}>✓</span>
                  <span style={{ fontSize: 14, color: '#374151' }}>{f}</span>
                </div>
              ))}
            </div>
            <div style={{ display: 'flex', gap: 12, marginTop: 20 }}>
              <button className="btn-primary">Manage Billing</button>
              <button className="btn-outline">Upgrade Plan</button>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'Security' && (
        <div className="card" style={{ padding: 28 }}>
          <h3 style={styles.sectionTitle}>Security Settings</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16, marginTop: 16 }}>
            <SecurityRow
              icon={<Shield size={18} color="#4fa3e0" />}
              title="Two-Factor Authentication"
              desc="Add an extra layer of security to your account"
              action="Enable"
            />
            <SecurityRow
              icon={<CreditCard size={18} color="#4fa3e0" />}
              title="Change Password"
              desc="Update your password regularly for security"
              action="Change"
            />
          </div>
        </div>
      )}

      {activeTab === 'Notifications' && (
        <div className="card" style={{ padding: 28 }}>
          <h3 style={styles.sectionTitle}>Notification Preferences</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16, marginTop: 16 }}>
            {[
              'Email notifications for interview results',
              'CV analysis completion alerts',
              'Weekly performance report',
              'Job match recommendations',
            ].map((item) => (
              <div key={item} style={styles.notifRow}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <Bell size={16} color="#4fa3e0" />
                  <span style={{ fontSize: 14, color: '#374151' }}>{item}</span>
                </div>
                <ToggleSwitch />
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function FormField({ icon, label, value, editing, onChange }) {
  return (
    <div>
      <label style={styles.label}>
        <span style={{ color: '#4fa3e0' }}>{icon}</span> {label}
      </label>
      {editing ? (
        <input
          className="input-field"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          style={{ marginTop: 6 }}
        />
      ) : (
        <p style={styles.fieldValue}>{value}</p>
      )}
    </div>
  )
}

function SecurityRow({ icon, title, desc, action }) {
  return (
    <div style={styles.secRow}>
      <div style={styles.secIcon}>{icon}</div>
      <div style={{ flex: 1 }}>
        <p style={{ fontWeight: 600, fontSize: 14, color: '#0f172a' }}>{title}</p>
        <p style={{ fontSize: 12, color: '#64748b', marginTop: 2 }}>{desc}</p>
      </div>
      <button className="btn-outline" style={{ padding: '8px 16px', fontSize: 13 }}>
        {action}
      </button>
    </div>
  )
}

function ToggleSwitch() {
  const [on, setOn] = useState(true)
  return (
    <div
      onClick={() => setOn(!on)}
      style={{
        width: 44,
        height: 24,
        borderRadius: 99,
        background: on ? '#4fa3e0' : '#e2e8f0',
        cursor: 'pointer',
        position: 'relative',
        transition: 'background 0.2s',
        flexShrink: 0,
      }}
    >
      <div style={{
        width: 18,
        height: 18,
        background: 'white',
        borderRadius: '50%',
        position: 'absolute',
        top: 3,
        left: on ? 23 : 3,
        transition: 'left 0.2s',
        boxShadow: '0 1px 4px rgba(0,0,0,0.15)',
      }} />
    </div>
  )
}

const styles = {
  pageTitle: { fontSize: 26, fontWeight: 700, color: '#0f172a' },
  profileCard: {
    display: 'flex',
    alignItems: 'center',
    gap: 20,
    marginBottom: 24,
    padding: 24,
    flexWrap: 'wrap',
  },
  avatarLarge: {
    width: 72,
    height: 72,
    background: 'linear-gradient(135deg, #4fa3e0, #2980c4)',
    borderRadius: '50%',
    color: 'white',
    fontSize: 28,
    fontWeight: 700,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
    boxShadow: '0 4px 16px rgba(79,163,224,0.3)',
  },
  tagRow: { display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 10, alignItems: 'center' },
  proPill: {
    background: 'linear-gradient(135deg, #dbeafe, #bfdbfe)',
    color: '#2980c4',
    padding: '4px 12px',
    borderRadius: 99,
    fontSize: 13,
    fontWeight: 700,
  },
  tabRow: {
    display: 'flex',
    gap: 4,
    background: '#f1f5f9',
    borderRadius: 12,
    padding: 4,
    marginBottom: 20,
    flexWrap: 'wrap',
  },
  tab: {
    padding: '9px 20px',
    borderRadius: 9,
    border: 'none',
    background: 'transparent',
    fontSize: 14,
    fontWeight: 500,
    color: '#64748b',
    cursor: 'pointer',
    fontFamily: 'Inter, sans-serif',
    transition: 'all 0.2s',
  },
  tabActive: {
    background: 'white',
    color: '#0f172a',
    fontWeight: 700,
    boxShadow: '0 1px 4px rgba(0,0,0,0.08)',
  },
  sectionTitle: { fontSize: 16, fontWeight: 700, color: '#0f172a', marginBottom: 4 },
  formGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
    gap: 20,
    marginTop: 16,
  },
  label: {
    fontSize: 12,
    fontWeight: 600,
    color: '#374151',
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    marginBottom: 4,
  },
  fieldValue: {
    fontSize: 14,
    color: '#0f172a',
    padding: '11px 14px',
    background: '#f8fafc',
    borderRadius: 10,
    border: '1px solid #e2e8f0',
    marginTop: 6,
  },
  planCard: {
    background: 'linear-gradient(135deg, #f0f9ff, #e0f2fe)',
    borderColor: '#7dd3fc',
    padding: 28,
    position: 'relative',
  },
  planBadge: {
    display: 'inline-block',
    background: '#4fa3e0',
    color: 'white',
    padding: '3px 12px',
    borderRadius: 99,
    fontSize: 11,
    fontWeight: 700,
    marginBottom: 10,
  },
  featureList: { display: 'flex', flexDirection: 'column', gap: 10 },
  featureItem: { display: 'flex', alignItems: 'center', gap: 10 },
  checkMark: {
    width: 22,
    height: 22,
    background: '#4fa3e0',
    color: 'white',
    borderRadius: '50%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: 12,
    fontWeight: 700,
    flexShrink: 0,
    lineHeight: '22px',
    textAlign: 'center',
  },
  secRow: {
    display: 'flex',
    alignItems: 'center',
    gap: 14,
    padding: '14px 0',
    borderBottom: '1px solid #f1f5f9',
  },
  secIcon: {
    width: 40,
    height: 40,
    background: '#ebf5ff',
    borderRadius: 10,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  notifRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '12px 0',
    borderBottom: '1px solid #f1f5f9',
  },
}
