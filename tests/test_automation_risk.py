"""
tests/test_automation_risk.py — unit tests for src/ingestion/automation_risk.py's
score_batch(): the heuristic automation/spam-risk scorer (docs/checklist.md
item 15). Never asserts a "this is a bot" verdict -- only the documented
[0, 1] risk-score behavior for duplicate text, rapid-fire posting, and
link/hashtag density.
"""

from src.ingestion.automation_risk import score_batch


def _comment(content_id, text, date="2026-03-05T12:00:00Z", author="author_1"):
    return {"content_id": content_id, "text": text, "date": date, "author_channel_id": author}


def test_score_batch_empty_input_returns_empty():
    assert score_batch([]) == {}


def test_score_batch_ignores_comments_without_content_id():
    comments = [{"text": "hello", "date": "2026-03-05T12:00:00Z", "author_channel_id": "a"}]
    assert score_batch(comments) == {}


def test_score_batch_unique_single_comment_scores_zero():
    comments = [_comment("c1", "a perfectly normal, unique opinion")]
    scores = score_batch(comments)
    assert scores["c1"] == 0.0


def test_score_batch_all_scores_within_unit_interval():
    comments = [_comment(f"c{i}", "same text repeated") for i in range(6)]
    scores = score_batch(comments)
    assert all(0.0 <= v <= 1.0 for v in scores.values())


def test_score_batch_repeated_text_scores_higher_than_unique():
    duped = [_comment(f"c{i}", "spam spam spam text") for i in range(5)]
    unique = [_comment("u1", "a distinct genuine opinion about the topic")]
    dupe_scores = score_batch(duped)
    unique_scores = score_batch(unique)
    assert max(dupe_scores.values()) > max(unique_scores.values())


def test_score_batch_rapid_fire_same_author_scores_higher_than_spread_out():
    rapid = [
        _comment("r1", "text one", date="2026-03-05T12:00:00Z", author="bot_a"),
        _comment("r2", "text two", date="2026-03-05T12:00:10Z", author="bot_a"),
        _comment("r3", "text three", date="2026-03-05T12:00:20Z", author="bot_a"),
    ]
    spread = [
        _comment("s1", "text one", date="2026-03-05T00:00:00Z", author="human_a"),
        _comment("s2", "text two", date="2026-03-06T00:00:00Z", author="human_a"),
        _comment("s3", "text three", date="2026-03-07T00:00:00Z", author="human_a"),
    ]
    rapid_scores = score_batch(rapid)
    spread_scores = score_batch(spread)
    assert max(rapid_scores.values()) > max(spread_scores.values())
    assert max(spread_scores.values()) == 0.0  # no duplicate text, no rapid-fire, no links


def test_score_batch_link_heavy_text_scores_higher_than_plain():
    linky = [_comment("l1", "check https://a.com https://b.com https://c.com #spam #now")]
    plain = [_comment("p1", "a normal comment with no links at all")]
    assert max(score_batch(linky).values()) > max(score_batch(plain).values())


def test_score_batch_missing_author_or_unparseable_date_does_not_crash():
    comments = [
        _comment("m1", "text", date="not-a-date", author=""),
        {"content_id": "m2", "text": "text2"},  # no date/author keys at all
    ]
    scores = score_batch(comments)
    assert set(scores.keys()) == {"m1", "m2"}
    assert all(0.0 <= v <= 1.0 for v in scores.values())
