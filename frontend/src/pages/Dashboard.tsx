import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { TrendingUp, AlertTriangle, CheckCircle, Clock, ArrowRight, MapPin, Store, Upload } from 'lucide-react'
import { submissionsApi } from '../api/client'
import type { SubmissionListItem } from '../api/client'
const STATUS_BADGE: Record<string, string> = {
  pending: 'badge-amber',
  validating: 'badge-amber',
  processing: 'badge-blue',
  completed: 'badge-green',
  failed: 'badge-red',
  flagged: 'badge-red',
}

const RISK_BADGE: Record<string, string> = {
  low: 'badge-green',
  medium: 'badge-amber',
  high: 'badge-red',
  critical: 'badge-red',
}

const REC_COLOR: Record<string, string> = {
  APPROVE: 'var(--accent-green)',
  APPROVE_WITH_MONITORING: 'var(--accent-blue)',
  REFER_FOR_FIELD_VISIT: 'var(--accent-amber)',
  REJECT: 'var(--accent-red)',
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-IN', {
    day: 'numeric', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

export default function Dashboard() {
  const [submissions, setSubmissions] = useState<SubmissionListItem[]>([])
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    submissionsApi.list()
      .then(r => setSubmissions(r.data))
      .catch(() => setSubmissions([]))
      .finally(() => setLoading(false))
  }, [])

  const completed = submissions.filter(s => s.status === 'completed').length
  const processing = submissions.filter(s => ['processing', 'validating', 'pending'].includes(s.status)).length
  const flagged = submissions.filter(s => s.risk_level && ['high', 'critical'].includes(s.risk_level)).length
  const approved = submissions.filter(s => s.recommendation === 'APPROVE').length

  return (
    <div className="fade-in">
      <div className="page-header">
        <h2>Credit Intelligence Dashboard</h2>
        <p>AI-driven kirana store analysis for NBFC credit underwriting</p>
      </div>

      <div className="page-body">
        {/* ── Stats ── */}
        <div className="stat-grid">
          <div className="stat-card blue">
            <div className="stat-label">Total Submissions</div>
            <div className="stat-value" style={{ color: 'var(--accent-blue)' }}>
              {submissions.length}
            </div>
            <div className="stat-sub">All time</div>
          </div>

          <div className="stat-card green">
            <div className="stat-label">Completed</div>
            <div className="stat-value" style={{ color: 'var(--accent-green)' }}>
              {completed}
            </div>
            <div className="stat-sub">{approved} approved</div>
          </div>

          <div className="stat-card amber">
            <div className="stat-label">Processing</div>
            <div className="stat-value" style={{ color: 'var(--accent-amber)' }}>
              {processing}
            </div>
            <div className="stat-sub">In pipeline</div>
          </div>

          <div className="stat-card red">
            <div className="stat-label">High Risk Flags</div>
            <div className="stat-value" style={{ color: 'var(--accent-red)' }}>
              {flagged}
            </div>
            <div className="stat-sub">Requires attention</div>
          </div>
        </div>

        {/* ── Submissions Table ── */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <div className="card-title" style={{ marginBottom: 0 }}>Recent Submissions</div>
            <button
              className="btn btn-primary btn-sm"
              onClick={() => navigate('/upload')}
            >
              <Store size={14} /> New Submission
            </button>
          </div>

          {loading ? (
            <div className="flex items-center justify-center" style={{ padding: 48, gap: 12 }}>
              <div className="spinner" />
              <span className="text-muted text-sm">Loading submissions…</span>
            </div>
          ) : submissions.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '48px 24px' }}>
              <Store size={40} style={{ color: 'var(--text-muted)', margin: '0 auto 12px' }} />
              <p style={{ color: 'var(--text-secondary)', fontSize: 15, fontWeight: 500 }}>
                No submissions yet
              </p>
              <p className="text-muted text-sm" style={{ marginTop: 4, marginBottom: 20 }}>
                Upload kirana store images to get started
              </p>
              <button className="btn btn-primary" onClick={() => navigate('/upload')}>
                <Upload size={15} /> Create First Submission
              </button>
            </div>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Store</th>
                    <th>Location</th>
                    <th>Status</th>
                    <th>Risk</th>
                    <th>Recommendation</th>
                    <th>Date</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {submissions.map(s => (
                    <tr
                      key={s.id}
                      style={{ cursor: 'pointer' }}
                      onClick={() => navigate(`/submissions/${s.id}`)}
                    >
                      <td>
                        <div style={{ fontWeight: 600, fontSize: 14 }}>
                          {s.store_name || 'Unnamed Store'}
                        </div>
                        <div className="text-xs text-muted font-mono">
                          {s.id.slice(0, 8)}…
                        </div>
                      </td>
                      <td>
                        <div className="flex items-center gap-2 text-sm text-muted">
                          <MapPin size={12} />
                          {s.latitude.toFixed(4)}, {s.longitude.toFixed(4)}
                        </div>
                      </td>
                      <td>
                        <span className={`badge ${STATUS_BADGE[s.status] || 'badge-blue'}`}>
                          {s.status}
                        </span>
                      </td>
                      <td>
                        {s.risk_level ? (
                          <span className={`badge ${RISK_BADGE[s.risk_level] || 'badge-blue'}`}>
                            {s.risk_level}
                          </span>
                        ) : <span className="text-muted text-xs">—</span>}
                      </td>
                      <td>
                        {s.recommendation ? (
                          <span style={{
                            fontSize: 12, fontWeight: 600,
                            color: REC_COLOR[s.recommendation] || 'var(--text-secondary)',
                          }}>
                            {s.recommendation.replace(/_/g, ' ')}
                          </span>
                        ) : <span className="text-muted text-xs">Pending</span>}
                      </td>
                      <td className="text-sm text-muted">{formatDate(s.created_at)}</td>
                      <td>
                        <ArrowRight size={14} style={{ color: 'var(--text-muted)' }} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// End of Dashboard.tsx
