from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, Counter, Gauge, generate_latest


REGISTRY = CollectorRegistry()

API_REQUESTS_TOTAL = Counter(
    "airq_api_requests_total",
    "Total API requests",
    ["path", "method", "status_code"],
    registry=REGISTRY,
)

DASHBOARD_REFRESH_TOTAL = Counter(
    "airq_dashboard_refresh_total",
    "Total dashboard refresh operations",
    ["source", "fallback_used"],
    registry=REGISTRY,
)

QAQC_VALID_RATE_PCT = Gauge(
    "airq_qaqc_valid_rate_pct",
    "Latest overall QA/QC valid rate percentage",
    registry=REGISTRY,
)

STALE_STATIONS = Gauge(
    "airq_stale_stations",
    "Number of stale stations at latest check",
    registry=REGISTRY,
)

ALERTS_SENT_TOTAL = Counter(
    "airq_alerts_sent_total",
    "Total outbound alert notifications",
    ["channel", "status"],
    registry=REGISTRY,
)


def render_metrics() -> tuple[bytes, str]:
    return generate_latest(REGISTRY), CONTENT_TYPE_LATEST
