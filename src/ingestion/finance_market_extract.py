"""
finance_market_extract.py - financial data extraction and preparation
Project : Global Public Opinion Analysis on the Iran-US Conflict
Window  : 2026-02-28 -> 2026-07-22  (W01-W21)
Version : 4.2 - FRED REST API verification; English-only logs/comments

Assignment requirement coverage
-----------------------------------------------------------------
  Document source and timestamp       -> Phase 2: observation_ts_utc + complete metadata
  Align frequency with project window -> Phase 5: daily + weekly W01-W21
  Handle missing values/market closure -> Phase 5: missing_reason from reference calendar
  Lag diagnostics                    -> Phase 8: frozen lags + exploratory scan
  Stationarity and common trend       -> Phase 7: ADF + KPSS
  Correlation is not causation        -> Phase 9: confounder warning

Installation
    pip install yfinance pandas numpy requests jdatetime \
                statsmodels scipy

Run
    python -m src.ingestion.finance_market_extract
"""

from __future__ import annotations

import json
import os
import time
import warnings
from dataclasses import dataclass, field, asdict
from datetime import datetime, time as dtime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import requests
from dotenv import load_dotenv

from config.config_loader import load_config

# Only known harmless warnings are suppressed. Suppressing all warnings
# would hide important statsmodels convergence and numerical warnings.
warnings.filterwarnings("ignore", message=".*test statistic is outside.*")
try:                                    # Harmless KPSS interpolation-table warning
    from statsmodels.tools.sm_exceptions import InterpolationWarning
    warnings.filterwarnings("ignore", category=InterpolationWarning)
except ImportError:
    pass
warnings.filterwarnings("ignore", category=FutureWarning, module="yfinance")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PIPELINE_CONFIG = load_config(PROJECT_ROOT / "config" / "config.yaml")

START = PIPELINE_CONFIG.date_range.start.isoformat()
END = PIPELINE_CONFIG.date_range.end.date().isoformat()
END_EXCL = (PIPELINE_CONFIG.date_range.end.date() + timedelta(days=1)).isoformat()
N_WEEKS = ((pd.Timestamp(END) - pd.Timestamp(START)).days // 7) + 1
TEDPIX_VALID_FROM = "2026-05-19"   # FD-TED-01 - pre-period stale/unusable for analysis
COLLECTOR_VERSION = "market-extract-4.2"

# FRED verification process (v4.2):
# - FRED is the external verification source.
# - FRED observations are retrieved from the official FRED REST API.
# - The registered API key is sent only to the FRED API endpoint.
# - Verification series remain separate from the primary analytical dataset.
# - FRED daily observations do not claim an exact market-close timestamp.
load_dotenv(PROJECT_ROOT / ".env")
FRED_API_KEY = os.getenv("FRED_API_KEY")
FRED_API_URL = "https://api.stlouisfed.org/fred/series/observations"

RUN_ID = os.getenv("FINANCIAL_RUN_ID") or datetime.now(timezone.utc).strftime(
    "financial-%Y%m%dT%H%M%SZ"
)
RUN_ROOT = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / PIPELINE_CONFIG.topic_id
    / "financial"
    / "runs"
    / RUN_ID
)
OUT = RUN_ROOT / "prepared"
RAW = RUN_ROOT / "raw"
AUDIT = RUN_ROOT / "audits"
RAW_PROVENANCE_PREFIX = RUN_ROOT.relative_to(PROJECT_ROOT) / "raw"
for directory in [
    OUT,
    AUDIT,
    RAW / "yahoo",
    RAW / "tgju",
    RAW / "fred",
    RAW / "tsetmc",
]:
    directory.mkdir(exist_ok=True, parents=True)
NOW = datetime.now(timezone.utc).isoformat(timespec="seconds")

GRAMS_PER_TROY_OZ = 31.1034768
PURITY_18K = 0.750

LOG: list[str] = []


def log(m: str = "") -> None:
    print(m)
    LOG.append(m)


def hdr(t: str) -> None:
    log("\n" + "=" * 70)
    log(f"  {t}")
    log("=" * 70)


# =======================================================================
# Asset registry - single source of truth for all metadata
# =======================================================================

@dataclass(frozen=True)
class Asset:
    asset_id: str
    name_fa: str
    category: str            # Required categories: fx | oil | gold | index | volatility | economic
    instrument_type: str     # futures|spot|index|yield|equity|etf|fx_rate|spread|ratio|vol_measure|crypto
    unit: str                # Physical/financial unit, separate from currency
    currency: str | None     # None for indices, yields, and ratios
    transform: str           # log_return | log_change | first_diff | none
    role: str                # core | secondary
    market: str              # global | iran_exchange | iran_otc | crypto | fx24
    tier: int
    price_type: str          # vendor_close | adjusted_close | index_level | yield | derived
                             # We do not claim settlement prices; Yahoo Close is not necessarily
                             # the official exchange settlement price and has not been verified as such.
    source: str
    source_series_id: str
    endpoint: str
    close_local: dtime | None = None
    tz: str | None = None
    ts_exact: bool = True
    instrument_variant: str | None = None
    auto_adjust: bool = False       # Only equities and ETFs use dividend-adjusted prices
    notes: str = ""


NY, LDN, TLV, TEH = ("America/New_York", "Europe/London",
                     "Asia/Jerusalem", "Asia/Tehran")
YF = "yfinance/yahoo-chart"

# Transformation contract
# log_return: strictly positive price series
# log_change: positive non-price level (VIX, OVX, realized volatility)
# first_diff: yields and spreads that may be zero or negative
# none: no transformation

