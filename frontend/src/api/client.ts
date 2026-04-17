import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export const api = axios.create({
  baseURL: API_BASE,
  timeout: 60000,
})

export interface SubmissionListItem {
  id: string
  created_at: string
  status: string
  store_name: string | null
  latitude: number
  longitude: number
  recommendation: string | null
  risk_level: string | null
}

export interface SubmissionDetail {
  id: string
  created_at: string
  updated_at: string
  status: string
  latitude: number
  longitude: number
  store_name: string | null
  years_in_operation: number | null
  claimed_floor_area_sqft: number | null
  monthly_rent: number | null
  image_records: ImageRecord[] | null
  vision_signals: VisionSignals | null
  geo_signals: GeoSignals | null
  fraud_assessment: FraudAssessment | null
  cash_flow_estimate: CashFlowEstimate | null
  recommendation: string | null
  risk_level: string | null
  explanation: string | null
  error_message: string | null
}

export interface ImageRecord {
  path: string
  label: string
  blur_score: number
  resolution: [number, number]
  valid: boolean
  exif_timestamp: string | null
}

export interface VisionSignals {
  sdi: number
  sku_diversity: number
  detected_product_count: number
  dominant_category: string
  category_mix: Record<string, number>
  inventory_value_est: number
  store_size_tier: string
  floor_area_est_sqft: number
}

export interface GeoSignals {
  catchment_tier: string
  population_500m: number
  footfall_proxy_score: number
  poi_count: number
  poi_breakdown: Record<string, number>
  road_type: string
  competition_count: number
  competition_factor: number
  geo_score: number
  nearby_stores: NearbyStore[]
}

export interface NearbyStore {
  name: string
  type: string
  distance_m: number
}

export interface FraudAssessment {
  risk_level: string
  flags: string[]
  flag_count: number
  confidence: number
}

export interface CashFlowEstimate {
  daily_sales_point: number
  daily_sales_low: number
  daily_sales_high: number
  confidence_score: number
  monthly_income_point: number
  monthly_income_low: number
  monthly_income_high: number
  blended_margin: number
  shap_factors: Record<string, ShapFactor>
}

export interface ShapFactor {
  value: number
  weight: number
  direction: string
  label: string
}

export const submissionsApi = {
  list: () => api.get<SubmissionListItem[]>('/api/v1/submissions'),
  get: (id: string) => api.get<SubmissionDetail>(`/api/v1/submissions/${id}`),
  status: (id: string) => api.get(`/api/v1/submissions/${id}/status`),
  create: (formData: FormData) =>
    api.post<{ id: string; status: string; message: string }>('/api/v1/submissions', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
}
