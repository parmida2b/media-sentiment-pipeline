# Cleaning report — cross-platform bot-detection pass

- Sources: `C:\Users\user\OneDrive\Desktop\hamrahaval\final\media-sentiment-pipeline-starter\media-sentiment-pipeline-starter\data\raw\iran_us_war` (YouTube), `C:\Users\user\OneDrive\Desktop\hamrahaval\final\media-sentiment-pipeline-starter\media-sentiment-pipeline-starter\data\raw\reddit` (Reddit), `C:\Users\user\OneDrive\Desktop\hamrahaval\final\media-sentiment-pipeline-starter\media-sentiment-pipeline-starter\data\raw\x` (X)
- Records by platform: {'youtube': 157474, 'reddit': 158959, 'x': 16475}
- Total comment/reply records: 332908
- Distinct users seen: 178231 (per-platform - a real person active on both YouTube and Reddit has two separate user_keys here, one per platform's own author_hash; see cross_platform_alignment_guide_fa.md §5 checklist item 4, cross-platform identity linkage is explicitly not attempted)
- Users flagged (`automation_risk_score_user >= 0.7`): 13 (0.0% of users)

> `automation_risk_score_user` is a heuristic risk score in [0,1], **not a bot verdict** — see `docs/cross_platform_alignment_guide_fa.md` §4. Nothing was removed from `clean.jsonl`; this flag is for manual review / a later, team-reviewed eligibility decision.

## Top 20 highest-risk users (manual spot-check candidates)

| user_key | score | total_interactions | exact_duplicate_ratio | url_interaction_ratio | hour_coverage_ratio |
|---|---|---|---|---|---|
| `eef00c9903bdc2f2ba8674a1` | 0.7892 | 2 | 1.0 | 1.0 | 0.0417 |
| `UC6gSRLjw6QCd_C5cibybo6A` | 0.7542 | 2 | 1.0 | 1.0 | 0.0417 |
| `UCa7MlqCj5faqHvqdV6OB5DA` | 0.7542 | 2 | 1.0 | 1.0 | 0.0417 |
| `UCDTo6Kqex7P_69Ezg-szDSg` | 0.7542 | 3 | 1.0 | 1.0 | 0.0417 |
| `UCkWcvOfwgD_MOyR03x6VPkg` | 0.7542 | 2 | 1.0 | 1.0 | 0.0417 |
| `UCsC1drGmTpCvfVkHXjB-Djg` | 0.7542 | 4 | 1.0 | 1.0 | 0.0417 |
| `d3898ad54baebfc1d2e19054` | 0.7542 | 2 | 1.0 | 1.0 | 0.0417 |
| `6fdaf018799184ba25c7883c` | 0.7142 | 3 | 1.0 | 0.0 | 0.0417 |
| `30aeca254da151a01b5ed265` | 0.7142 | 8 | 1.0 | 0.0 | 0.0417 |
| `70c253d2e87b9fb2be79d03d` | 0.7142 | 3 | 1.0 | 0.0 | 0.0417 |
| `bf0ccf3362057ec880ec979e` | 0.7098 | 4 | 1.0 | 0.0 | 0.0417 |
| `2ebb647e777a313e1ef81dd1` | 0.7054 | 4 | 1.0 | 0.0 | 0.0417 |
| `2fda5a006c4b7d228f79e9dd` | 0.7054 | 6 | 1.0 | 0.0 | 0.0417 |
