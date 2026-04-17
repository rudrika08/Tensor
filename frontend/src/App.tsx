import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import { LayoutDashboard, Upload, FileText, Settings } from 'lucide-react'
import Dashboard from './pages/Dashboard'
import UploadPage from './pages/UploadPage'
import SubmissionDetail from './pages/SubmissionDetail'
import './index.css'

export default function App() {
  return (
    <BrowserRouter>
      <div className="app-layout">
        {/* ── Sidebar ── */}
        <aside className="sidebar">
          <div className="sidebar-logo">
            <h1>⬡ TENSOR</h1>
            <p>Credit Intelligence</p>
          </div>

          <nav className="sidebar-nav">
            <div className="nav-section-label">Main</div>

            <NavLink
              to="/"
              end
              className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
            >
              <LayoutDashboard size={16} />
              Dashboard
            </NavLink>

            <NavLink
              to="/upload"
              className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
            >
              <Upload size={16} />
              New Submission
            </NavLink>

            <div className="nav-section-label" style={{ marginTop: 8 }}>Analysis</div>

            <NavLink
              to="/submissions"
              className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
            >
              <FileText size={16} />
              All Submissions
            </NavLink>
          </nav>

          {/* Version tag */}
          <div style={{ padding: '16px 20px', borderTop: '1px solid var(--border)' }}>
            <p className="text-xs text-muted">Tensor AI v1.0.0</p>
            <p className="text-xs text-muted" style={{ marginTop: 2 }}>Kirana Credit Engine</p>
          </div>
        </aside>

        {/* ── Main content ── */}
        <main className="main-content">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/upload" element={<UploadPage />} />
            <Route path="/submissions" element={<Dashboard />} />
            <Route path="/submissions/:id" element={<SubmissionDetail />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
