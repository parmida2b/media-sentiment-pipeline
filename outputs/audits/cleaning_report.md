# Cleaning report — YouTube bot-detection pass

- Source: `C:\Users\user\OneDrive\Desktop\hamrahaval\final\media-sentiment-pipeline-starter\media-sentiment-pipeline-starter\data\raw\iran_us_war`
- Total comment/reply records: 155397
- Distinct users seen: 103315
- Users flagged (`automation_risk_score_user >= 0.7`): 12 (0.0% of users)

> `automation_risk_score_user` is a heuristic risk score in [0,1], **not a bot verdict** — see `docs/cross_platform_alignment_guide_fa.md` §4. Nothing was removed from `clean.jsonl`; this flag is for manual review / a later, team-reviewed eligibility decision.

## Top 20 highest-risk users (manual spot-check candidates)

| user_key | score | total_interactions | exact_duplicate_ratio | url_interaction_ratio | hour_coverage_ratio |
|---|---|---|---|---|---|
| `4aa57251d1e06d9974f291e6` | 0.7892 | 2 | 1.0 | 1.0 | 0.0417 |
| `UC6gSRLjw6QCd_C5cibybo6A` | 0.7542 | 2 | 1.0 | 1.0 | 0.0417 |
| `UCa7MlqCj5faqHvqdV6OB5DA` | 0.7542 | 2 | 1.0 | 1.0 | 0.0417 |
| `UCDTo6Kqex7P_69Ezg-szDSg` | 0.7542 | 3 | 1.0 | 1.0 | 0.0417 |
| `UCkWcvOfwgD_MOyR03x6VPkg` | 0.7542 | 2 | 1.0 | 1.0 | 0.0417 |
| `UCsC1drGmTpCvfVkHXjB-Djg` | 0.7542 | 4 | 1.0 | 1.0 | 0.0417 |
| `a2448667691ef8d7edbcd0a0` | 0.7142 | 3 | 1.0 | 0.0 | 0.0417 |
| `cbe73675e44b0fc916a74177` | 0.7142 | 8 | 1.0 | 0.0 | 0.0417 |
| `0b7c1ad39fc620f2d19f0366` | 0.7142 | 3 | 1.0 | 0.0 | 0.0417 |
| `2fd4d1794aaa47b46fc99243` | 0.7098 | 4 | 1.0 | 0.0 | 0.0417 |
| `7a461b81142b7e6129a276b5` | 0.7054 | 4 | 1.0 | 0.0 | 0.0417 |
| `5433156c75d2236231b18ae7` | 0.7054 | 6 | 1.0 | 0.0 | 0.0417 |
