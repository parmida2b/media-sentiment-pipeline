from pathlib import Path

MONITORING_ROOT = Path(__file__).resolve().parent
PIPELINE_ROOT = MONITORING_ROOT.parent
BUNDLE_ROOT = PIPELINE_ROOT.parent
STATE_DIR = MONITORING_ROOT / "state"
LOG_DIR = MONITORING_ROOT / "logs"
CONTROL_DB = STATE_DIR / "control_plane.db"
STATE_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

WEB_HOST = "127.0.0.1"
WEB_PORT = 8020
METRICS_PORT = 8003
BUILD_ID = "group-overlay-social-live-ui-20260814-08"
