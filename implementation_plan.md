# Multi-Modal Credit Intelligence System — Implementation Plan

## Overview

This system replaces physical field officer visits with an AI-driven pipeline that analyzes store images and GPS coordinates to produce calibrated cash flow estimates for NBFC credit underwriting. The architecture is a six-phase pipeline where each phase feeds structured signals downstream.

```
Raw Inputs (Images + GPS)
       │
       ▼
┌─────────────┐    ┌──────────────────┐
│ Vision      │    │  Geo-Spatial     │
│ Engine      │    │  Engine          │
│ (Phase 2)   │    │  (Phase 3)       │
└──────┬──────┘    └────────┬─────────┘
       │                    │
       ▼                    │
┌─────────────┐             │
│ Fraud Check │◄────────────┘
│ (Phase 4)   │
└──────┬──────┘
       │
       ▼
┌─────────────────────┐
│ Multi-Modal Fusion  │
│ (Phase 5)           │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Output + Report     │
│ (Phase 6)           │
└─────────────────────┘
```

---

## User Review Required

> [!IMPORTANT]
> **Scope Clarification**: This plan covers the full 6-phase architecture as a monorepo with a Python backend (FastAPI), a web frontend (React), and a PostgreSQL database. Mobile (React Native/Flutter) is scoped for Phase 1 but as a web-first MVP first. Confirm if mobile-first is required from Day 1.

> [!WARNING]
> **External API Keys Required Before Development Starts**: Google Maps Platform (Places API, Roads API, Geocoding API), AWS S3 or GCS credentials, and optionally OpenAI API (for CLIP via API vs. local inference). These must be provisioned before Phase 3 can be built.

> [!CAUTION]
> **YOLOv8 Fine-Tuning Requires Labeled Data**: Phase 2's product detection accuracy depends heavily on 500–2000 labeled kirana store images. Without this dataset, the system falls back to zero-shot CLIP classification. Plan for a data labeling sprint (Roboflow or Label Studio) **before** Phase 2 is production-ready.

---

## Open Questions

> [!IMPORTANT]
> 1. **Deployment Target**: Cloud-native (AWS/GCP) or on-premise? This affects storage (S3 vs. local), DB (RDS vs. self-hosted PG), and model serving (SageMaker vs. bare FastAPI).
> 2. **Mobile Requirement**: Is a React Native / Flutter mobile app required for the hackathon demo, or is a responsive web form sufficient for Phase 1?
> 3. **Labeled Dataset**: Do you have access to any kirana store image datasets, or does labeling need to start from scratch (Roboflow public sets)?
> 4. **Bayesian Uncertainty**: Full PyMC/Stan Bayesian modeling or simpler quantile regression (scikit-learn)? PyMC is more accurate but far harder to productionize quickly.
> 5. **NBFC Output Format**: Does the final report need a PDF (Jinja2 → WeasyPrint), or is a web dashboard sufficient for the demo?
> 6. **Hackathon Timeline**: Approximate time available? This determines which phases to build fully vs. mock/stub.

---

## Proposed Changes

### Phase 1 — Data Ingestion & Preprocessing

#### [NEW] `backend/app/api/upload.py`
FastAPI router for `/api/v1/submissions`. Accepts multipart form with 3–5 image files + GPS JSON. Performs:
- File size and MIME type validation
- Assigns a `submission_id` (UUID)
- Saves images to S3/GCS with structured key: `submissions/{id}/{type}_{n}.jpg`
- Writes metadata record to PostgreSQL

#### [NEW] `backend/app/models/submission.py`
SQLAlchemy ORM model for `submissions` table:
```
submissions(id UUID, timestamp, lat FLOAT, lon FLOAT, image_paths JSONB, status ENUM, fraud_flags JSONB, scores JSONB)
```

#### [NEW] `backend/app/services/image_validator.py`
Validation pipeline:
- **Resolution check**: Reject if < 640×480
- **Blur detection**: Laplacian variance via OpenCV. Threshold < 100 = blurry, reject
- **Coverage type classifier**: Lightweight CNN or CLIP zero-shot to tag each image as `shelf` / `counter` / `exterior` / `unknown`
- Returns `{valid: bool, label: str, blur_score: float, resolution: tuple}`

