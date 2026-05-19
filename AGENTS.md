# Agent instructions — fpl_stats

Use this file for **every** Cloud Agent run on this repo. Each run should implement **one GitHub issue** unless the issue explicitly spans multiple concerns.

## How to start work

1. Read the linked GitHub issue: title, summary, acceptance criteria, and listed files.
2. Implement only what that issue asks for. Do not refactor unrelated code or fix other open issues in the same PR.
3. If the issue lists **Depends on** another issue, either implement dependencies first in order or keep the PR scoped and note the blocker in the PR description.
4. When triggered from GitHub, `@cursor` with a short line is enough (e.g. `Implement this issue`). Do not wait for a long manual brief.

## Git and pull requests

- Branch from `main`. Use branch names: `cursor/<short-description>` (lowercase, hyphens).
- One issue → one branch → one draft PR.
- Commit messages: short imperative summary (e.g. `Fix autosub award unit label (#11)`).
- PR body: what changed, how to verify, which issue it closes (`Closes #N`), and any follow-ups.
- Do not commit secrets, `.env`, live CSV dumps, or generated PDFs/HTML under `fpl_output/`.

## Python environment

- **Python 3** (3.10+ recommended).
- Install deps: `pip install -r requirements.txt` (prefer a venv).
- Main scripts:
  - `fetch_fpl_league_data.py` — downloads league data (needs live FPL API + cookie).
  - `fpl_generate_report_v3.py` — builds PDF/HTML reports from `csv/fpl_season_data.csv`.
  - `map_players_name.py` — player name mapping utilities.

## Secrets and live API

- Local fetch uses `.env`:
  - `FPL_COOKIE` — session cookie for FPL API.
  - `FPL_LEAGUE_ID` — league id (code uses this name; README may say `LEAGUE_ID` — align docs when touching env docs).
- **CI and automated tests must not require** `FPL_COOKIE`, live FPL HTTP, or network access to `fantasy.premierleague.com` unless an issue explicitly adds an optional integration job.
- Use **fixtures** under `test/` (sample CSV/JSON) when adding tests; see issue #9 for direction.

## Testing and verification

- After changes, run what exists:
  - `python -m py_compile fpl_generate_report_v3.py fetch_fpl_league_data.py map_players_name.py` (always reasonable).
  - `pytest` when a test suite exists (issues #9, #15).
- For report logic without live data, use checked-in or fixture CSV under `test/` rather than fetching.
- If you cannot run WeasyPrint/PDF locally (missing system libs), say so in the PR and rely on logic/tests for the changed paths.

## Domain conventions

### Data

- Season input: `csv/fpl_season_data.csv` (often gitignored; tests use fixtures).
- Player IDs: `json/player_id_mapped.json`, `json/player_id_map.json`.
- Outputs: `fpl_output/` (reports, charts) — do not commit unless an issue requires it.

### FPL seasons and chips

- **Assistant Manager** chip existed in 2024/25, removed for **2025/26**. Do not reintroduce AM charts for current-season reports unless an issue says otherwise.
- **2025/26** has different chip rules (e.g. double chip) — follow the specific issue (#3, #16) for award/chip logic.
- Chip values in CSV include strings like `bboost`, `3xc`, `freehit`, etc.

### Awards (Polish copy)

- Report copy is **Polish**. Keep tone and joke titles consistent with existing `add_award(...)` entries.
- **Units must match the metric:**
  - Points → suffix `pkt` (or `pkt/gw` for per-GW rates).
  - Counts → suffix `razy` (e.g. `best_gw_count`, `autosub_count`, chip usage counts) — **not** `pkt`.
- When touching awards, skim all `add_award` value strings for consistent units.

### Pandas aggregation

- Never assign groupby results to `agg` columns via bare `.values` when keyed by `entry_name`. Use `.map()`, `merge(on="entry_name")`, or aligned joins so row order cannot mis-attach values (see issue #8).

### Import safety

- Prefer making `fpl_generate_report_v3.py` safe to import (guard side effects at module level) when working on entry points or tests (issue #7).

## Issue dependency hints

| Issue area | Notes |
|------------|--------|
| #9 Tests/fixtures | Foundation for #8, #11, chip logic tests |
| #13 Pin deps | Do before or with #15 CI |
| #15 CI | Should run `pytest` without live API once #9 exists |
| #10 Player mapping | May need bootstrap fetch script; keep optional/offline path |
| #14 PDF assets | WeasyPrint/CSS; avoid hard dependency on external URLs in CI |

Independent issues (e.g. #11 label fix, #6 README env name) can ship in parallel.

## Scope and style

- Smallest correct diff. Match existing style (pandas, matplotlib/seaborn, Polish strings).
- Comments only for non-obvious business rules (FPL scoring, chip seasons).
- Update README only when behavior, env vars, or setup commands change.

## Checklist before opening PR

- [ ] Acceptance criteria from the issue are met.
- [ ] No unrelated file churn.
- [ ] No secrets or large generated artifacts in the diff.
- [ ] Verification steps documented in the PR.
- [ ] Issue linked with `Closes #N` when appropriate.
