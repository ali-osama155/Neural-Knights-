import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
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

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Login />} />
        <Route path="/dashboard" element={<AppLayout><Dashboard /></AppLayout>} />
        <Route path="/cv-upload" element={<AppLayout><CVUpload /></AppLayout>} />
        <Route path="/chatbot" element={<AppLayout><Chatbot /></AppLayout>} />
        <Route path="/interview" element={<AppLayout><Interview /></AppLayout>} />
        <Route path="/profile" element={<AppLayout><Profile /></AppLayout>} />
        <Route path="*" element={<Navigate to="/" />} />
      </Routes>
    </BrowserRouter>
  )
}