#### [NEW] `frontend/src/pages/UploadPage.tsx`
React web form with:
- Drag-and-drop image uploader (3–5 images)
- GPS input (manual entry or browser Geolocation API)
- Image type tagging UI (user can override auto-label)
- Submission progress indicator

#### [NEW] `backend/migrations/001_initial_schema.sql`
PostgreSQL schema migrations via Alembic.

---

### Phase 2 — Vision Engine

#### [NEW] `backend/app/services/vision/preprocessor.py`
OpenCV preprocessing pipeline:
- CLAHE for low-light normalization (converts to LAB, applies to L channel)
- Resize to model input size
- EXIF metadata extraction (timestamp, GPS, device) via `exifread`

#### [NEW] `backend/app/services/vision/detector.py`
YOLOv8 inference wrapper:
- Loads pretrained `yolov8m.pt` or fine-tuned model
- Returns bounding boxes + class labels + confidence scores
- Computes **Shelf Density Index (SDI)** = `filled_area / total_shelf_area`
- Computes **SKU diversity score** = unique product category count
- Computes **inventory value estimate** = category × median unit price × unit count

#### [NEW] `backend/app/services/vision/segmenter.py`
Meta SAM integration:
- Segments shelf zones from exterior/counter images
- Computes fill percentage per shelf zone
- Provides polygon masks for downstream area estimation

#### [NEW] `backend/app/services/vision/clip_classifier.py`
CLIP zero-shot classification:
- Product category labels: `["staples", "FMCG packaged goods", "dairy", "snacks", "beverages", "tobacco", "personal care", "household", "fresh produce"]`
- Returns category probability distribution per detected region

#### [NEW] `backend/app/services/vision/depth_estimator.py`
MiDaS depth map:
- Estimates relative depth from a single exterior/interior image
- Heuristic floor area estimation from depth profile
- Maps to store size tier: `small (<100sqft) / medium (100-300sqft) / large (>300sqft)`

#### [NEW] `backend/app/services/vision/pipeline.py`
Orchestrator that runs all vision services in order and returns a unified `VisionSignals` dataclass:
```python
@dataclass
class VisionSignals:
    sdi: float                    # 0.0–1.0
    sku_diversity: int            # count
    category_mix: dict            # {category: weight}
    inventory_value_est: float    # ₹
    store_size_tier: str          # small/medium/large
    floor_area_est: float         # sq ft
    image_quality_scores: list
    exif_timestamps: list
    lighting_histograms: list
```

---

### Phase 3 — Geo-Spatial Engine

#### [NEW] `backend/app/services/geo/catchment.py`
Catchment Density Score:
- Queries WorldPop raster or Census ward-level data for 500m radius
- Classifies: `urban_dense / urban_sparse / peri_urban / rural`
- H3 hexagonal indexing (resolution 8–9) for efficient spatial queries

#### [NEW] `backend/app/services/geo/footfall.py`
Footfall Proxy Index:
- Google Places API: queries nearby POIs within 500m (schools, offices, bus stops, markets, auto stands)
- Weights POI types by traffic multiplier: bus_stop=1.5, school=1.3, office=1.2, market=1.8
- Google Roads API: classifies road type at store GPS (arterial=1.5x, collector=1.2x, local=1.0x, gully=0.7x)
- Returns composite `footfall_proxy_score` (0–100)

#### [NEW] `backend/app/services/geo/competition.py`
Competition Density Index:
- Google Places API or Overpass API (OSM) for `shop=convenience`, `shop=supermarket`, `shop=grocery` within 300m
- Scoring: 0–1 stores=0.9, 2–4 stores=1.0, 5–8 stores=0.9, >8 stores=0.8
- Returns `competition_count` and `competition_factor`

