"""
Natural Language Generation — Jinja2 template-based explanations.
Deterministic, auditable, no external API needed.
"""
from jinja2 import Template

EXPLANATION_TEMPLATE = Template("""
Store Analysis Summary
──────────────────────────────────────────────────────────

{% if store_name %}{{ store_name }}{% else %}This kirana store{% endif %} is located in a {{ catchment_tier | replace('_', ' ') }} area with an estimated footfall score of {{ footfall_score }}/100.

INVENTORY & SHELF ANALYSIS
The shelf density index is {{ sdi }} (scale 0–1), indicating {% if sdi >= 0.7 %}well-stocked shelves{% elif sdi >= 0.4 %}moderately stocked shelves{% else %}sparse inventory{% endif %}. {{ sku_diversity }} distinct product categories were detected, with {{ dominant_category }} as the dominant category. Estimated inventory value on display: ₹{{ "{:,.0f}".format(inventory_value) }}.

LOCATION INTELLIGENCE  
The store is situated on a {{ road_type }} road with {{ competition_count }} competing stores within 300m ({{ competition_label }}). {% if poi_count > 5 %}Nearby demand generators include {{ poi_count }} POIs such as schools, bus stops, and markets.{% else %}Limited nearby demand generators were identified.{% endif %}

CASH FLOW ESTIMATE
Estimated daily sales: ₹{{ "{:,.0f}".format(daily_low) }}–₹{{ "{:,.0f}".format(daily_high) }} (70% confidence interval)
Estimated monthly net income: ₹{{ "{:,.0f}".format(monthly_low) }}–₹{{ "{:,.0f}".format(monthly_high) }}
Blended net margin: {{ margin_pct }}% (based on detected category mix)

{% if flags %}
RISK FLAGS ({{ flag_count }} detected)
{% for flag in flags %}- {{ flag | replace('_', ' ') | title }}
{% endfor %}
{% endif %}

RECOMMENDATION: {{ recommendation | replace('_', ' ') }}
Confidence Score: {{ confidence_score }}/1.0

{% if recommendation == 'APPROVE' %}The store demonstrates consistent signals across visual inventory, location, and market context. Standard loan terms are appropriate.
{% elif recommendation == 'APPROVE_WITH_MONITORING' %}The store shows generally positive signals but with some uncertainty. Recommend quarterly check-ins and moderate loan sizing.
{% elif recommendation == 'REFER_FOR_FIELD_VISIT' %}Conflicting signals detected between image data and location context. A physical field visit by a loan officer is advised before disbursement.
{% elif recommendation == 'REJECT' %}Multiple high-confidence fraud indicators detected. This submission requires manual review and should not proceed to disbursement without verification.
{% endif %}
""".strip())


def generate_explanation(vision: dict, geo: dict, fraud: dict, cash_flow: dict, store_name: str = None, recommendation: str = "APPROVE_WITH_MONITORING") -> str:
    flags = fraud.get("flags", [])
    competition_label_map = {1.0: "healthy competition", 0.9: "moderate competition", 0.8: "saturated market", 0.85: "low competition"}

    return EXPLANATION_TEMPLATE.render(
        store_name=store_name,
        catchment_tier=geo.get("catchment_tier", "urban_sparse"),
        footfall_score=geo.get("footfall_proxy_score", 50),
        sdi=vision.get("sdi", 0.5),
        sku_diversity=vision.get("sku_diversity", 10),
        dominant_category=vision.get("dominant_category", "staples"),
        inventory_value=vision.get("inventory_value_est", 50000),
        road_type=geo.get("road_type", "residential"),
        competition_count=geo.get("competition_count", 3),
        competition_label=competition_label_map.get(geo.get("competition_factor", 1.0), "moderate competition"),
        poi_count=geo.get("poi_count", 5),
        daily_low=cash_flow.get("daily_sales_low", 8000),
        daily_high=cash_flow.get("daily_sales_high", 18000),
        monthly_low=cash_flow.get("monthly_income_low", 16000),
        monthly_high=cash_flow.get("monthly_income_high", 36000),
        margin_pct=round(cash_flow.get("blended_margin", 0.12) * 100, 1),
        flags=flags,
        flag_count=len(flags),
        recommendation=recommendation,
        confidence_score=cash_flow.get("confidence_score", 0.5),
    )
