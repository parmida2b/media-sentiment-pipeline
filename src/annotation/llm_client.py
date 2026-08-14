"""
llm_client.py — unified multi-provider annotation caller (Parmida)

One entry point, `annotate()`, used by both run_model_comparison.py (Day 1
scouting) and evaluate_sentiment_accuracy.py (Day 2 benchmark) so provider
wiring, retries, caching, and cost/latency logging live in exactly one place
instead of being copy-pasted per script (§42: no unnecessary duplication).

Implements pieces of §21 (cost-aware pipeline) and §39 (Observability):
  - cache keyed on hash(route + prompt_version + prompt text) — §21 step 6
  - retry with exponential backoff on transient failures — §42
  - per-call cost/latency/token logging to outputs/model_evaluation/usage_log.jsonl
  - schema validation of every parsed response before it's trusted (§22)
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import requests

from src.annotation.model_routes import ModelRoute, estimate_cost_usd
from src.annotation.prompt_contract import PROMPT_VERSION, build_prompt
from src.annotation.schema import AnnotationValidationError, validate_annotation_output

ROOT = Path(__file__).resolve().parent.parent.parent
CACHE_PATH = ROOT / "outputs" / "model_evaluation" / "llm_annotation_cache.json"
USAGE_LOG_PATH = ROOT / "outputs" / "model_evaluation" / "usage_log.jsonl"

MAX_RETRIES = 3
BACKOFF_BASE_SECONDS = 1.5
REQUEST_TIMEOUT_SECONDS = 30

# HTTP 4xx errors other than 429 (rate limit) won't fix themselves on retry
# (bad key, insufficient balance, bad request, ...) — retrying just burns
# wall-clock time for a call that will fail again identically.
_NON_RETRYABLE_HTTP_PREFIXES = tuple(f"HTTP {code}" for code in (400, 401, 402, 403, 404, 422))


# --- cache -------------------------------------------------------------------

class AnnotationCache:
    """Load once, look up/insert in memory, save once — avoids re-paying for
    an identical (route, prompt_version, text) call across re-runs."""

    def __init__(self, path: Path = CACHE_PATH):
        self.path = path
        self._data: dict[str, dict] = {}
        if self.path.exists():
            self._data = json.loads(self.path.read_text(encoding="utf-8"))

    @staticmethod
    def key(route_name: str, prompt_version: str, prompt: str) -> str:
        h = hashlib.sha256()
        for part in (route_name, prompt_version, prompt):
            h.update(part.encode("utf-8"))
            h.update(b"\x00")
        return h.hexdigest()

    def get(self, cache_key: str) -> Optional[dict]:
        return self._data.get(cache_key)

    def set(self, cache_key: str, value: dict) -> None:
        # dict.__setitem__ is atomic under the GIL, so concurrent set() calls
        # from different threads (run_full_annotation.py's ThreadPoolExecutor,
        # 2026-08-14) can't corrupt _data itself — the caller still owns
        # deciding *when* to call save() (see save()'s own docstring).
        self._data[cache_key] = value

    def save(self) -> None:
        """Not thread-safe by itself — two threads calling save()
        simultaneously could interleave writes to the same file. Callers
        that annotate from multiple threads (run_full_annotation.py) must
        serialize their own save() calls (e.g. one dedicated thread/lock),
        not call this directly from worker threads."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._data, ensure_ascii=False, indent=2), encoding="utf-8")


# --- usage / cost logging (§39 Observability) --------------------------------

_usage_log_lock = threading.Lock()