#### [NEW] `backend/app/services/geo/pipeline.py`
Orchestrator returning unified `GeoSignals` dataclass:
```python
@dataclass
class GeoSignals:
    catchment_tier: str         # urban_dense / rural / etc.
    population_500m: int
    footfall_proxy_score: float # 0–100
    poi_breakdown: dict
    road_type: str
    competition_count: int
    competition_factor: float   # 0.8–1.0
    geo_score: float            # composite 0–100
```

---

### Phase 4 — Fraud Detection Layer

#### [NEW] `backend/app/services/fraud/consistency_checker.py`
Multi-image consistency:
- If >1 shelf image: compare inventory count across angles (±20% tolerance)
- Flag `inventory_count_inconsistency` if variance exceeds threshold

#### [NEW] `backend/app/services/fraud/temporal_checker.py`
EXIF temporal check:
- Extracts timestamps from all uploaded images
- Flags `temporal_gap_detected` if max gap > 30 minutes
- Flags `missing_exif` if EXIF absent (could mean screenshot/web-sourced image)

#### [NEW] `backend/app/services/fraud/lighting_checker.py`
Lighting histogram comparison:
- Converts all images to HSV, compares V-channel histograms
- Flags `lighting_inconsistency` if histogram correlation < 0.7 between images

#### [NEW] `backend/app/services/fraud/cross_signal_validator.py`
Economic logic rule engine:
| Condition | Flag |
|-----------|------|
| High inventory value + low footfall + rural road | `inventory_footfall_mismatch` |
| Overfull shelves + low SKU diversity | `possible_inspection_restocking` |
| New-looking store + claimed age > 10yrs | `age_claim_mismatch` |
| High category diversity + very small floor area | `space_category_inconsistency` |
| SDI > 0.9 + competition_count > 8 | `oversupply_high_competition` |

#### [NEW] `backend/app/services/fraud/pipeline.py`
Returns `FraudAssessment` dataclass with `risk_level: str`, `flags: list[str]`, `confidence: float`.

---

### Phase 5 — Multi-Modal Fusion & Cash Flow Estimation

#### [NEW] `backend/app/services/fusion/scorer.py`
Weighted estimation engine implementing the formula:
```
Estimated Daily Sales = Base × SDI_weight × SKU_weight × GeoScore_weight × CompetitionFactor

Weights:
  SDI_weight        = 0.6–1.4 (linear mapping of SDI 0→1)
  SKU_weight        = 0.7–1.3 (based on category diversity)
  GeoScore_weight   = 0.5–1.6 (based on footfall proxy score)
  CompetitionFactor = 0.8–1.0 (from geo engine)

Base sales by store size tier (₹/day):
  small:  ₹4,500 (midpoint of 3,000–6,000)
  medium: ₹14,000 (midpoint of 8,000–20,000)
  large:  ₹40,000 (midpoint of 20,000–60,000)
```

#### [NEW] `backend/app/services/fusion/uncertainty_estimator.py`
Confidence interval computation:
- Uses scikit-learn quantile regression (α=0.15, α=0.85 for 70% CI)
- Feature vector: `[sdi, sku_diversity_normalized, geo_score, competition_factor, store_size_encoded]`
- Trained on synthetic calibration data derived from CRISIL/RBI kirana benchmarks
- Wider bands when fraud flags are present or signals conflict

#### [NEW] `backend/app/services/fusion/margin_calculator.py`
Net margin blending based on category mix:
```
Margin assumptions:
  staples: 10%
  FMCG: 17.5%
  tobacco/snacks: 21.5%
  dairy: 8%
  beverages: 15%
  personal_care: 20%

Monthly Income = Daily Sales × 26 working days × blended_margin
```

#### [NEW] `backend/app/services/fusion/explainer.py`
SHAP-based feature explainability:
- Computes SHAP values for the fusion model
- Maps to human-readable factor labels
- Powers the natural language explanation in Phase 6

#### [NEW] `backend/app/services/fusion/pipeline.py`
Returns `CashFlowEstimate`:
```python
@dataclass
class CashFlowEstimate:
    daily_sales_point: float        # ₹
    daily_sales_range: tuple        # (low, high) 70% CI
    monthly_income_point: float     # ₹ after margin
    monthly_income_range: tuple
    confidence_score: float         # 0–1
    blended_margin: float
    shap_factors: dict
```