ASSETS: dict[str, Asset] = {a.asset_id: a for a in [

    # Foreign exchange
    Asset("DXY", "U.S. Dollar Index", "fx", "index", "index_points", None,
          "log_return", "secondary", "global", 2, "index_level",
          "yahoo", "DX-Y.NYB", YF, dtime(17, 0), NY),
    Asset("EURUSD", "EUR/USD", "fx", "fx_rate", "USD_per_EUR", None,
          "log_return", "secondary", "fx24", 3, "close",
          "yahoo", "EURUSD=X", YF, dtime(17, 0), NY,
          notes="24/5 market - Sunday 22:00 UTC to Friday 22:00 UTC"),
    Asset("IRR_USD", "USD/IRR - free market", "fx", "spot", "IRR_per_USD", "IRR",
          "log_return", "core", "iran_otc", 1, "close",
          "tgju", "price_dollar_rl", "tgju.org/archive-tool",
          dtime(20, 0), TEH, ts_exact=False, instrument_variant="free_market",
          notes=" Free-market rate - do not mix with official or NIMA rates"),

    # Oil prices
    Asset("OIL_BRENT", "Brent crude oil (front-month futures)", "oil", "futures",
          "USD_per_barrel", "USD", "log_return", "core", "global", 1,
          "vendor_close", "yahoo", "BZ=F", YF, dtime(19, 30), LDN,
          instrument_variant="front_month_future"),
    Asset("OIL_WTI", "WTI crude oil (front-month futures)", "oil", "futures",
          "USD_per_barrel", "USD", "log_return", "secondary", "global", 2,
          "vendor_close", "yahoo", "CL=F", YF, dtime(14, 30), NY,
          instrument_variant="front_month_future"),

    # Gold
    Asset("GOLD_USD", "Gold futures", "gold", "futures", "USD_per_troy_oz", "USD",
          "log_return", "core", "global", 1, "vendor_close",
          "yahoo", "GC=F", YF, dtime(13, 30), NY,
          instrument_variant="front_month_future"),
    Asset("IRR_GOLD18", "18K gold", "gold", "spot", "IRR_per_gram", "IRR",
          "log_return", "core", "iran_otc", 2, "close",
          "tgju", "geram18", "tgju.org/archive-tool", dtime(20, 0), TEH,
          ts_exact=False, instrument_variant="free_market"),
    Asset("IRR_GOLD24", "24K gold", "gold", "spot", "IRR_per_gram", "IRR",
          "log_return", "secondary", "iran_otc", 3, "close",
          "tgju", "geram24", "tgju.org/archive-tool", dtime(20, 0), TEH,
          ts_exact=False, instrument_variant="free_market"),
    Asset("IRR_COIN", "Bahar Azadi full coin", "gold", "spot", "IRR_per_coin", "IRR",
          "log_return", "secondary", "iran_otc", 2, "close",
          "tgju", "sekeb", "tgju.org/archive-tool", dtime(20, 0), TEH,
          ts_exact=False, instrument_variant="free_market"),
    Asset("IRR_COIN_G", "Gram gold coin", "gold", "spot", "IRR_per_coin", "IRR",
          "log_return", "secondary", "iran_otc", 3, "close",
          "tgju", "gerami", "tgju.org/archive-tool", dtime(20, 0), TEH,
          ts_exact=False, instrument_variant="free_market"),

    # Market indices
    Asset("SP500", "S&P 500", "index", "index", "index_points", None,
          "log_return", "secondary", "global", 2, "index_level",
          "yahoo", "^GSPC", YF, dtime(16, 0), NY),
    Asset("TA125", "Tel Aviv TA-125 Index", "index", "index", "index_points", None,
          "log_return", "secondary", "global", 3, "index_level",
          "yahoo", "^TA125.TA", YF, dtime(17, 25), TLV),
    Asset("TEDPIX", "Tehran Stock Exchange TEDPIX", "index", "index", "index_points", None,
          "log_return", "core", "iran_exchange", 2, "index_level",
          "tsetmc", "32097828799138957", "cdn.tsetmc.com/api/Index",
          dtime(12, 30), TEH),

    # Risk and volatility indices
    Asset("VIX", "S&P 500 Volatility Index", "volatility", "index", "index_points", None,
          "log_change", "core", "global", 1, "index_level",
          "yahoo", "^VIX", YF, dtime(16, 15), NY),
    Asset("OVX", "Oil Volatility Index", "volatility", "index", "index_points", None,
          "log_change", "core", "global", 1, "index_level",
          "yahoo", "^OVX", YF, dtime(16, 15), NY,
          notes="Oil-specific volatility measure; more relevant to Hormuz risk than broad VIX"),

    # Related economic indicators
    Asset("UST10Y", "U.S. 10-Year Treasury Yield", "economic", "yield", "percent", None,
          "first_diff", "secondary", "global", 3, "yield",
          "yahoo", "^TNX", YF, dtime(16, 0), NY,
          notes=" This is a percentage yield, not a price; use first difference, not log return"),
    Asset("GAS_NG", "Natural gas futures", "economic", "futures",
          "USD_per_MMBtu", "USD", "log_return", "secondary", "global", 2,
          "vendor_close", "yahoo", "NG=F", YF, dtime(14, 30), NY),
    Asset("TANKER_FRO", "Frontline", "economic", "equity", "USD_per_share",
          "USD", "log_return", "secondary", "global", 2, "adjusted_close",
          "yahoo", "FRO", YF, dtime(16, 0), NY, auto_adjust=True,
          notes="auto_adjust is required because variable dividends can be material"),
    Asset("TANKER_STNG", "Scorpio Tankers", "economic", "equity",
          "USD_per_share", "USD", "log_return", "secondary", "global", 2,
          "adjusted_close", "yahoo", "STNG", YF, dtime(16, 0), NY, auto_adjust=True),
    Asset("TANKER_DHT", "DHT Holdings", "economic", "equity", "USD_per_share",
          "USD", "log_return", "secondary", "global", 2, "adjusted_close",
          "yahoo", "DHT", YF, dtime(16, 0), NY, auto_adjust=True),
    Asset("DEFENSE", "Defense industry ETF", "economic", "etf", "USD_per_share",
          "USD", "log_return", "secondary", "global", 3, "adjusted_close",
          "yahoo", "ITA", YF, dtime(16, 0), NY, auto_adjust=True),

    # 24/7 assets
    # Only assets that trade on weekends. EV-001 marks the conflict start.
    # February 28 was a Saturday, so same-day market reactions are visible only here.
    Asset("BTC", "Bitcoin", "economic", "crypto", "USD_per_BTC", "USD",
          "log_return", "secondary", "crypto", 3, "close",
          "yahoo", "BTC-USD", YF, dtime(0, 0), "UTC",
          notes="24/7 market - covers weekend events"),
    Asset("ETH", "Ethereum", "economic", "crypto", "USD_per_ETH", "USD",
          "log_return", "secondary", "crypto", 3, "close",
          "yahoo", "ETH-USD", YF, dtime(0, 0), "UTC",
          notes="24/7"),
]}

# Verification series - never included in the analytical dataset
VERIFY: dict[str, Asset] = {a.asset_id: a for a in [
    Asset("OIL_BRENT__FRED", "Brent Europe FOB spot", "verify", "spot",
          "USD_per_barrel", "USD", "log_return", "verify", "global", 9,
          "close", "fred", "DCOILBRENTEU", "api.stlouisfed.org/fred/series/observations",
          None, None, ts_exact=False, instrument_variant="spot_fob",
          notes=" Spot series, not futures; the level is not directly comparable with BZ=F"),
    Asset("OIL_WTI__FRED", "WTI Cushing spot", "verify", "spot",
          "USD_per_barrel", "USD", "log_return", "verify", "global", 9,
          "close", "fred", "DCOILWTICO", "api.stlouisfed.org/fred/series/observations",
          None, None, ts_exact=False, instrument_variant="spot_cushing"),
    Asset("VIX__FRED", "VIX - CBOE", "verify", "index", "index_points", None,
          "log_change", "verify", "global", 9, "index_level",
          "fred", "VIXCLS", "api.stlouisfed.org/fred/series/observations", None, None,
          ts_exact=False),
    Asset("UST10Y__FRED", "U.S. 10-Year Treasury", "verify", "yield", "percent", None,
          "first_diff", "verify", "global", 9, "yield",
          "fred", "DGS10", "api.stlouisfed.org/fred/series/observations", None, None,
          ts_exact=False),
]}

# Cross-source verification
# mode="level" only when instrument_type is the same
# mode="return" when instruments differ; compare returns, not levels
# The thresholds below are operational QA checks for anomaly detection,
# not inferential/statistical standards. Record them in the decision log.
CROSSCHECK = [
    ("VIX",       "VIX__FRED",         "level",  0.02),
    ("UST10Y",    "UST10Y__FRED",      "level",  0.05),
    ("OIL_BRENT", "OIL_BRENT__FRED",   "return", 0.90),
    ("OIL_WTI",   "OIL_WTI__FRED",     "return", 0.90),
]

# Reference calendar for each market
REFERENCE = {
    "global":         "SP500",
    "iran_exchange":  "TEDPIX",
    "iran_otc":       "IRR_USD",  # Inferred; TGJU is not an official trading calendar
    "fx24":           "EURUSD",   # FX uses its own calendar, not the U.S. equity calendar
    "crypto":         None,          # All calendar days
}

