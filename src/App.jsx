import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { CVProvider } from './contexts/CVContext'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import CVUpload from './pages/CVUpload'
import Chatbot from './pages/Chatbot'
import Interview from './pages/Interview'
import Profile from './pages/Profile'
import Sidebar from './components/Sidebar'
import Navbar from './components/Navbar'

function AppLayout({ children }) {
  return (
    <div className="app-layout">
      <Sidebar />
      <div className="main-content">
        <Navbar />
        <div className="page-content">
          {children}
        </div>
      </div>
    </div>
  )
}

/** Guards authenticated-only routes so a stale/missing token redirects to login. */
function RequireAuth({ children }) {
  const { loading, isAuthenticated } = useAuth()

  if (loading) {
    return (
      <div style={{
        minHeight: '100vh', display: 'flex',
        alignItems: 'center', justifyContent: 'center',
        color: '#64748b', fontFamily: 'Inter, sans-serif',
      }}>
        Loading…
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/" replace />
  }

  return children
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <CVProvider>
          <Routes>
            <Route path="/" element={<Login />} />
            <Route path="/dashboard" element={
              <RequireAuth><AppLayout><Dashboard /></AppLayout></RequireAuth>
            } />
            <Route path="/cv-upload" element={
              <RequireAuth><AppLayout><CVUpload /></AppLayout></RequireAuth>
            } />
            <Route path="/chatbot" element={
              <RequireAuth><AppLayout><Chatbot /></AppLayout></RequireAuth>
            } />
            <Route path="/interview" element={
              <RequireAuth><AppLayout><Interview /></AppLayout></RequireAuth>
            } />
            <Route path="/profile" element={
              <RequireAuth><AppLayout><Profile /></AppLayout></RequireAuth>
            } />
            <Route path="*" element={<Navigate to="/" />} />
          </Routes>
        </CVProvider>
      </AuthProvider>
    </BrowserRouter>
  )
}