---

### Phase 6 — Output & Recommendation Engine

#### [NEW] `backend/app/api/results.py`
FastAPI router for `/api/v1/submissions/{id}/results`:
- Returns full JSON payload (see spec below)
- Triggers PDF generation on-demand

#### [NEW] `backend/app/services/output/json_builder.py`
Assembles final output JSON:
```json
{
  "submission_id": "uuid",
  "timestamp": "ISO-8601",
  "location": {"lat": 0.0, "lon": 0.0, "catchment_tier": "urban_dense"},
  "vision_signals": { "sdi": 0.72, "sku_diversity": 14, "store_size_tier": "medium" },
  "geo_signals": { "footfall_proxy_score": 67, "competition_count": 3 },
  "fraud_assessment": { "risk_level": "low", "flags": [] },
  "cash_flow_estimate": {
    "daily_sales_range": [9500, 17000],
    "monthly_income_range": [19000, 34000],
    "confidence_score": 0.74
  },
  "recommendation": "APPROVE_WITH_MONITORING",
  "explanation": "Natural language paragraph..."
}
```

#### [NEW] `backend/app/services/output/nlg.py`
Natural Language Generation for loan officer summaries:
- Template-based NLG using Jinja2 (deterministic, auditable)
- Optionally enhanced with GPT-4o for more fluid prose
- Integrates SHAP factor weights to explain key drivers

#### [NEW] `backend/app/services/output/pdf_generator.py`
PDF report via Jinja2 + WeasyPrint:
- 2-page loan officer report
- Page 1: Store overview, visual heat map, scores
- Page 2: Cash flow range, fraud flags, recommendation

#### [NEW] `frontend/src/pages/DashboardPage.tsx`
Loan officer React dashboard:
- Submission list with status badges
- Store detail view: score cards, fraud flags, cash flow chart
- PDF download button
- Map view (Leaflet.js) with store pin + catchment circle

---

## Project Structure

```
tensor/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── upload.py
│   │   │   └── results.py
│   │   ├── models/
│   │   │   └── submission.py
│   │   ├── services/
│   │   │   ├── vision/
│   │   │   │   ├── preprocessor.py
│   │   │   │   ├── detector.py       # YOLOv8
│   │   │   │   ├── segmenter.py      # SAM
│   │   │   │   ├── clip_classifier.py
│   │   │   │   ├── depth_estimator.py # MiDaS
│   │   │   │   └── pipeline.py
│   │   │   ├── geo/
│   │   │   │   ├── catchment.py
│   │   │   │   ├── footfall.py
│   │   │   │   ├── competition.py
│   │   │   │   └── pipeline.py
│   │   │   ├── fraud/
│   │   │   │   ├── consistency_checker.py
│   │   │   │   ├── temporal_checker.py
│   │   │   │   ├── lighting_checker.py
│   │   │   │   ├── cross_signal_validator.py
│   │   │   │   └── pipeline.py
│   │   │   ├── fusion/
│   │   │   │   ├── scorer.py
│   │   │   │   ├── uncertainty_estimator.py
│   │   │   │   ├── margin_calculator.py
│   │   │   │   ├── explainer.py      # SHAP
│   │   │   │   └── pipeline.py
│   │   │   └── output/
│   │   │       ├── json_builder.py
│   │   │       ├── nlg.py
│   │   │       └── pdf_generator.py
│   │   ├── core/
│   │   │   ├── config.py             # env vars, API keys
│   │   │   └── database.py           # SQLAlchemy engine
│   │   └── main.py                   # FastAPI app entry
│   ├── migrations/
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── UploadPage.tsx
│   │   │   └── DashboardPage.tsx
│   │   ├── components/
│   │   └── App.tsx
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
└── README.md
```

---

## Technology Stack

