# fpl_stats

![CI](https://github.com/tymoteuszlenart/fpl_stats/actions/workflows/ci.yml/badge.svg)

Analyze Fantasy Premier League league data and generate season PDF/HTML reports with charts and Polish-language awards.

**Python 3.10+** · `pip install -r requirements.txt` · tests/dev: `pip install -r requirements-dev.txt`

## Quick start

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env              # add FPL_COOKIE + FPL_LEAGUE_ID
python fetch_fpl_league_data.py
python fpl_generate_report_v3.py  # outputs to fpl_output/
```

**`.env`** — session cookie from [fantasy.premierleague.com/api/me](https://fantasy.premierleague.com/api/me) and your league ID (`FPL_LEAGUE_ID`).

### Fetch options

Writes `csv/fpl_season_data.csv` (manager/GW stats) and `csv/fpl_season_picks.csv` (player picks). By default only **finished** gameweeks are fetched.

```bash
python fetch_fpl_league_data.py --through-current   # through current GW
python fetch_fpl_league_data.py --full-season       # all GWs (e.g. 38)
python fetch_fpl_league_data.py --max-gw 10
```

Env: `FPL_FETCH_MODE` (`finished`, `current`, `full`), `FPL_MAX_GW`.

### Player name mapping

```bash
python map_players_name.py --fetch   # bootstrap snapshot → json/player_id_*.json
python map_players_name.py           # offline rebuild from existing snapshot
```

Re-run `--fetch` at the start of a new season or when awards show `Gracz #<id>`.

## PDF generation (WeasyPrint)

Reports need **Pango/Cairo** native libraries. See [WeasyPrint first steps](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html) for full OS instructions.

```bash
# macOS
brew install pango

# Ubuntu/Debian
sudo apt install libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0
```

Awards use local assets only (`css/`, `img/`) — no network required for PDF/HTML.

## Development

**Tests** (fixtures only, no live API):

```bash
pytest
python fpl_generate_report_v3.py --csv tests/fixtures/fpl_season_minimal.csv --no-write
```

**Formatting** — Prettier (JSON/CSS/MD/YAML) + Ruff (Python):

```bash
npm install && pip install -r requirements-dev.txt
npm run format:all              # or format:check:all for CI-style check
```

## Layout

| Path | Role |
| --- | --- |
| `fetch_fpl_league_data.py`, `fpl_generate_report_v3.py`, `map_players_name.py` | Entry scripts |
| `fpl_stats/` | Report/aggregation library |
| `json/` | Player ID mapping (committed) |
| `csv/`, `fpl_output/`, `.env` | Generated/local — gitignored |
| `tests/fixtures/` | Offline test data |

**Note:** The Assistant Manager chip (2024/25) was removed for 2025/26; reports ignore `chip == "manager"` rows.

---

**Wybieramy Steczka Roku!**