def _append_usage_log(entry: dict) -> None:
    # Locked (2026-08-14): run_full_annotation.py calls annotate() from
    # multiple threads — unlocked concurrent appends to the same file handle
    # could interleave partial lines on some platforms/buffering modes.
    USAGE_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _usage_log_lock:
        with open(USAGE_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# --- raw provider callers -----------------------------------------------------

# §22's structured output (sentiment/stance/emotion/content_type/confidence/
# reason_code) is a small JSON object — real completions run well under 200
# tokens. Left unset, providers default max_tokens to the model's own ceiling
# (e.g. 65535 for gemini-2.5-flash-lite), and OpenRouter's pre-flight balance
# check rejects a call if the account can't afford that *ceiling*, even
# though the real response is tiny (seen 2026-08-14: "HTTP 402 ... requested
# up to 65535 tokens, but can only afford 57073" on an account with plenty of
# credit for the actual annotation). Capping this explicitly fixes that
# false-insufficient-credit rejection without touching any account/balance —
# generous enough to never truncate a real response, per docs/decision_log.md.
MAX_OUTPUT_TOKENS = 500


@dataclass
class RawCallResult:
    raw_text: Optional[str]
    latency_ms: float
    input_tokens: Optional[int]
    output_tokens: Optional[int]
    call_error: Optional[str]  # None on success, else a short error message


def _is_daily_quota_message(message: str) -> bool:
    # Same heuristic as src/ingestion/geo_tagger.py's _is_daily_quota_message
    # (2026-08-12): Groq's 429 body says "...on tokens per day (TPD): Limit
    # 100000, Used 99901..." for a daily cap vs "...per minute (TPM)..." for
    # a transient one. A day/date never comes back sooner by retrying.
    text = (message or "").lower()
    return "per day" in text or "rpd" in text or "tpd" in text


_groq_exhausted_keys: set[str] = set()  # keys that hit their *daily* quota this process
_groq_rr_index = 0  # round-robin cursor across keys, protected by _groq_rr_lock
_groq_rr_lock = threading.Lock()


def _next_groq_key_order(keys: list[str]) -> list[str]:
    """Round-robin the starting key across concurrent calls (2026-08-14):
    with run_full_annotation.py's ThreadPoolExecutor, every call used to
    start from keys[0] — under concurrency that piles every worker onto one
    key's per-minute token limit (TPM) instead of spreading load across all
    configured keys, defeating the point of having several. Rotating the
    starting offset per call means N concurrent workers land on ~N/len(keys)
    different keys instead of all N on the same one."""
    global _groq_rr_index
    if not keys:
        return keys
    with _groq_rr_lock:
        offset = _groq_rr_index % len(keys)
        _groq_rr_index += 1
    return keys[offset:] + keys[:offset]


def _load_groq_keys(api_keys: dict[str, str]) -> list[str]:
    """Multi-key support (2026-08-14, mirrors geo_tagger.py's 2026-08-12
    precedent): GROQ_API_KEYS (comma-separated) pools several teammates' own
    Groq accounts' daily quota — each key must belong to a real teammate's
    own account, never a throwaway/duplicate one (Groq ToS; see
    docs/decision_log.md). Falls back to the single GROQ_API_KEY (api_keys
    dict, same as every other provider here) when GROQ_API_KEYS isn't set."""
    multi = os.getenv("GROQ_API_KEYS")
    if multi:
        keys = [k.strip() for k in multi.split(",") if k.strip()]
        if keys:
            return keys
    single = api_keys.get("GROQ_API_KEY", "")
    return [single] if single else []


def _call_groq(api_keys: dict[str, str], route: ModelRoute, prompt: str) -> RawCallResult:
    from groq import Groq, RateLimitError

    keys = _load_groq_keys(api_keys)
    usable_keys = _next_groq_key_order([k for k in keys if k not in _groq_exhausted_keys])
    if not usable_keys:
        return RawCallResult(
            None, 0.0, None, None,
            f"HTTP 429: all {len(keys)} configured Groq key(s) exhausted their daily quota.",
        )

    last_error = None
    for key in usable_keys:
        client = Groq(api_key=key)
        t0 = time.monotonic()
        try:
            response = client.chat.completions.create(
                model=route.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=MAX_OUTPUT_TOKENS,
            )
            latency_ms = (time.monotonic() - t0) * 1000
            usage = getattr(response, "usage", None)
            return RawCallResult(
                raw_text=response.choices[0].message.content,
                latency_ms=latency_ms,
                input_tokens=getattr(usage, "prompt_tokens", None),
                output_tokens=getattr(usage, "completion_tokens", None),
                call_error=None,
            )
        except RateLimitError as e:
            message = str(getattr(e, "message", None) or e)
            if _is_daily_quota_message(message):
                _groq_exhausted_keys.add(key)
                print(f"[warn] llm_client: Groq key ...{key[-4:]} hit its daily quota — "
                      f"rotating to next key ({len(usable_keys) - usable_keys.index(key) - 1} left to try).")
                last_error = RawCallResult(None, (time.monotonic() - t0) * 1000, None, None, f"HTTP 429: {message[:250]}")
                continue  # try the next key, same call, no backoff needed — different account
            # Per-minute (TPM/RPM) limit, not a daily one — the key isn't
            # exhausted, just busy this minute. With run_full_annotation.py's
            # concurrent workers, several keys are usually still under their
            # own per-minute cap right now (2026-08-14: 30 workers all on one
            # key blew straight through Groq's 6000 TPM cap for
            # llama-3.1-8b-instant) — so try the next key immediately instead
            # of giving up after one. Only after every key has been tried
            # this call does it fall through to annotate()'s outer
            # retry/backoff loop.
            last_error = RawCallResult(None, (time.monotonic() - t0) * 1000, None, None, f"HTTP 429: {message[:250]}")
            continue
        except Exception as e:  # noqa: BLE001 — provider SDKs raise varied exception types
            last_error = RawCallResult(None, (time.monotonic() - t0) * 1000, None, None, str(e)[:300])
            break

    return last_error


def _call_openai_compatible(
    api_key: str, base_url: str, route: ModelRoute, prompt: str, extra_headers: dict | None = None,
) -> RawCallResult:
    """Shared caller for OpenRouter and DeepSeek — both speak the OpenAI
    chat/completions wire format, so one HTTP function covers both."""
    t0 = time.monotonic()
    try:
        response = requests.post(
            f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                **(extra_headers or {}),
            },
            json={
                "model": route.model_name,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0,
                "max_tokens": MAX_OUTPUT_TOKENS,
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        latency_ms = (time.monotonic() - t0) * 1000
        if response.status_code != 200:
            return RawCallResult(None, latency_ms, None, None, f"HTTP {response.status_code}: {response.text[:200]}")
        payload = response.json()
        usage = payload.get("usage", {})
        return RawCallResult(
            raw_text=payload["choices"][0]["message"]["content"],
            latency_ms=latency_ms,
            input_tokens=usage.get("prompt_tokens"),
            output_tokens=usage.get("completion_tokens"),
            call_error=None,
        )
    except Exception as e:  # noqa: BLE001
        return RawCallResult(None, (time.monotonic() - t0) * 1000, None, None, str(e)[:300])


def _call_provider(route: ModelRoute, prompt: str, api_keys: dict[str, str]) -> RawCallResult:
    if route.provider == "groq":
        return _call_groq(api_keys, route, prompt)
    if route.provider == "openrouter":
        return _call_openai_compatible(
            api_keys["OPENROUTER_API_KEY"], "https://openrouter.ai/api/v1", route, prompt,
            extra_headers={"HTTP-Referer": "https://github.com/media-sentiment-pipeline",
                            "X-Title": "media-sentiment-pipeline"},
        )
    if route.provider == "deepseek":
        return _call_openai_compatible(api_keys["DEEPSEEK_API_KEY"], "https://api.deepseek.com", route, prompt)
    if route.provider == "ollama":
        # Local, unauthenticated server — Ollama's /v1/chat/completions is
        # OpenAI-wire-compatible (verified 2026-08-14: proper choices[0].
        # message.content + usage.prompt_tokens/completion_tokens), so the
        # shared caller works unchanged; the "api_key" is a dummy string,
        # Ollama ignores the Authorization header entirely.
        base_url = api_keys.get("OLLAMA_BASE_URL") or "http://localhost:11434"
        return _call_openai_compatible("ollama-local-no-auth", f"{base_url}/v1", route, prompt)
    raise ValueError(f"Unknown provider {route.provider!r} on route {route.route_name!r}")


# --- JSON parsing --------------------------------------------------------------

def _parse_json_response(raw_text: str) -> tuple[Optional[dict], Optional[str]]:
    """Returns (payload, parse_error). payload is None iff parse_error is set."""
    text = raw_text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json\n"):
            text = text[len("json\n"):]
    try:
        return json.loads(text), None
    except json.JSONDecodeError as e:
        return None, f"JSONDecodeError: {e}"


# --- public entry point --------------------------------------------------------

@dataclass
class AnnotationResult:
    route_name: str
    model_name: str
    provider: str
    prompt_version: str
    payload: Optional[dict]  # the 4-layer annotation dict, or None on failure
    confidence: Optional[float]
    latency_ms: float
    input_tokens: Optional[int]
    output_tokens: Optional[int]
    cost_usd: Optional[float]
    from_cache: bool
    call_error: Optional[str]
    parse_error: Optional[str]
    validation_error: Optional[str]

    @property
    def ok(self) -> bool:
        return self.payload is not None and self.call_error is None

    def as_log_row(self, run_id: str, content_id: str) -> dict:
        row = asdict(self)
        row.pop("payload")
        row.update(run_id=run_id, content_id=content_id, recorded_at_utc=datetime.now(timezone.utc).isoformat())
        return row


def annotate(
    text: str,
    target_id: str,
    route: ModelRoute,
    api_keys: dict[str, str],
    cache: AnnotationCache,
    run_id: str = "unspecified",
    content_id: str = "",
    log_usage: bool = True,
) -> AnnotationResult:
    """Run the full §22 structured-annotation contract for one (text, target)
    pair against one model route, with caching, retry+backoff, schema
    validation, and cost/latency logging."""
    prompt = build_prompt(text, target_id)
    cache_key = AnnotationCache.key(route.route_name, PROMPT_VERSION, prompt)

    cached = cache.get(cache_key)
    if cached is not None:
        result = AnnotationResult(**{**cached, "from_cache": True})
    else:
        call = None
        for attempt in range(MAX_RETRIES):
            call = _call_provider(route, prompt, api_keys)
            if call.call_error is None:
                break
            if call.call_error.startswith(_NON_RETRYABLE_HTTP_PREFIXES):
                break  # bad key / insufficient balance / bad request — retrying won't help
            time.sleep(BACKOFF_BASE_SECONDS * (2 ** attempt))

        payload, parse_error, validation_error, confidence = None, None, None, None
        if call.call_error is None:
            parsed, parse_error = _parse_json_response(call.raw_text)
            if parsed is not None:
                try:
                    validate_annotation_output(parsed)
                    payload = parsed
                    confidence = float(parsed["confidence"])
                except AnnotationValidationError as e:
                    validation_error = str(e)

        cost_usd = None
        if call.input_tokens is not None and call.output_tokens is not None:
            cost_usd = estimate_cost_usd(route, call.input_tokens, call.output_tokens)

        result = AnnotationResult(
            route_name=route.route_name,
            model_name=route.model_name,
            provider=route.provider,
            prompt_version=PROMPT_VERSION,
            payload=payload,
            confidence=confidence,
            latency_ms=call.latency_ms,
            input_tokens=call.input_tokens,
            output_tokens=call.output_tokens,
            cost_usd=cost_usd,
            from_cache=False,
            call_error=call.call_error,
            parse_error=parse_error,
            validation_error=validation_error,
        )
        # Only cache successful, schema-valid results — a transient error or
        # parse failure shouldn't be "sticky" across re-runs.
        if result.ok:
            cache.set(cache_key, asdict(result))

    if log_usage:
        _append_usage_log(result.as_log_row(run_id, content_id))

    return result
