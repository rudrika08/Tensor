import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { useNavigate } from 'react-router-dom'
import { Upload, X, MapPin, Image, CheckCircle, AlertCircle } from 'lucide-react'
import { submissionsApi } from '../api/client'

type ImageLabel = 'shelf' | 'counter' | 'exterior' | 'unknown'
interface ImageFile { file: File; preview: string; label: ImageLabel }

export default function UploadPage() {
  const navigate = useNavigate()
  const [images, setImages] = useState<ImageFile[]>([])
  const [lat, setLat] = useState('')
  const [lon, setLon] = useState('')
  const [storeName, setStoreName] = useState('')
  const [yearsOp, setYearsOp] = useState('')
  const [floorArea, setFloorArea] = useState('')
  const [rent, setRent] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [gpsLoading, setGpsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const newFiles = acceptedFiles.slice(0, 5 - images.length).map(f => ({
      file: f, preview: URL.createObjectURL(f), label: 'unknown' as ImageLabel,
    }))
    setImages(prev => [...prev, ...newFiles].slice(0, 5))
    setError(null)
  }, [images])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'image/*': ['.jpg', '.jpeg', '.png', '.webp'] },
    maxFiles: 5, maxSize: 20 * 1024 * 1024, disabled: images.length >= 5,
  })

  const removeImage = (idx: number) => {
    URL.revokeObjectURL(images[idx].preview)
    setImages(prev => prev.filter((_, i) => i !== idx))
  }

  const updateLabel = (idx: number, label: ImageLabel) =>
    setImages(prev => prev.map((img, i) => i === idx ? { ...img, label } : img))

  const detectGPS = () => {
    if (!navigator.geolocation) return
    setGpsLoading(true)
    navigator.geolocation.getCurrentPosition(
      pos => { setLat(pos.coords.latitude.toFixed(6)); setLon(pos.coords.longitude.toFixed(6)); setGpsLoading(false) },
      () => setGpsLoading(false)
    )
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    if (images.length < 3) { setError('Please upload at least 3 images.'); return }
    if (!lat || !lon) { setError('GPS coordinates are required.'); return }
    setSubmitting(true)
    try {
      const fd = new FormData()
      images.forEach(img => fd.append('images', img.file))
      fd.append('latitude', lat); fd.append('longitude', lon)
      fd.append('image_labels', JSON.stringify(images.map(i => i.label)))
      if (storeName) fd.append('store_name', storeName)
      if (yearsOp) fd.append('years_in_operation', yearsOp)
      if (floorArea) fd.append('claimed_floor_area_sqft', floorArea)
      if (rent) fd.append('monthly_rent', rent)
      const res = await submissionsApi.create(fd)
      setSuccess(true)
      setTimeout(() => navigate(`/submissions/${res.data.id}`), 1200)
    } catch (err: any) {
      setError(err?.response?.data?.detail?.message || 'Submission failed.')
    } finally { setSubmitting(false) }
  }

  const isReady = images.length >= 3 && lat && lon

  return (
    <div className="fade-in">
      <div className="page-header">
        <h2>New Store Submission</h2>
        <p>Upload 3–5 store images and GPS coordinates to begin AI analysis</p>
      </div>
      <div className="page-body">
        <form onSubmit={handleSubmit}>
          <div className="grid-2" style={{ gap: 28, alignItems: 'start' }}>

            {/* LEFT — Images + GPS */}
            <div>
              <div className="card mb-6">
                <div className="card-title">Store Images <span style={{ color: 'var(--accent-red)' }}>*</span></div>
                <p className="text-sm text-muted mb-4">3–5 images · min 640×480 · JPG/PNG/WEBP · max 20 MB each</p>
                <div className="flex items-center gap-2 mb-4 text-sm">
                  <span style={{ color: images.length >= 3 ? 'var(--accent-green)' : 'var(--accent-amber)' }}>
                    {images.length}/5
                  </span>
                  <div className="progress-bar" style={{ flex: 1 }}>
                    <div className="progress-fill" style={{ width: `${(images.length / 5) * 100}%` }} />
                  </div>
                </div>

                {images.length < 5 && (
                  <div {...getRootProps()} className={`upload-zone ${isDragActive ? 'drag-active' : ''}`}>
                    <input {...getInputProps()} id="image-upload" />
                    <div className="upload-zone-icon">
                      <Image size={24} style={{ color: 'var(--accent-blue)' }} />
                    </div>
                    <h3>{isDragActive ? 'Drop images here' : 'Drag & drop store images'}</h3>
                    <p>or <span style={{ color: 'var(--accent-blue)' }}>click to browse</span></p>
                  </div>
                )}

                {images.length > 0 && (
                  <div className="image-preview-grid" style={{ marginTop: 16 }}>
                    {images.map((img, idx) => (
                      <div key={idx} className="image-preview-item">
                        <img src={img.preview} alt={`img-${idx}`} />
                        <button type="button" className="image-preview-remove" onClick={() => removeImage(idx)}>
                          <X size={12} />
                        </button>
                        <div className="image-preview-overlay">
                          <select className="label-select" value={img.label}
                            onChange={e => updateLabel(idx, e.target.value as ImageLabel)}>
                            <option value="unknown">Auto</option>
                            <option value="shelf">Shelf</option>
                            <option value="counter">Counter</option>
                            <option value="exterior">Exterior</option>
                          </select>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div className="card">
                <div className="card-title">GPS Coordinates <span style={{ color: 'var(--accent-red)' }}>*</span></div>
                <div className="grid-2" style={{ gap: 12, marginBottom: 12 }}>
                  <div className="form-group" style={{ marginBottom: 0 }}>
                    <label className="form-label">Latitude</label>
                    <input id="latitude-input" className="form-input" placeholder="19.0760"
                      value={lat} onChange={e => setLat(e.target.value)} type="number" step="any" required />
                  </div>
                  <div className="form-group" style={{ marginBottom: 0 }}>
                    <label className="form-label">Longitude</label>
                    <input id="longitude-input" className="form-input" placeholder="72.8777"
                      value={lon} onChange={e => setLon(e.target.value)} type="number" step="any" required />
                  </div>
                </div>
                <button type="button" id="detect-gps-btn" className="btn btn-secondary btn-sm"
                  onClick={detectGPS} disabled={gpsLoading}>
                  {gpsLoading ? <div className="spinner" style={{ width: 14, height: 14 }} /> : <MapPin size={14} />}
                  Detect My Location
                </button>
              </div>
            </div>

            {/* RIGHT — Details + Submit */}
            <div>
              <div className="card mb-6">
                <div className="card-title">Store Details <span className="text-muted text-xs" style={{ textTransform: 'none', fontWeight: 400 }}>(Optional)</span></div>
                <div className="form-group">
                  <label className="form-label">Store Name</label>
                  <input id="store-name-input" className="form-input" placeholder="Sharma General Store"
                    value={storeName} onChange={e => setStoreName(e.target.value)} />
                </div>
                <div className="grid-2" style={{ gap: 12 }}>
                  <div className="form-group">
                    <label className="form-label">Years Operating</label>
                    <input id="years-op-input" className="form-input" placeholder="5"
                      value={yearsOp} onChange={e => setYearsOp(e.target.value)} type="number" min="0" />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Floor Area (sqft)</label>
                    <input id="floor-area-input" className="form-input" placeholder="150"
                      value={floorArea} onChange={e => setFloorArea(e.target.value)} type="number" min="0" />
                  </div>
                </div>
                <div className="form-group" style={{ marginBottom: 0 }}>
                  <label className="form-label">Monthly Rent (₹)</label>
                  <input id="rent-input" className="form-input" placeholder="8000"
                    value={rent} onChange={e => setRent(e.target.value)} type="number" min="0" />
                </div>
              </div>

              <div className="card mb-6">
                <div className="card-title">Checklist</div>
                {[
                  { label: `${images.length} image(s) uploaded (min 3)`, done: images.length >= 3 },
                  { label: 'GPS coordinates set', done: !!(lat && lon) },
                  { label: 'At least one image tagged', done: images.some(i => i.label !== 'unknown') },
                ].map((item, i) => (
                  <div key={i} className="flex items-center gap-2 text-sm" style={{ marginBottom: 10 }}>
                    {item.done
                      ? <CheckCircle size={16} style={{ color: 'var(--accent-green)', flexShrink: 0 }} />
                      : <AlertCircle size={16} style={{ color: 'var(--text-muted)', flexShrink: 0 }} />}
                    <span style={{ color: item.done ? 'var(--text-primary)' : 'var(--text-muted)' }}>{item.label}</span>
                  </div>
                ))}
              </div>

              {error && (
                <div className="flag-item mb-4">
                  <AlertCircle size={16} style={{ color: 'var(--accent-red)', flexShrink: 0 }} />
                  <span>{error}</span>
                </div>
              )}

              {success && (
                <div className="flex items-center gap-2 mb-4 text-sm"
                  style={{ padding: 12, background: 'rgba(16,185,129,0.08)', border: '1px solid rgba(16,185,129,0.3)', borderRadius: 'var(--radius-sm)' }}>
                  <CheckCircle size={16} style={{ color: 'var(--accent-green)' }} />
                  <span style={{ color: 'var(--accent-green)' }}>Submitted! Redirecting…</span>
                </div>
              )}

              <button id="submit-btn" type="submit" className="btn btn-primary btn-lg"
                style={{ width: '100%', justifyContent: 'center' }} disabled={!isReady || submitting}>
                {submitting
                  ? <><div className="spinner" style={{ width: 18, height: 18 }} /> Submitting…</>
                  : <><Upload size={18} /> Analyse Store</>}
              </button>
              <p className="text-xs text-muted" style={{ textAlign: 'center', marginTop: 10 }}>
                Analysis completes in ~30–90 seconds
              </p>
            </div>
          </div>
        </form>
      </div>
    </div>
  )
}
