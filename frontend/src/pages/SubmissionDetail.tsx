import { useEffect, useState, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  ArrowLeft, RefreshCw, AlertTriangle, CheckCircle,
  TrendingUp, MapPin, Eye, ShieldAlert, Info
} from 'lucide-react'
import { submissionsApi } from '../api/client'
import type { SubmissionDetail as ISubmissionDetail } from '../api/client'
const RISK_BADGE: Record<string, string> = {
  low: 'badge-green', medium: 'badge-amber', high: 'badge-red', critical: 'badge-red',
}
const REC_COLOR: Record<string, string> = {
  APPROVE: 'var(--accent-green)',
  APPROVE_WITH_MONITORING: 'var(--accent-blue)',
  REFER_FOR_FIELD_VISIT: 'var(--accent-amber)',
  REJECT: 'var(--accent-red)',
}

function fmt(n: number) {
  return new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 }).format(n)
}

function ScoreMeter({ label, value, max = 100, color = 'var(--accent-blue)' }:
  { label: string; value: number; max?: number; color?: string }) {
  return (
    <div style={{ marginBottom: 14 }}>
      <div className="flex justify-between text-sm mb-4" style={{ marginBottom: 6 }}>
        <span className="text-muted">{label}</span>
        <span style={{ fontWeight: 600 }}>{typeof value === 'number' ? value.toFixed(2) : '—'}</span>
      </div>
      <div className="score-track">
        <div className="score-fill" style={{ width: `${Math.min((value / max) * 100, 100)}%`, background: color }} />
      </div>
    </div>
  )
}

const PROCESSING_STATUSES = ['pending', 'validating', 'processing']

