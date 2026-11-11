# Working rules for this repository

Read `planning/LEAD.md` (lead session) or your task card in `planning/tasks/` (worker session) before doing anything.

- Never commit or push to `main`. Integration branch: `claude/code-review-integrity-v2`. Worker branches: `claude/tNN-<slug>` cut from the latest integration branch.
- The repository owner's instruction: no AI attribution anywhere. Do not add `Co-Authored-By`, session links, "Generated with" lines or any mention of an AI assistant to commit messages, PR text, code, comments or docs.
- Follow `planning/STYLE.md` for every line you write: short comments that explain why, no em dash or en dash characters, no dated history notes or checklist section references in code.
- Behaviour changes need a test that fails before the change and passes after it. Run `pytest` before pushing.
- Never edit `data/raw_harmonized/`, `data/raw_original/` or `data/annotated/` in place. Run the pipeline on a scratch copy of the repo.
- Never put API keys in chat, code, config or docs. Ask the user through the secure credential form.
- Paid API calls (LLM annotation) and network collection need the user's explicit approval first.
- This file, `planning/` and `docs/review/` are temporary and are deleted in task T20.
