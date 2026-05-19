# fpl_stats

![CI](https://github.com/tymoteuszlenart/fpl_stats/actions/workflows/ci.yml/badge.svg)

**fpl_stats** is an application for analyzing and generating statistical reports based on Fantasy Premier League data.  
It allows you to process manager results, create season summaries, visualize statistics, and select winners in various categories.  
The results are presented as clear PDF reports and charts.

## Features

- Aggregation and analysis of FPL manager statistics
- Automatic generation of season summary reports (PDF)
- Visualization of key statistics (matplotlib, seaborn)
- Awards for best and worst performances in various categories
- Player name normalization and mapping

## Python environment

- **Supported Python:** 3.10 or newer (tested on 3.12).
- **Runtime dependencies:** `pip install -r requirements.txt` (pinned versions).
- **Development / tests:** `pip install -r requirements-dev.txt` (includes pytest).

### WeasyPrint system packages (PDF generation)

`fpl_generate_report_v3.py` uses WeasyPrint, which needs **Pango** and related libraries on the OS. Install these before `pip install` if PDF generation fails with missing-library errors.

**Ubuntu ≥ 20.04** (wheels; typical for a venv):

```bash
sudo apt install python3-pip libpango-1.0-0 libharfbuzz0b libpangoft2-1.0-0 libharfbuzz-subset0
```

**Debian ≥ 11** (wheels):

```bash
sudo apt install python3-pip libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0
```

Alternatively, install the distribution package: `sudo apt install weasyprint` (no separate pip install of weasyprint required for CLI use; this project still installs it via `requirements.txt` for the Python API).

See [WeasyPrint first steps](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html) for other platforms and build-from-source dependencies.

## Technologies Used

- **Python 3.10+**
- **pandas** – data processing and analysis
- **matplotlib** & **seaborn** – data visualization
- **json** – reading and writing player data
- **unicodedata** & **re** – player name normalization
- **matplotlib.backends.backend_pdf.PdfPages** – PDF report generation

## How to Use

1. **Create virtual environment** 
   Use Python 3.10 or newer (`python3 --version`).
   Create new virtual environment
   ```bash
   python -m venv venv
   ```
   For Windows use command:
   ```bash
   venv\Scripts\activate
   ```
   For Linux/macOS:
   ```bash
   source venv/bin/activate
   ```
2. **Install dependencies**   
   On Ubuntu/Debian, install [WeasyPrint system packages](#weasyprint-system-packages-pdf-generation) if you need PDF reports. Then install Python packages:
   ```bash
   pip install -r requirements.txt
   ```
   For development or running tests: `pip install -r requirements-dev.txt`.

3. Create your own `.env` file in the project root directory.  
   Add your session cookie from [https://fantasy.premierleague.com/api/me](https://fantasy.premierleague.com/api/me) and your league ID, for example:
   ```
   FPL_COOKIE=your_fpl_cookie_here
   FPL_LEAGUE_ID=your_league_id_here
   ```

   See `.env.example` for a template you can copy to `.env`.

4. Run the main fetcher script to download data:
   ```bash
   python fetch_fpl_league_data.py
   ```

   By default only **finished** gameweeks are fetched (from FPL `bootstrap-static` metadata). Other ranges:
   ```bash
   python fetch_fpl_league_data.py --through-current   # GW 1 through current
   python fetch_fpl_league_data.py --full-season       # all gameweeks (e.g. 38)
   python fetch_fpl_league_data.py --max-gw 10         # cap upper GW
   ```
   Optional env: `FPL_FETCH_MODE` (`finished`, `current`, or `full`), `FPL_MAX_GW`.

5. Run script to generate reports:
   ```bash
   python fpl_generate_report_v3.py
   ```

6. The output PDFs, stats and awards, will be saved in the `fpl_output/` directory.

## Tests

Automated tests use **pytest** and small fixtures under `tests/fixtures/` (no live FPL API or `.env` required).

```bash
pip install -r requirements-dev.txt
pytest
```

Useful variants:

```bash
pytest -q                    # quiet summary
pytest tests/test_wildcard_chip.py -v
python fpl_generate_report_v3.py --csv tests/fixtures/fpl_season_minimal.csv --no-write
```

CI runs `pytest` on push and pull requests to `main` (see `.github/workflows/test.yml`).

## Repository layout

| Path | Role |
|------|------|
| `fetch_fpl_league_data.py`, `fpl_generate_report_v3.py`, `map_players_name.py` | Source scripts |
| `img/`, `css/` | Committed assets for PDF/HTML reports |
| `json/` | Player ID mapping templates (`player_id_map.json`, `player_id_mapped.json`) |
| `csv/` | **Generated** — season data from the fetcher (e.g. `fpl_season_data.csv`); gitignored |
| `fpl_output/` | **Generated** — PDF/HTML reports and charts; gitignored |
| `.env` | **Local only** — API cookie and league id; gitignored |
| `tests/`, `tests/fixtures/` | Pytest suite and sample CSV/JSON (no network) |
| `venv/`, `__pycache__/`, `.pytest_cache/` | Local Python environment and cache; gitignored |

Do not commit live CSV dumps, report outputs, secrets, or cache directories. Source images, CSS, and JSON mapping files in the repo are intentional.

### Assistant Manager chip (2024/25 and earlier)

The **Assistant Manager** chip existed in 2024/25 but was **removed for 2025/26**. Season reports no longer include Assistant Manager charts or aggregation.

If you still have CSV data from 2024/25 with `chip == "manager"` rows, those rows remain in the file but are ignored by the report generator. To analyze that season manually, filter `csv/fpl_season_data.csv` where `chip == "manager"` and use the official FPL scoring for those gameweeks (the report never used correct AM scoring).

---

**Wybieramy Steczka Roku!**  
Let the best manager win!