NOWRUZ = ("2026-03-18", "2026-04-03")

HEADERS = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36"),
           "Accept": "application/json, text/plain, */*"}


# =======================================================================
# Phase 2 - Timestamp and metadata
# =======================================================================

def obs_ts(date_str: str, a: Asset) -> str | None:
    """
    Exact UTC timestamp represented by this observation.

    Returns None when the exact time is genuinely unknown (for example FRED daily series).
    Do not claim timestamp precision that the source does not provide.
    """
    if not a.ts_exact or a.close_local is None or a.tz is None:
        return None
    d = datetime.strptime(date_str, "%Y-%m-%d").date()
    local = datetime.combine(d, a.close_local, tzinfo=ZoneInfo(a.tz))
    return local.astimezone(timezone.utc).isoformat(timespec="seconds")


def mk(date, a: Asset, value, raw_file: str = "", volume=np.nan,
       http_status: int | None = None, observed_keys: str = "") -> dict:
    ds = pd.to_datetime(date).strftime("%Y-%m-%d")
    return {
        # Time identity: local trading date plus UTC timestamp when exact
        "observation_date": ds,
        "observation_ts_utc": obs_ts(ds, a),
        "ts_is_exact": a.ts_exact,
        "close_local": a.close_local.strftime("%H:%M") if a.close_local else None,
        "timezone": a.tz,
        # Asset identity
        "asset_id": a.asset_id,
        "asset_name": a.name_fa,
        "category": a.category,
        "instrument_type": a.instrument_type,
        "instrument_variant": a.instrument_variant,
        "price_type": a.price_type,
        "market": a.market,
        "role": a.role,
        "tier": a.tier,
        # Value; unit is separate from currency
        "value": float(value),
        "unit": a.unit,
        "currency": a.currency,
        "volume": volume,
        "transform": a.transform,
        # Provenance
        "source": a.source,
        "source_series_id": a.source_series_id,
        "endpoint": a.endpoint,
        "raw_file": raw_file,
        "collector_version": COLLECTOR_VERSION,
        "retrieved_at_utc": NOW,
        "http_status": http_status,
        "observed_keys": observed_keys,
        "notes": a.notes,
    }


# =======================================================================
# Phase 3 - Extraction
# =======================================================================

def _yahoo_group(assets: list[Asset], label: str) -> pd.DataFrame:
    import yfinance as yf
    rows = []
    for a in assets:
        try:
            df = yf.download(a.source_series_id, start=START, end=END_EXCL,
                             progress=False, auto_adjust=a.auto_adjust,
                             multi_level_index=False)
            if df is None or df.empty:
                log(f"   {a.asset_id:15s} {a.source_series_id:11s} empty")
                continue
            df = df.dropna(subset=["Close"])
            rf = Path("yahoo") / f"yahoo_{a.asset_id}.csv"
            df.to_csv(RAW / rf)
            for d, r in df.iterrows():
                rows.append(mk(d, a, r["Close"], str(RAW_PROVENANCE_PREFIX / rf),
                               volume=float(r.get("Volume", np.nan) or np.nan),
                               http_status=200,
                               observed_keys="|".join(map(str, df.columns))))
            tzs = a.tz.split("/")[-1] if a.tz else "-"
            cl = a.close_local.strftime("%H:%M") if a.close_local else "-"
            log(f"   {a.asset_id:15s} {a.source_series_id:11s} {len(df):3d} observations  "
                f"{cl} {tzs:12s} {a.price_type}")
        except Exception as e:
            log(f"   {a.asset_id:15s} {a.source_series_id:11s} {type(e).__name__}: {e}")
        time.sleep(0.4)
    return pd.DataFrame(rows)


def fetch_yahoo() -> pd.DataFrame:
    hdr("Phase 3A - Yahoo Finance")
    log("  Each symbol is fetched separately so every market keeps its own trading calendar.")
    log("  auto_adjust is enabled only for equities and ETFs to account for dividends.")
    log("  auto_adjust is disabled for indices, futures, FX, and crypto.")
    log("  price_type is recorded for every observation.\n")
    return _yahoo_group([a for a in ASSETS.values() if a.source == "yahoo"], "yahoo")


def fetch_fred() -> pd.DataFrame:
    """
    Retrieve verification series directly from the official FRED REST API.

    Process:
    1. Request each registered FRED series for the project date window.
    2. Authenticate with the registered FRED API key.
    3. Keep only valid numeric observations; FRED uses "." for missing values.
    4. Save each raw FRED response as a CSV file for auditability.
    5. Convert valid observations into the common project schema with mk().
    6. Keep FRED data in the verification layer only; it never enters the
       primary analytical source dataset.
    """
    if not FRED_API_KEY:
        raise RuntimeError(
            "FRED_API_KEY is not configured. Set it in the local .env file "
            "before running the financial collector."
        )

    hdr("Phase 3B - FRED verification")
    log("  Source: official FRED REST API.")
    log("  FRED is used only for source verification.")
    log("  observation_ts_utc is None because FRED daily series do not provide")
    log("  an exact market-close timestamp.\n")

    rows = []

    for a in [v for v in VERIFY.values() if v.source == "fred"]:
        params = {
            "series_id": a.source_series_id,
            "api_key": FRED_API_KEY,
            "file_type": "json",
            "observation_start": START,
            "observation_end": END,
        }

        try:
            r = requests.get(
                FRED_API_URL,
                params=params,
                headers=HEADERS,
                timeout=30,
            )
            r.raise_for_status()
            payload = r.json()
            observations = payload.get("observations", [])

            valid_records = []
            for obs in observations:
                value = obs.get("value")
                if value in (None, "", "."):
                    continue

                try:
                    numeric_value = float(value)
                except (TypeError, ValueError):
                    continue

                date_str = obs.get("date")
                if not date_str:
                    continue

                valid_records.append(
                    {
                        "date": date_str,
                        "value": numeric_value,
                        "realtime_start": obs.get("realtime_start"),
                        "realtime_end": obs.get("realtime_end"),
                    }
                )

            if not valid_records:
                log(
                    f"  FRED {a.asset_id:20s} {a.source_series_id:14s}: "
                    "no valid observations returned"
                )
                continue

            raw_df = pd.DataFrame(valid_records)
            rf = Path("fred") / f"fred_{a.asset_id}.csv"
            raw_df.to_csv(RAW / rf, index=False)

            for rec in valid_records:
                rows.append(
                    mk(
                        rec["date"],
                        a,
                        rec["value"],
                        str(RAW_PROVENANCE_PREFIX / rf),
                        http_status=r.status_code,
                        observed_keys="date|value|realtime_start|realtime_end",
                    )
                )

            log(
                f"  FRED {a.asset_id:20s} {a.source_series_id:14s}: "
                f"{len(valid_records):3d} observations [{a.instrument_variant}]"
            )

        except requests.exceptions.RequestException as e:
            log(
                f"  FRED {a.asset_id:20s} {a.source_series_id:14s}: "
                f"HTTP error - {type(e).__name__}: {e}"
            )
        except ValueError as e:
            log(
                f"  FRED {a.asset_id:20s} {a.source_series_id:14s}: "
                f"JSON parsing error - {e}"
            )

        time.sleep(0.3)

    return pd.DataFrame(rows)

def _jalali_range(a: str, b: str):
    import jdatetime
    d0 = jdatetime.date.fromgregorian(date=datetime.strptime(a, "%Y-%m-%d").date())
    d1 = jdatetime.date.fromgregorian(date=datetime.strptime(b, "%Y-%m-%d").date())
    while d0 <= d1:
        yield d0
        d0 += jdatetime.timedelta(days=1)