| Layer | Technology | Rationale |
|-------|------------|-----------|
| Backend API | FastAPI (Python 3.11) | Async, auto-docs, ML-native |
| Object Detection | YOLOv8 (Ultralytics) | Best accuracy/speed for retail |
| Segmentation | SAM (Meta) | Shelf zone segmentation |
| Zero-shot Classification | CLIP (OpenAI) | Sparse label fallback |
| Depth Estimation | MiDaS | Monocular floor area proxy |
| Image Preprocessing | OpenCV | CLAHE, blur, histogram |
| Spatial Indexing | H3 (Uber) | Hexagonal grid, fast radius queries |
| Geo Operations | GeoPandas + Shapely | Polygon ops, radius aggregation |
| Geo APIs | Google Maps Platform | POIs, Roads, Places |
| Competition Data | Overpass API (OSM) | Free kirana density data |
| Population Data | WorldPop raster | 100m resolution India grids |
| ML Modeling | scikit-learn | Quantile regression, SHAP |
| Explainability | SHAP | Feature importance for loan officers |
| Database | PostgreSQL + PostGIS | Spatial query support |
| Storage | AWS S3 / GCS | Image storage |
| Report Generation | Jinja2 + WeasyPrint | PDF loan officer reports |
| Frontend | React + Vite + TypeScript | Fast, modern web UI |
| Maps (Frontend) | Leaflet.js | Store map + catchment visualization |
| Containerization | Docker + Compose | Local + cloud deployment |

---

## Build Sequence (Recommended Sprint Order)

| Sprint | Phases | Deliverable |
|--------|--------|-------------|
| **Sprint 1** | Phase 1 | Upload API + DB schema + image validation + basic React upload form |
| **Sprint 2** | Phase 2 | Vision pipeline (YOLO→CLIP→SAM→MiDaS) + VisionSignals output |
| **Sprint 3** | Phase 3 | Geo engine (catchment + footfall + competition) + GeoSignals output |
| **Sprint 4** | Phase 4 | Fraud detection rule engine (4 checkers) + FraudAssessment output |
| **Sprint 5** | Phase 5 | Fusion scorer + quantile regression CI + SHAP explainer |
| **Sprint 6** | Phase 6 | JSON output + NLG explanation + PDF report + React dashboard |

---

## Verification Plan

### Automated Tests
```bash
# Unit tests per service
pytest backend/tests/ -v

# Integration test: full pipeline with sample images
python backend/tests/integration/test_full_pipeline.py --images sample_kirana/

# API smoke test
uvicorn app.main:app --reload &
curl -X POST /api/v1/submissions -F "images=@test1.jpg" -F "gps={lat:12.9,lon:77.5}"
```

### Manual Verification
- Upload 5 real kirana store images → verify VisionSignals are plausible
- Test GPS for a known urban-dense location → verify GeoSignals match expectation
- Submit images with EXIF timestamps 2 days apart → verify temporal fraud flag fires
- Verify PDF report renders correctly in browser
- End-to-end: upload → wait for processing → view dashboard → download PDF

### Demo Checkpoint
- **Happy path**: Upload 4 kirana images + Mumbai GPS → receive ₹12,000–₹18,000/day estimate with "APPROVE" recommendation
- **Fraud path**: Upload images with mismatched EXIF + rural GPS + high inventory → receive fraud flags + "REFER_FOR_FIELD_VISIT" recommendation

---

## Risk Register

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| No kirana labeled data for YOLO fine-tuning | High | Use CLIP zero-shot as fallback; label 200 images minimum |
| Google Maps API cost overrun | Medium | Implement Redis caching for repeated GPS queries; use OSM Overpass as free fallback |
| SAM + MiDaS + YOLO too slow for real-time | Medium | Run async via Celery worker queue; return `processing` status, poll for results |
| WorldPop raster large file sizes (India = ~2GB) | Medium | Pre-tile and store in PostGIS raster table for sub-second queries |
| WeasyPrint PDF rendering issues on Windows | Low | Use Docker Linux container for PDF generation |
| EXIF stripping by mobile browsers on upload | High | Extract EXIF before S3 upload server-side; flag missing EXIF as soft fraud signal |
