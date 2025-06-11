# FPL Stats Generator

**FPL Stats Generator** to zaawansowane narzędzie do analizy i generowania raportów statystycznych dla Fantasy Premier League. Aplikacja przetwarza wyniki menedżerów, tworzy podsumowania sezonowe, wizualizuje statystyki i przyznaje nagrody w różnych kategoriach.

## Główne funkcje

### Analiza danych
- Kompleksowa analiza statystyk drużyn
- Śledzenie punktów kapitanów
- Analiza skuteczności transferów
- Monitorowanie punktów na ławce
- Porównanie wyników między rundami

### Wizualizacje
- Wykresy statystyk sezonowych
- Analiza wykorzystania chipów
- Porównanie wildcardów
- Statystyki kapitanów

### Nagrody i wyróżnienia
- Automatyczne przyznawanie nagród w różnych kategoriach
- Generowanie dyplomów w formacie HTML i PDF
- Szczegółowe uzasadnienia dla każdej nagrody

## Architektura

Projekt jest podzielony na moduły:
- `fpl_data.py` - przetwarzanie i analiza danych
- `fpl_plotting.py` - generowanie wykresów i wizualizacji
- `fpl_html.py` - generowanie dokumentów HTML/PDF
- `fpl_generate_report_v3.py` - główny skrypt koordynujący

## Wymagania techniczne

### Zależności
- Python 3.8+
- pandas - przetwarzanie danych
- matplotlib & seaborn - wizualizacje
- weasyprint - generowanie PDF

### Struktura projektu
```
fpl_stats/
├── csv/                    # Pliki z danymi
├── json/                   # Mapowania zawodników
├── css/                    # Style dla raportów
├── img/                    # Grafiki do raportów
├── test/                   # Testy jednostkowe
└── fpl_output/            # Wygenerowane raporty
```

## Instalacja

1. Sklonuj repozytorium:
```bash
git clone https://github.com/username/fpl_stats.git
cd fpl_stats
```

2. Stwórz wirtualne środowisko:
```bash
python -m venv venv
source venv/bin/activate  # dla macOS/Linux
# lub
venv\Scripts\activate     # dla Windows
```

3. Zainstaluj zależności:
```bash
pip install -r requirements.txt
```

## Technologies Used

- **Python 3**
- **pandas** – data processing and analysis
- **matplotlib** & **seaborn** – data visualization
- **json** – reading and writing player data
- **unicodedata** & **re** – player name normalization
- **matplotlib.backends.backend_pdf.PdfPages** – PDF report generation

## How to Use

1. **Create virtual environment** 
   Make sure you have Python 3 installed.
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
   Install all required libraries using pip:
   ```bash
   pip install -r requirements.txt
   ```

3. Create your own `.env` file in the project root directory.  
   Add your session cookie from [https://fantasy.premierleague.com/api/me](https://fantasy.premierleague.com/api/me) and your league ID, for example:
   ```
   FPL_COOKIE=your_fpl_cookie_here
   LEAGUE_ID=your_league_id_here
   ```

4. Run the main fetcher script to download data:
   ```bash
   python fetch_fpl_league_data.py
   ```

5. Run script to generate reports:
   ```bash
   python fpl_generate_report_v3.py
   ```

6. The output PDFs, stats and awards, will be saved in the `fpl_output/` directory.

---

**Wybieramy Steczka Roku!**  
Let the best manager win!