def _tgju_one(sess, series_id, jd) -> dict | None:
    """Record HTTP status, observed keys, and failure reason."""
    p = {"act": "archive-tool", "noview": "", "client": "ajax", "v": 200,
         "name": series_id, "year": jd.year, "month": jd.month, "day": jd.day}
    try:
        r = sess.get("https://www.tgju.org/", params=p, timeout=30)
        status = r.status_code
        r.raise_for_status()
        data = r.json()
    except requests.exceptions.RequestException as e:
        return {"fail": f"http:{type(e).__name__}", "status": None}
    except ValueError:
        return {"fail": "json_decode", "status": status}

    rec = None
    if isinstance(data, list) and data and isinstance(data[0], dict):
        rec = data[0]
    elif isinstance(data, dict):
        inner = data.get("data", data)
        rec = inner if isinstance(inner, dict) else (
            inner[0] if isinstance(inner, list) and inner
            and isinstance(inner[0], dict) else None)
    if not rec:
        return {"fail": "no_record", "status": status}

    price = rec.get("price") or rec.get("value") or rec.get("close")
    if price in (None, "", "-"):
        return {"fail": "no_price_field", "status": status,
                "keys": "|".join(sorted(rec.keys()))}
    try:
        price = float(str(price).replace(",", ""))
    except ValueError:
        return {"fail": "unparseable_price", "status": status}
    return {"g": jd.togregorian().strftime("%Y-%m-%d"), "price": price,
            "status": status, "keys": "|".join(sorted(rec.keys())), "raw": rec}


def fetch_tgju(delay: float = 0.4) -> pd.DataFrame:
    hdr("Phase 3C - tgju.org (Iran)")
    log("  access_method = unofficial_web_endpoint")
    log("   This step may take about 15 minutes; the complete raw response is stored.\n")
    rows, dumps, fails = [], [], {}
    with requests.Session() as s:
        s.headers.update({**HEADERS, "Referer": "https://www.tgju.org/"})
        for a in [x for x in ASSETS.values() if x.source == "tgju"]:
            n = 0
            for jd in _jalali_range(START, END):
                rec = _tgju_one(s, a.source_series_id, jd)
                if rec and "price" in rec:
                    rows.append(mk(
                        rec["g"], a, rec["price"],
                        str(RAW_PROVENANCE_PREFIX / "tgju" / "tgju_raw.json"),
                                   http_status=rec.get("status"),
                                   observed_keys=rec.get("keys", "")))
                    dumps.append({"asset_id": a.asset_id, **rec})
                    n += 1
                elif rec:
                    fails[rec["fail"]] = fails.get(rec["fail"], 0) + 1
                time.sleep(delay)
            log(f"  {'' if n else ''} {a.asset_id:15s} "
                f"{a.source_series_id:16s} {n:3d} observations  [{a.instrument_variant}]")
    (RAW / "tgju" / "tgju_raw.json").write_text(
        json.dumps(dumps, ensure_ascii=False, default=str), encoding="utf-8")
    if fails:
        log(f"\n  Reasons for missing records: {fails}")
        log("   no_record may indicate a market closure, but without confirmation from")
        log("     the reference calendar it must not be treated as a confirmed closure; it may be")
        log("     an archive gap, source outage, or API behavior change.")
    log("\n  ts_is_exact=False because TGJU updates continuously; 20:00 Tehran is an explicit assumption.")
    return pd.DataFrame(rows)


def fetch_tedpix() -> pd.DataFrame:
    hdr("Phase 3D - TSETMC")
    a = ASSETS["TEDPIX"]
    urls = [f"https://cdn.tsetmc.com/api/Index/GetIndexB2History/{a.source_series_id}",
            f"http://old.tsetmc.com/tsev2/chart/data/IndexFinancial.aspx?i={a.source_series_id}&t=value",
            f"http://www.tsetmc.com/tsev2/chart/data/IndexFinancial.aspx?i={a.source_series_id}&t=value"]
    for u in urls:
        try:
            r = requests.get(u, headers=HEADERS, timeout=30)
            r.raise_for_status()
            recs = []
            if "api/Index" in u:
                for it in r.json().get("indexB2", []):
                    d = str(it["dEven"])
                    recs.append((f"{d[:4]}-{d[4:6]}-{d[6:]}",
                                 float(it["xNivInuClMresIbs"])))
            else:
                for part in r.text.strip().split(";"):
                    if part.strip():
                        dt, val = part.split(",")[:2]
                        recs.append((dt.replace("/", "-"), float(val)))
            recs = [(d, v) for d, v in recs if START <= d <= END]
            if not recs:
                continue
            (RAW / "tsetmc" / "tedpix_raw.txt").write_text(r.text[:300_000], encoding="utf-8")
            log(f"   TEDPIX {len(recs)} observations <- {u.split('/')[2]}")
            return pd.DataFrame([mk(d, a, v, str(RAW_PROVENANCE_PREFIX / "tsetmc" / "tedpix_raw.txt"),
                                    http_status=r.status_code) for d, v in recs])
        except Exception as e:
            log(f"  ... {u.split('/')[2]}: {type(e).__name__}")
    try:                                    # Fourth fallback route
        from pytse_client import download_financial_indexes
        dd = download_financial_indexes(symbols=["\u0634\u0627\u062e\u0635 \u0643\u0644"], write_to_csv=False)
        df = list(dd.values())[0]
        if not isinstance(df.index, pd.DatetimeIndex):
            df = df.set_index(pd.to_datetime(df.iloc[:, 0]))
        col = "value" if "value" in df.columns else df.select_dtypes("number").columns[-1]
        recs = [(i.strftime("%Y-%m-%d"), float(v)) for i, v in df[col].items()
                if START <= i.strftime("%Y-%m-%d") <= END]
        if recs:
            (RAW / "tsetmc" / "tedpix_pytse.csv").write_text(
                "date,value\n" + "\n".join(f"{d},{v}" for d, v in recs),
                encoding="utf-8")
            log(f"   TEDPIX {len(recs)} observations <- pytse-client")
            return pd.DataFrame([mk(d, a, v, str(RAW_PROVENANCE_PREFIX / "tsetmc" / "tedpix_pytse.csv"))
                                 for d, v in recs])
    except ImportError:
        log("  pytse-client is not installed; run: pip install pytse-client")
    except Exception as e:
        log(f"  ... pytse-client: {type(e).__name__}: {e}")

    log("   All TEDPIX routes failed; the Iran reference calendar will fall back to IRR_USD.")
    log("     Alternative: pip install pytse-client")
    log("     >>> from pytse_client import download_financial_indexes")
    log("     >>> download_financial_indexes(symbols=[\'\\u0634\\u0627\\u062e\\u0635 \\u0643\\u0644\'], write_to_csv=True)")
    return pd.DataFrame()


# =======================================================================
# Phase 4 - Derived features
# =======================================================================

