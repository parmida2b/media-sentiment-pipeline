"""
event_registry.py — machine-readable copy of docs/event_registry_v3.md §4
("رویدادهای تحلیل اصلی") (Parmida)

These 4 events were registered in docs/event_registry_v3.md BEFORE this
analysis code was written (docs/checklist.md §25/فاز سیزدهم: "رویدادهای
اصلی باید پیش از آزمون نهایی ثبت شوند" — Cherry-picking prevention). This
file transcribes that table's §4 columns verbatim (ID/date/target/outcome/
expected_direction/windows) — it does not invent, select, or adjust any
event; if the analysis needs a different event set, docs/event_registry_v3.md
is the file to change first, not this one.

EV-001 has no `main_window`/comparable "before" period (it IS the war's
start, W01) — analysis_role=study_anchor, kept for descriptive volume/
composition reporting only, excluded from the before/after stance-share
comparison event_study.py runs for the 3 primary_confirmatory events.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class RegisteredEvent:
    event_id: str
    event_date: date
    project_week: str
    event_type: str
    analysis_role: str  # "study_anchor" | "primary_confirmatory"
    title_fa: str
    target_id: str | None
    primary_outcome_fa: str
    expected_direction_fa: str | None
    main_window_days: int | None  # None for study_anchor (no before/after window)
    sensitivity_window_days: int | None


EVENTS: list[RegisteredEvent] = [
    RegisteredEvent(
        event_id="EV-001",
        event_date=date(2026, 2, 28),
        project_week="W01",
        event_type="military",
        analysis_role="study_anchor",
        title_fa="آغاز حملات گسترده آمریکا و اسرائیل به ایران",
        target_id="T01",
        primary_outcome_fa="حجم و ترکیب محتوای روزهای آغاز",
        expected_direction_fa=None,
        main_window_days=None,  # "توصیف پسارویداد" — descriptive post-event only, no pre-war baseline in-window
        sensitivity_window_days=None,
    ),
    RegisteredEvent(
        event_id="EV-016",
        event_date=date(2026, 4, 7),
        project_week="W06",
        event_type="diplomatic",
        analysis_role="primary_confirmatory",
        title_fa="اعلام آتش‌بس دوهفته‌ای",
        target_id="T02",
        primary_outcome_fa="سهم حمایت از دیپلماسی",
        expected_direction_fa="افزایش حمایت و Hope",
        main_window_days=14,
        sensitivity_window_days=7,
    ),
    RegisteredEvent(
        event_id="EV-025",
        event_date=date(2026, 6, 17),
        project_week="W16",
        event_type="diplomatic",
        analysis_role="primary_confirmatory",
        title_fa="امضای تفاهم‌نامه اسلام‌آباد",
        target_id="T02",
        primary_outcome_fa="سهم حمایت از دیپلماسی",
        expected_direction_fa="افزایش حمایت و کاهش Fear",
        main_window_days=7,  # narrowed from 14: EV-025/EV-031 are 10 days apart, see event_registry_v3.md §4 note
        sensitivity_window_days=3,
    ),
    RegisteredEvent(
        event_id="EV-031",
        event_date=date(2026, 6, 27),
        project_week="W18",
        event_type="military",
        analysis_role="primary_confirmatory",
        title_fa="ازسرگیری حملات متقابل",
        target_id="T01",
        primary_outcome_fa="سهم مخالفت با تشدید نظامی",
        expected_direction_fa="افزایش مخالفت و Fear",
        main_window_days=7,
        sensitivity_window_days=3,
    ),
]

PRIMARY_CONFIRMATORY_EVENTS = [e for e in EVENTS if e.analysis_role == "primary_confirmatory"]


def placebo_event_for(event: RegisteredEvent, offset_days: int = -35) -> RegisteredEvent:
    """A PLACEBO comparison point — not a real event, never claimed as one.
    docs/checklist.md §25 asks for a Placebo where possible (sensitivity:
    does the same before/after test show a similarly-sized 'effect' at a
    date nothing happened?). Offset defaults to -35 days: far enough that
    its own +/- window doesn't overlap the real event's, close enough to
    stay inside the project window for events registered early on.
    event_id is prefixed 'PLACEBO-' and title_fa is prefixed explicitly so
    it can never be mistaken for — or silently reported as — a real
    registered event (project rule: no fabricated events, docs/checklist.md
    §45)."""
    return RegisteredEvent(
        event_id=f"PLACEBO-{event.event_id}",
        event_date=date.fromordinal(event.event_date.toordinal() + offset_days),
        project_week="N/A",
        event_type=event.event_type,
        analysis_role="placebo",
        title_fa=f"[PLACEBO — رویداد واقعی نیست، فقط برای آزمون حساسیت] {event.title_fa}",
        target_id=event.target_id,
        primary_outcome_fa=event.primary_outcome_fa,
        expected_direction_fa=None,  # a placebo has no a-priori expected direction — that's the point
        main_window_days=event.main_window_days,
        sensitivity_window_days=event.sensitivity_window_days,
    )
