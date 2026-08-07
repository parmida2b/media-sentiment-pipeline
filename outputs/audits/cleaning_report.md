# Cleaning report — YouTube bot-detection pass

- Source: `C:\Users\user\OneDrive\Desktop\hamrahaval\final\media-sentiment-pipeline-starter\media-sentiment-pipeline-starter\data\raw\iran_us_war`
- Total comment/reply records: 74924
- Distinct users seen: 50527
- Users flagged (`automation_risk_score_user >= 0.7`): 5 (0.0% of users)

> `automation_risk_score_user` is a heuristic risk score in [0,1], **not a bot verdict** — see `docs/cross_platform_alignment_guide_fa.md` §4. Nothing was removed from `clean.jsonl`; this flag is for manual review / a later, team-reviewed eligibility decision.

## Top 20 highest-risk users (manual spot-check candidates)

| user_key | score | total_interactions | exact_duplicate_ratio | url_interaction_ratio | hour_coverage_ratio |
|---|---|---|---|---|---|
| `UC6gSRLjw6QCd_C5cibybo6A` | 0.7542 | 2 | 1.0 | 1.0 | 0.0417 |
| `UCa7MlqCj5faqHvqdV6OB5DA` | 0.7542 | 2 | 1.0 | 1.0 | 0.0417 |
| `UCDTo6Kqex7P_69Ezg-szDSg` | 0.7542 | 3 | 1.0 | 1.0 | 0.0417 |
| `UCkWcvOfwgD_MOyR03x6VPkg` | 0.7542 | 2 | 1.0 | 1.0 | 0.0417 |
| `UCsC1drGmTpCvfVkHXjB-Djg` | 0.7542 | 4 | 1.0 | 1.0 | 0.0417 |