DERIVED_META = {
    "SPREAD_BRENT_WTI": Asset(
        "SPREAD_BRENT_WTI", "Brent-WTI spread", "oil", "spread",
        "USD_per_barrel", "USD", "first_diff", "core", "global", 1,
        "derived", "derived", "OIL_BRENT - OIL_WTI", "internal",
        dtime(16, 0), NY,
        notes=" Can be negative; use first difference, never a logarithmic transform"),
    "RV_BRENT_10D": Asset(
        "RV_BRENT_10D", "Brent 10-day realized volatility", "volatility",
        "vol_measure", "annualised_sd", None, "log_change", "secondary",
        "global", 2, "derived", "derived",
        "std(logret OIL_BRENT,10)*sqrt(252)", "internal", dtime(16, 0), NY),
    "IRR_IMPLIED_USD": Asset(
        "IRR_IMPLIED_USD", "Gold-implied USD/IRR rate", "fx", "ratio",
        "IRR_per_USD", "IRR", "log_return", "core", "iran_otc", 1,
        "derived", "derived",
        "IRR_GOLD18 / (GOLD_USD * 0.75 / 31.1034768)", "internal",
        dtime(20, 0), TEH, ts_exact=False, instrument_variant="implied",
        notes="Units are normalized so the series is comparable with observed IRR_USD"),
    "TANKER_BASKET": Asset(
        "TANKER_BASKET", "Tanker basket", "economic", "index", "index_base100",
        None, "log_return", "core", "global", 2, "derived", "derived",
        "mean(FRO,STNG,DHT) normalised", "internal", dtime(16, 0), NY,
        notes="Free proxy for tanker/shipping performance and Hormuz risk"),
}


def build_derived(wide: pd.DataFrame) -> pd.DataFrame:
    hdr("Phase 4 - Derived features")
    rows = []

    def add(s: pd.Series, aid: str):
        a = DERIVED_META[aid]
        s = s.dropna()
        if s.empty:
            log(f"   {aid:20s} insufficient data")
            return
        for d, v in s.items():
            rows.append(mk(d, a, v, "", http_status=None))
        log(f"   {aid:20s} {len(s):3d} observations  transform={a.transform}")

    if {"OIL_BRENT", "OIL_WTI"} <= set(wide.columns):
        add(wide["OIL_BRENT"] - wide["OIL_WTI"], "SPREAD_BRENT_WTI")

    if "OIL_BRENT" in wide.columns:
        # Fix: holiday NaNs could prevent rolling(10) from producing valid observations.
        # Drop missing observations first, then apply the rolling window.
        lr = np.log(wide["OIL_BRENT"].dropna()).diff()
        add(lr.rolling(10).std() * np.sqrt(252), "RV_BRENT_10D")

    # Normalize units so the implied exchange rate is interpretable.
    if {"IRR_GOLD18", "GOLD_USD"} <= set(wide.columns):
        usd_per_gram_18k = wide["GOLD_USD"] * PURITY_18K / GRAMS_PER_TROY_OZ
        add(wide["IRR_GOLD18"] / usd_per_gram_18k, "IRR_IMPLIED_USD")
        log(f"     <- 18K gold = {PURITY_18K:.0%} pure ; "
            f"1 troy ounce = {GRAMS_PER_TROY_OZ:.4f} grams")

    # No backward fill; use the first genuinely common observation date.
    tk = [c for c in ("TANKER_FRO", "TANKER_STNG", "TANKER_DHT") if c in wide]
    if len(tk) >= 2:
        sub = wide[tk]
        full = sub.dropna(how="any")          # Base date must have complete member observations.
        if full.empty:
            log("  TANKER_BASKET: no date has complete observations for all members; basket not created")
        else:
            base_date = full.index[0]
            base = sub.loc[base_date]
            members = sub.notna().sum(axis=1)
            log(f"     <- base: {base_date.date()} with {int(members.loc[base_date])} members"
                f" (without bfill)")
            log(f"     <- member availability over the period: "
                f"{members.value_counts().sort_index().to_dict()}")
            add(sub.div(base).mean(axis=1), "TANKER_BASKET")
            global BASKET_MEMBERS
            BASKET_MEMBERS = members.rename("basket_member_count")
    return pd.DataFrame(rows)


# =======================================================================
# Phase 5 - Calendar, market closures, and missingness
# =======================================================================