export default function SubmissionDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [data, setData] = useState<ISubmissionDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const load = async () => {
    if (!id) return
    try {
      const res = await submissionsApi.get(id)
      setData(res.data)
      if (!PROCESSING_STATUSES.includes(res.data.status)) {
        if (pollRef.current) clearInterval(pollRef.current)
      }
    } catch { /* ignore */ }
    finally { setLoading(false) }
  }

  useEffect(() => {
    load()
    pollRef.current = setInterval(load, 4000)
    return () => { if (pollRef.current) clearInterval(pollRef.current) }
  }, [id])

  if (loading) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '60vh', gap: 12 }}>
      <div className="spinner" style={{ width: 28, height: 28 }} />
      <span className="text-muted">Loading analysis…</span>
    </div>
  )

  if (!data) return (
    <div style={{ textAlign: 'center', padding: 80 }}>
      <p className="text-muted">Submission not found.</p>
      <button className="btn btn-secondary mt-2" style={{ marginTop: 12 }} onClick={() => navigate('/')}>
        Back to Dashboard
      </button>
    </div>
  )

  const isProcessing = PROCESSING_STATUSES.includes(data.status)
  const v = data.vision_signals
  const g = data.geo_signals
  const fr = data.fraud_assessment
  const cf = data.cash_flow_estimate

  return (
    <div className="fade-in">
      <div className="page-header">
        <div className="flex items-center gap-4">
          <button className="btn btn-ghost btn-sm" onClick={() => navigate('/')}>
            <ArrowLeft size={16} /> Back
          </button>
          <div>
            <h2>{data.store_name || 'Unnamed Store'}</h2>
            <p className="font-mono" style={{ fontSize: 12 }}>{data.id}</p>
          </div>
          <div style={{ marginLeft: 'auto', display: 'flex', gap: 10, alignItems: 'center' }}>
            {data.risk_level && <span className={`badge ${RISK_BADGE[data.risk_level]}`}>{data.risk_level} risk</span>}
            {isProcessing && (
              <span className="badge badge-blue">
                <div className="spinner" style={{ width: 10, height: 10 }} /> Processing
              </span>
            )}
            <button className="btn btn-secondary btn-sm" onClick={load}>
              <RefreshCw size={14} /> Refresh
            </button>
          </div>
        </div>
      </div>

      <div className="page-body">
        {/* Processing banner */}
        {isProcessing && (
          <div className="card mb-6" style={{ background: 'rgba(79,142,247,0.06)', borderColor: 'rgba(79,142,247,0.3)', textAlign: 'center', padding: 32 }}>
            <div className="spinner" style={{ width: 32, height: 32, margin: '0 auto 12px' }} />
            <p style={{ fontWeight: 600, fontSize: 15 }}>AI Analysis in Progress</p>
            <p className="text-muted text-sm" style={{ marginTop: 4 }}>
              Running vision engine → geo analysis → fraud checks → fusion model…
            </p>
            <p className="text-muted text-xs" style={{ marginTop: 8 }}>Auto-refreshing every 4 seconds</p>
          </div>
        )}

        {data.status === 'failed' && (
          <div className="flag-item mb-6">
            <AlertTriangle size={18} style={{ color: 'var(--accent-red)' }} />
            <div>
              <strong>Pipeline Failed</strong>
              <p className="text-sm text-muted">{data.error_message}</p>
            </div>
          </div>
        )}

        {/* Recommendation banner */}
        {data.recommendation && (
          <div className="card mb-6" style={{
            background: `rgba(${data.recommendation === 'APPROVE' ? '16,185,129' :
              data.recommendation === 'REJECT' ? '239,68,68' : '79,142,247'}, 0.07)`,
            borderColor: REC_COLOR[data.recommendation],
            padding: '20px 24px',
          }}>
            <div className="flex items-center gap-3">
              {data.recommendation === 'APPROVE' ? <CheckCircle size={24} style={{ color: 'var(--accent-green)' }} />
                : <AlertTriangle size={24} style={{ color: REC_COLOR[data.recommendation] }} />}
              <div>
                <div style={{ fontWeight: 700, fontSize: 16, color: REC_COLOR[data.recommendation] }}>
                  {data.recommendation.replace(/_/g, ' ')}
                </div>
                {cf && (
                  <div className="text-sm text-muted">
                    Confidence: {((cf.confidence_score || 0) * 100).toFixed(0)}% ·
                    Risk: {data.risk_level}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Cash flow */}
        {cf && (
          <div className="card mb-6">
            <div className="card-title"><TrendingUp size={14} style={{ display: 'inline', marginRight: 6 }} />Cash Flow Estimate</div>
            <div className="grid-2" style={{ gap: 16 }}>
              <div className="cashflow-range" style={{ flexDirection: 'column', alignItems: 'flex-start' }}>
                <div className="text-xs text-muted" style={{ marginBottom: 4 }}>Daily Sales (70% CI)</div>
                <div className="cashflow-value">₹{fmt(cf.daily_sales_low)}–{fmt(cf.daily_sales_high)}</div>
                <div className="text-xs text-muted">Point: ₹{fmt(cf.daily_sales_point)}/day</div>
              </div>
              <div className="cashflow-range" style={{ flexDirection: 'column', alignItems: 'flex-start' }}>
                <div className="text-xs text-muted" style={{ marginBottom: 4 }}>Monthly Net Income (70% CI)</div>
                <div className="cashflow-value" style={{ fontSize: 26 }}>
                  ₹{fmt(cf.monthly_income_low)}–{fmt(cf.monthly_income_high)}
                </div>
                <div className="text-xs text-muted">Margin: {((cf.blended_margin || 0) * 100).toFixed(1)}% blended</div>
              </div>
            </div>

            {/* SHAP factors */}
            {cf.shap_factors && (
              <div style={{ marginTop: 20 }}>
                <div className="text-xs text-muted" style={{ marginBottom: 12, fontWeight: 600, letterSpacing: '0.5px', textTransform: 'uppercase' }}>Key Drivers</div>
                {Object.entries(cf.shap_factors).map(([key, factor]) => (
                  <ScoreMeter
                    key={key}
                    label={factor.label}
                    value={(factor.weight - 0.5) * 100}
                    max={110}
                    color={factor.direction === 'positive' ? 'var(--accent-green)' : 'var(--accent-red)'}
                  />
                ))}
              </div>
            )}
          </div>
        )}

        <div className="grid-2" style={{ gap: 20, marginBottom: 20 }}>
          {/* Vision Signals */}
          {v && (
            <div className="card">
              <div className="card-title"><Eye size={14} style={{ display: 'inline', marginRight: 6 }} />Vision Signals</div>
              <ScoreMeter label="Shelf Density Index" value={v.sdi} max={1} color="var(--accent-violet)" />
              <ScoreMeter label="SKU Diversity" value={v.sku_diversity} max={25} color="var(--accent-blue)" />
              <div style={{ marginTop: 12, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                {[
                  { label: 'Store Size', value: v.store_size_tier },
                  { label: 'Floor Area Est.', value: `${v.floor_area_est_sqft?.toFixed(0)} sqft` },
                  { label: 'Dominant Category', value: v.dominant_category },
                  { label: 'Inventory Value', value: `₹${fmt(v.inventory_value_est)}` },
                ].map(({ label, value }) => (
                  <div key={label} style={{ background: 'var(--bg-secondary)', borderRadius: 'var(--radius-sm)', padding: '10px 12px' }}>
                    <div className="text-xs text-muted">{label}</div>
                    <div style={{ fontWeight: 600, fontSize: 13, marginTop: 3 }}>{value}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Geo Signals */}
          {g && (
            <div className="card">
              <div className="card-title"><MapPin size={14} style={{ display: 'inline', marginRight: 6 }} />Geo Signals</div>
              <ScoreMeter label="Footfall Proxy Score" value={g.footfall_proxy_score} max={100} color="var(--accent-teal)" />
              <ScoreMeter label="Geo Score (composite)" value={g.geo_score} max={100} color="var(--accent-blue)" />
              <div style={{ marginTop: 12, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                {[
                  { label: 'Catchment Tier', value: g.catchment_tier?.replace(/_/g, ' ') },
                  { label: 'Population (500m)', value: fmt(g.population_500m) },
                  { label: 'Road Type', value: g.road_type },
                  { label: 'Competitors (300m)', value: String(g.competition_count) },
                ].map(({ label, value }) => (
                  <div key={label} style={{ background: 'var(--bg-secondary)', borderRadius: 'var(--radius-sm)', padding: '10px 12px' }}>
                    <div className="text-xs text-muted">{label}</div>
                    <div style={{ fontWeight: 600, fontSize: 13, marginTop: 3 }}>{value}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Fraud Assessment */}
        {fr && (
          <div className="card mb-6">
            <div className="card-title"><ShieldAlert size={14} style={{ display: 'inline', marginRight: 6 }} />Fraud Assessment</div>
            <div className="flex items-center gap-3 mb-4">
              <span className={`badge ${RISK_BADGE[fr.risk_level]}`}>{fr.risk_level} risk</span>
              <span className="text-sm text-muted">{fr.flag_count} flag(s) detected</span>
              <span className="text-sm text-muted">· Confidence: {((fr.confidence || 0) * 100).toFixed(0)}%</span>
            </div>
            {fr.flags.length === 0 ? (
              <div className="flex items-center gap-2 text-sm" style={{ color: 'var(--accent-green)' }}>
                <CheckCircle size={16} /> No fraud signals detected
              </div>
            ) : (
              fr.flags.map((flag, i) => (
                <div key={i} className="flag-item">
                  <AlertTriangle size={16} style={{ color: 'var(--accent-red)', flexShrink: 0 }} />
                  <span>{flag.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}</span>
                </div>
              ))
            )}
          </div>
        )}

        {/* NLG Explanation */}
        {data.explanation && (
          <div className="card">
            <div className="card-title"><Info size={14} style={{ display: 'inline', marginRight: 6 }} />Analyst Explanation</div>
            <pre style={{
              fontFamily: 'Inter, sans-serif', fontSize: 13, lineHeight: 1.8,
              color: 'var(--text-secondary)', whiteSpace: 'pre-wrap', margin: 0,
            }}>
              {data.explanation}
            </pre>
          </div>
        )}
      </div>
    </div>
  )
}