def clean_raw_for_analysis(raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Apply analysis-only exclusions while preserving ``financial_raw.csv`` unchanged.

    Rules currently frozen in the project decision log:
      - TGJU/iran_otc Friday carry-forwards are not analytical observations.
      - TEDPIX before TEDPIX_VALID_FROM is stale/unusable for analysis (FD-TED-01).

    Returns
    -------
    analytical_raw : pd.DataFrame
        Source observations allowed to enter derived features and analysis.
    exclusions : pd.DataFrame
        Audit trail with the removed source rows and ``cleaning_reason``.
    """
    if raw.empty:
        return raw.copy(), pd.DataFrame()

    d = raw.copy()
    dates = pd.to_datetime(d["observation_date"])
    reasons = pd.Series(pd.NA, index=d.index, dtype="object")

    iran_otc_ids = {a.asset_id for a in ASSETS.values() if a.market == "iran_otc"}
    friday = d["asset_id"].isin(iran_otc_ids) & (dates.dt.dayofweek == 4)
    reasons.loc[friday] = "invalidated_by_cleaning:tgju_friday_carry_forward"

    stale_tedpix = ((d["asset_id"] == "TEDPIX") &
                    (dates < pd.Timestamp(TEDPIX_VALID_FROM)))
    reasons.loc[stale_tedpix] = "invalidated_by_cleaning:tedpix_stale_pre_valid_from"

    excluded = d.loc[reasons.notna()].copy()
    if not excluded.empty:
        excluded["cleaning_reason"] = reasons.loc[excluded.index].values
        log(f"   analysis cleaning: {len(excluded)} source observations excluded")
        for reason, n in excluded["cleaning_reason"].value_counts().items():
            log(f"     {reason}: {n}")

    analytical = d.loc[reasons.isna()].copy()
    return analytical, excluded.reset_index(drop=True)


def drop_iran_friday(wide: pd.DataFrame) -> pd.DataFrame:
    """Backward-compatible helper. Prefer ``clean_raw_for_analysis`` upstream."""
    iran = [a.asset_id for a in ASSETS.values() if a.market == "iran_otc"]
    cols = [c for c in iran if c in wide.columns]
    if not cols:
        return wide
    w = wide.copy()
    w.loc[w.index.dayofweek == 4, cols] = np.nan
    return w


def project_week(d) -> str:
    s, t = pd.Timestamp(START), pd.Timestamp(d)
    return "OUT" if not (s <= t <= pd.Timestamp(END)) else f"W{(t-s).days//7+1:02d}"


def build_calendar_panel(df: pd.DataFrame, exclusions: pd.DataFrame | None = None) -> pd.DataFrame:
    """
    Build one row for each asset-by-calendar-day combination with a missing_reason.

    The expected calendar is inferred from a reference asset in the same market,
    rather than from a manually maintained holiday list.
    """
    hdr("Phase 5 - Market calendar and missing-value classification")
    log("  market_closed: the reference market also had no observation that day")
    log("  source_gap: the market was open but the direct source has no observation")
    log("  dependency_missing: a derived feature could not be built because an input was missing")
    log("  rolling_window_warmup: the rolling feature does not yet have enough history")
    log("  invalidated_by_cleaning: a raw source observation was removed by the cleaning contract")
    log("   No values are interpolated.")
    log("  calendar_confidence: Iranian market calendars are inferred from a reference asset,")
    log("    not from an official calendar. If the reference source fails on a day,")
    log("    that day may be incorrectly classified as market_closed.\n")

    all_days = pd.date_range(START, END, freq="D")
    obs = {aid: set(pd.to_datetime(g.observation_date))
           for aid, g in df.groupby("asset_id")}
    excluded_map: dict[str, set] = {}
    if exclusions is not None and not exclusions.empty:
        excluded_map = {aid: set(pd.to_datetime(g.observation_date))
                        for aid, g in exclusions.groupby("asset_id")}

    ref_cal: dict[str, set] = {}
    conf: dict[str, str] = {}
    for mkt, ref in REFERENCE.items():
        if ref is None:
            ref_cal[mkt] = set(all_days)
            src = "all calendar days"
        elif ref in obs and obs[ref]:
            cal = set(obs[ref])
            if mkt == "iran_otc":               # Friday is closed
                cal = {d for d in cal if d.dayofweek != 4}
            ref_cal[mkt] = cal
            src = f"inferred from {ref}" + (" excluding Fridays" if mkt == "iran_otc" else "")
        else:                                  # Reference unavailable; use same-market union.
            same = [a for a in ASSETS.values() if a.market == mkt]
            u = set().union(*[obs.get(a.asset_id, set()) for a in same]) or set(all_days)
            ref_cal[mkt] = u
            src = f"{ref} unavailable; using union of assets in the same market"
        conf[mkt] = ("official" if ref is None else
                     "reference_inferred" if (ref in obs and obs[ref])
                     else "fallback_inferred")
        log(f"  {mkt:15s} {len(ref_cal[mkt]):3d} open days   "
            f"[{conf[mkt]}]  ({src})")

    rows = []
    registry = {**ASSETS, **DERIVED_META}
    for aid, have in obs.items():
        a = registry.get(aid)
        if a is None:                          # verification series
            continue
        cal = ref_cal.get(a.market, set(all_days))
        excluded_days = excluded_map.get(aid, set())
        first_obs = min(have) if have else None
        for d in all_days:
            if d in have:
                reason = "observed"
            elif d in excluded_days:
                reason = "invalidated_by_cleaning"
            elif d not in cal:
                reason = "market_closed"
            elif aid == "RV_BRENT_10D" and first_obs is not None and d < first_obs:
                reason = "rolling_window_warmup"
            elif aid in DERIVED_META:
                reason = "dependency_missing"
            else:
                reason = "source_gap"
            rows.append({"observation_date": d.strftime("%Y-%m-%d"),
                         "asset_id": aid, "market": a.market,
                         "project_week": project_week(d),
                         "market_open": d in cal,
                         "has_observation": d in have,
                         "missing_reason": reason,
                         "calendar_confidence": conf.get(a.market, "unknown")})
    panel = pd.DataFrame(rows)

    log("\n  -- Breakdown by asset --")
    piv = (panel.pivot_table(index="asset_id", columns="missing_reason",
                             values="observation_date", aggfunc="count")
                .fillna(0).astype(int))
    reason_cols = ("observed", "market_closed", "source_gap", "dependency_missing",
                   "rolling_window_warmup", "invalidated_by_cleaning")
    for c in reason_cols:
        if c not in piv:
            piv[c] = 0
    log(piv[list(reason_cols)].to_string())

    bad = piv[piv.source_gap > 5].sort_values("source_gap", ascending=False)
    if not bad.empty:
        log("\n  Source gaps longer than 5 days (not market closures; data are missing):")
        log(bad[["source_gap"]].to_string())

    log(f"\n  -- Nowruz window {NOWRUZ[0]} -> {NOWRUZ[1]} --")
    nz = panel[(panel.observation_date >= NOWRUZ[0])
               & (panel.observation_date <= NOWRUZ[1])
               & (panel.market.str.startswith("iran"))]
    if not nz.empty:
        log(nz.groupby(["asset_id", "missing_reason"]).size().to_string())
    log("  These gaps are market_closed; never interpolate them.")
    return panel


# =======================================================================
# Phase 6 - Transformation and frequency alignment
# =======================================================================

def apply_transform(s: pd.Series, kind: str, aid: str) -> pd.Series | None:
    s = s.dropna()
    if len(s) < 3:
        return None
    if kind in ("log_return", "log_change"):
        if (s <= 0).any():
            log(f"   {aid}: {int((s <= 0).sum())} values <= 0 - "
                f"{kind} invalid; falling back to first_diff")
            return s.diff()
        return np.log(s).diff()
    if kind == "first_diff":
        return s.diff()
    return s


def build_features(wide: pd.DataFrame) -> pd.DataFrame:
    hdr("Phase 6 - Transformation contract")
    log("  Each asset follows its own transformation contract; applying one np.log() to all series is incorrect.\n")
    registry = {**ASSETS, **DERIVED_META}
    out = {}
    for c in wide.columns:
        a = registry.get(c)
        if a is None:
            continue
        t = apply_transform(wide[c], a.transform, c)
        if t is not None:
            out[f"{a.transform}__{c}"] = t
    feat = pd.DataFrame(out).sort_index()

    summ = pd.DataFrame([
        {"asset_id": c, "instrument": registry[c].instrument_type,
         "unit": registry[c].unit, "transform": registry[c].transform}
        for c in wide.columns if c in registry])
    log(summ.sort_values(["transform", "asset_id"]).to_string(index=False))
    return feat


def build_weekly(wide: pd.DataFrame, panel: pd.DataFrame) -> pd.DataFrame:
    hdr("Phase 6B - Alignment with the social-media window (W01-W21)")
    order = [f"W{i:02d}" for i in range(1, N_WEEKS + 1)]

    # Count observations separately for each asset, not from the pooled panel.
    cnt = (panel[panel.has_observation]
           .pivot_table(index="project_week", columns="asset_id",
                        values="observation_date", aggfunc="count")
           .reindex(order).fillna(0).astype(int))
    cnt.columns = [f"{c}__n_obs" for c in cnt.columns]

    w = wide.copy()
    w["project_week"] = [project_week(d) for d in w.index]
    last = w[w.project_week != "OUT"].groupby("project_week").last().reindex(order)

    wk = last.join(cnt)
    core = [c for c in ("OIL_BRENT__n_obs", "VIX__n_obs", "IRR_USD__n_obs",
                        "TEDPIX__n_obs") if c in wk.columns]
    if core:
        log("  Number of observations for core assets in each week:")
        log(wk[core].to_string())
        thin = wk[(wk[core] < 3).any(axis=1)]
        if not thin.empty:
            log(f"\n   Thin-data weeks: {list(thin.index)}")
    log("\n  This weekly file is intended for visualization; do not run inferential tests on n=21.")
    return wk


# =======================================================================
# Phase 7 - Stationarity: ADF + KPSS
# =======================================================================

def stationarity(wide: pd.DataFrame, feat: pd.DataFrame) -> pd.DataFrame:
    hdr("Phase 7 - Stationarity (ADF + KPSS)")
    try:
        from statsmodels.tsa.stattools import adfuller, kpss
    except ImportError:
        log("  statsmodels is not installed; Phase 7 was skipped")
        log("")
        log("       This is an explicit project requirement::")
        log('       "Consider stationarity and common trends"')
        log("")
        log("       pip install statsmodels, then run the script again.")
        log("       Without statsmodels, report_stationarity.csv will remain empty.")
        return pd.DataFrame()

    log("  ADF  - H0: unit root / non-stationary. p<0.05 -> reject H0")
    log("  KPSS - H0: stationary.                p<0.05 -> reject H0")
    log("  Their null hypotheses are opposite, so using both gives a stronger diagnostic.\n")

    def test(s, name, stage):
        s = s.dropna()
        if len(s) < 25:
            return None
        try:
            _, p_adf, *_ = adfuller(s, autolag="AIC")
        except Exception:
            return None
        try:
            p_kpss = kpss(s, regression="c", nlags="auto")[1]
        except Exception:
            p_kpss = np.nan
        a_rej = p_adf < 0.05
        k_rej = (p_kpss < 0.05) if not np.isnan(p_kpss) else None
        if k_rej is None:
            verdict = "probably stationary (ADF only)" if a_rej else "probably non-stationary (ADF only)"
        elif a_rej and not k_rej:
            verdict = " probably stationary"
        elif not a_rej and k_rej:
            verdict = " probably non-stationary"
        elif a_rej and k_rej:
            verdict = " inconclusive - possible structural break"
        else:
            verdict = " inconclusive - low power"
        return {"series": name, "stage": stage, "n": len(s),
                "p_ADF": round(p_adf, 4),
                "p_KPSS": round(p_kpss, 4) if not np.isnan(p_kpss) else None,
                "assessment": verdict}

    rows = []
    for c in wide.columns:
        if c in {**ASSETS, **DERIVED_META}:
            r = test(wide[c], c, "level")
            if r:
                rows.append(r)
    for c in feat.columns:
        r = test(feat[c], c.split("__", 1)[1], f"transformed ({c.split('__')[0]})")
        if r:
            rows.append(r)

    rep = pd.DataFrame(rows)
    if rep.empty:
        return rep
    log(rep.to_string(index=False))

    bad = rep[
        rep["stage"].str.startswith("transformed")
        & ~rep["assessment"].str.contains(
            "probably stationary",
            case=False,
            na=False
        )
        ]
    if not bad.empty:
        log(f"\n  Transformed series whose stationarity was not confirmed: {list(bad['series'])}")

    log("\n  " + "-" * 62)
    log("  Stationarity is necessary for many analyses, but it is not sufficient.")
    log("  Before inference, also examine:")
    log("    autocorrelation; heteroskedasticity; structural breaks")
    log("    outliers; non-synchronous trading; multiple testing")
    log("  " + "-" * 62)
    return rep


# =======================================================================
# Phase 8 - Lag diagnostics
# =======================================================================

FROZEN_LAGS = (0, 1, 3, 7)
SCAN_RANGE = range(-7, 8)


def naive_r_threshold(n: int, alpha: float = 0.05) -> float:
    """
     A simple threshold that assumes independent observations.
    Financial series exhibit volatility clustering and sentiment series may be autocorrelated,
    so the effective sample size may be smaller and this threshold can be optimistic.
    Use this only as an exploratory guide, not as an inferential rule.
    """
    try:
        from scipy import stats
        t = stats.t.ppf(1 - alpha / 2, n - 2)
    except ImportError:
        t = 1.984 if n > 60 else 2.093
    return t / np.sqrt(t ** 2 + n - 2)


def cross_corr(x: pd.Series, y: pd.Series, lags=SCAN_RANGE,
               min_n: int = 30) -> pd.DataFrame:
    """
    Exploratory diagnostic. lag>0 means x leads; lag<0 means y leads.

    (#14) min_n=30 is an operational display minimum,
    not a universal statistical-sufficiency threshold.
    """
    # Fix after the first run: after dropna(), the series have irregular date spacing.
    # Gaps may span 1, 3, or 4 days. shift() operates on rows, so shift(1) may mean
    # one calendar day in one place and several days elsewhere, also reducing n.
    # Reindex to a regular daily calendar first so lag=k means exactly
    # k calendar days and the sample alignment is stable.
    grid = pd.date_range(min(x.index.min(), y.index.min()),
                         max(x.index.max(), y.index.max()), freq="D")
    xg, yg = x.reindex(grid), y.reindex(grid)

    out = []
    for lag in lags:
        a, b = (xg.shift(lag), yg) if lag >= 0 else (xg, yg.shift(-lag))
        d = pd.concat([a, b], axis=1).dropna()
        if len(d) < min_n:
            continue
        r = float(np.corrcoef(d.iloc[:, 0], d.iloc[:, 1])[0, 1])
        out.append({"lag": lag, "n": len(d), "r": round(r, 3),
                    "r2": round(r * r, 3),
                    "naive_thr": round(naive_r_threshold(len(d)), 3),
                    "above_naive_threshold": abs(r) > naive_r_threshold(len(d))})
    return pd.DataFrame(out)


def lag_diagnostics(feat: pd.DataFrame) -> pd.DataFrame:
    hdr("Phase 8 - Lag diagnostics")
    log(f"  Frozen confirmatory lags: {FROZEN_LAGS}")
    log(f"  Exploratory scan: {SCAN_RANGE.start} to {SCAN_RANGE.stop-1}")
    log("   Selecting the best lag after scanning results is data fishing.")
    log("     Even with random data, one of many scanned lags may appear largest.")
    log("     Confirmatory analysis is restricted to the frozen lags.")
    log("     These lags must be recorded in decision_log.md")
    log("     before inspecting finance-by-sentiment results.")
    log("     FD-LAG-01: Primary lags = 0,1,3,7 - chosen before result inspection\n")

    core = [c for c in feat.columns
            if c.split("__", 1)[1] in {k for k, v in {**ASSETS, **DERIVED_META}.items()
                                       if v.role == "core"}]
    rows = []
    for i, a in enumerate(core):
        for b in core[i + 1:]:
            cc = cross_corr(feat[a], feat[b], lags=FROZEN_LAGS)
            for _, r in cc.iterrows():
                rows.append({"A": a.split("__", 1)[1], "B": b.split("__", 1)[1],
                             **r.to_dict(), "type": "frozen"})
    rep = pd.DataFrame(rows)
    if not rep.empty:
        log(rep.to_string(index=False))
        n = int(feat.dropna(how="all").shape[0])
        log(f"\n  Observed n = {n}")
        log(f"  Naive threshold at this n ~ {naive_r_threshold(max(n,3)):.3f}")
        log("   No universal sufficiency threshold is applied.")
        log("     Power depends on the model and target effect size, not on one fixed number.")
    return rep


# =======================================================================
# Phase 9 - Validation
# =======================================================================

def crosscheck(wide_all: pd.DataFrame) -> pd.DataFrame:
    log("\n  -- Cross-source verification --")
    log("  Compare levels only when instrument_type is the same.")
    log("  Futures and spot are different instruments; a non-zero basis can be valid.")
    log("  For unlike instruments, compare transformed returns rather than price levels.\n")
    rows = []
    reg = {**ASSETS, **VERIFY}
    for a, b, mode, tol in CROSSCHECK:
        if a not in wide_all.columns or b not in wide_all.columns:
            rows.append({"A": a, "B": b, "mode": mode, "result": "missing"})
            continue
        x, y = wide_all[a].dropna(), wide_all[b].dropna()
        com = x.index.intersection(y.index)
        if len(com) < 10:
            rows.append({"A": a, "B": b, "mode": mode, "n": len(com),
                         "result": "insufficient overlap"})
            continue
        ta = reg[a].instrument_type if a in reg else "?"
        tb = reg[b].instrument_type if b in reg else "?"
        if mode == "level":
            rel = ((x[com] - y[com]).abs() / x[com])
            med, mx = rel.median(), rel.max()
            ok = med < tol
            rows.append({"A": a, "B": b, "mode": "level", "n": len(com),
                         "type_A": ta, "type_B": tb,
                         "median_relative_difference": f"{med:.2%}", "maximum_relative_difference": f"{mx:.2%}",
                         "threshold": f"{tol:.1%}", "result": "PASS" if ok else "FAIL"})
        else:
            # Use each asset's registered transform rather than a hard-coded log transform.
            rx = apply_transform(x[com], reg[a].transform if a in reg else "log_return", a)
            ry = apply_transform(y[com], reg[b].transform if b in reg else "log_return", b)
            if rx is None or ry is None:
                rows.append({"A": a, "B": b, "mode": "return", "result": "transformation failed"})
                continue
            rx, ry = rx.dropna(), ry.dropna()
            k = rx.index.intersection(ry.index)
            rho = float(np.corrcoef(rx[k], ry[k])[0, 1]) if len(k) > 10 else np.nan
            same = float((np.sign(rx[k]) == np.sign(ry[k])).mean()) if len(k) else np.nan
            ok = (not np.isnan(rho)) and rho >= tol
            rows.append({"A": a, "B": b, "mode": "return", "n": len(k),
                         "type_A": ta, "type_B": tb,
                         "return_correlation": round(rho, 3) if not np.isnan(rho) else None,
                         "same_direction_share": f"{same:.0%}" if not np.isnan(same) else None,
                         "threshold": f"rho>={tol}", "result": "PASS" if ok else "FAIL"})
    rep = pd.DataFrame(rows)
    log(rep.to_string(index=False))
    return rep


def validate(df: pd.DataFrame, wide_all: pd.DataFrame) -> pd.DataFrame:
    hdr("Phase 9 - Validation")

    log("  -- Coverage of the six required financial categories --")
    need = {"fx": "Foreign exchange", "oil": "Oil prices", "gold": "Gold",
            "index": "Market indices", "volatility": "Risk or volatility indices",
            "economic": "Related economic indicators"}
    real = df[df.category != "verify"]
    for k, fa in need.items():
        sub = real[real.category == k]
        n, ncore = sub.asset_id.nunique(), sub[sub.role == "core"].asset_id.nunique()
        log(f"  {'' if n else ''} {fa:24s} {n:2d} variables  ({ncore} core)")

    cc = crosscheck(wide_all)

    log("\n  -- Timestamp --")
    ts = (real.groupby("asset_id")
              .agg(exact=("ts_is_exact", "first"), close=("close_local", "first"),
                   tz=("timezone", "first"), variant=("instrument_variant", "first"))
              .reset_index())
    log(ts.to_string(index=False))
    log("\n  observation_ts_utc is None for FRED verification series.")
    log("  Do not claim timestamp precision that the source does not provide.")

    log("\n" + "  " + "-" * 66)
    log("   Correlation does not establish a causal effect")
    log("  " + "-" * 66)
    log("  A conflict event can be a common cause of both market changes and sentiment changes:")
    log("")
    log("            oil <- event -> sentiment")
    log("")
    log("  In this structure, the event is a confounder; oil is not automatically a mediator.")
    log("  (A mediator would imply event -> oil -> sentiment, which is a different assumption.)")
    log("  Therefore, correlation between oil and sentiment alone does not establish")
    log("  a causal relationship between them.")
    log("")
    log('  Incorrect: "Oil caused sentiment to change."')
    log('  Preferred wording: "Oil changes and sentiment changes were contemporaneously associated (r=..., r2=..., n=...)."')
    log("")
    log("  In inferential models where simultaneous events may confound the relationship,")
    log("  consider event controls from event_registry_v1.")
    log("  (Descriptive plots, unconditional correlations, and event-window analysis do not necessarily")
    log("   require the same adjustment.)")
    return cc


# =======================================================================
#  Run
# =======================================================================

def to_wide(d: pd.DataFrame) -> pd.DataFrame:
    w = d.pivot_table(index="observation_date", columns="asset_id",
                      values="value", aggfunc="first")
    w.index = pd.to_datetime(w.index)
    return w.sort_index()


def main() -> None:
    if not FRED_API_KEY:
        raise RuntimeError(
            "FRED_API_KEY is required for the registered source cross-check. "
            "Set it in the local .env file before starting collection."
        )

    hdr(f"Financial data extraction  {START} -> {END}   |   {COLLECTOR_VERSION}")
    log(f"  Run: {NOW}")

    raw = pd.concat([p for p in (fetch_yahoo(), fetch_tedpix(), fetch_tgju())
                     if not p.empty], ignore_index=True)
    ver = fetch_fred()

    for d in (raw, ver):
        if not d.empty:
            d.drop(d.index[(d.observation_date < START) |
                           (d.observation_date > END)], inplace=True)
            d.drop_duplicates(["asset_id", "observation_date"],
                              keep="first", inplace=True)

    # -- Cleaning Contract: Raw preserved; analysis source cleaned first --
    hdr("Phase 3E - Cleaning contract before derived features")
    analytical_raw, exclusions = clean_raw_for_analysis(raw)

    # Derived features MUST be created from analytical source observations,
    # not from raw carry-forwards/stale values.
    wide_source = to_wide(analytical_raw)
    derived = build_derived(wide_source)

    # Raw and derived remain physically separate. ``all_obs`` is the analytical
    # observation layer (clean source + derived), never the immutable raw layer.
    all_obs = pd.concat([analytical_raw, derived], ignore_index=True)
    all_obs["project_week"] = all_obs.observation_date.map(project_week)
    raw["project_week"] = raw.observation_date.map(project_week)
    analytical_raw["project_week"] = analytical_raw.observation_date.map(project_week)
    if not derived.empty:
        derived["project_week"] = derived.observation_date.map(project_week)

    wide = to_wide(all_obs)
    wide_all = to_wide(pd.concat([all_obs, ver], ignore_index=True)) \
        if not ver.empty else wide

    panel = build_calendar_panel(all_obs, exclusions=exclusions)

    feat = build_features(wide)
    wk = build_weekly(wide, panel)
    adf = stationarity(wide, feat)
    lags = lag_diagnostics(feat)
    cc = validate(all_obs, wide_all)

    files = {
        "financial_raw.csv":            raw,
        "financial_cleaning_exclusions.csv": exclusions,
        "financial_analytical_source.csv": analytical_raw,
        "financial_derived.csv":        derived,
        "financial_source_crosscheck.csv": ver,
        "financial_analysis_wide.csv":  wide,
        "financial_features.csv":       feat,
        "financial_weekly.csv":         wk,
        "financial_calendar_panel.csv": panel,
        "report_stationarity.csv":      adf,
        "report_lags.csv":              lags,
        "report_crosscheck.csv":        cc,
    }
    hdr("Output")
    for name, obj in files.items():
        if obj is None or (hasattr(obj, "empty") and obj.empty):
            log(f"   {name:34s} empty")
            continue
        idx = name in ("financial_analysis_wide.csv", "financial_features.csv",
                       "financial_weekly.csv")
        obj.to_csv(OUT / name, index=idx, encoding="utf-8-sig")
        log(f"   {name:34s} {(OUT/name).stat().st_size/1024:8.1f} KB")

    pd.DataFrame([asdict(a) for a in {**ASSETS, **DERIVED_META, **VERIFY}.values()]) \
      .to_csv(OUT / "asset_registry.csv", index=False, encoding="utf-8-sig")
    log(f"   {'asset_registry.csv':34s} (complete metadata for every asset)")
    log(f"   {'run raw files:':34s} {len([p for p in RAW.rglob('*') if p.is_file()])} files")

    validation_path = AUDIT / "financial_collection_validation_report.txt"
    validation_path.write_text("\n".join(LOG), encoding="utf-8")
    print(f"\n Run directory: {RUN_ROOT}")
    print(f"\n Review: {validation_path}")
    print(f" Analysis input: {OUT / 'financial_analysis_wide.csv'}")


if __name__ == "__main__":
    main()
