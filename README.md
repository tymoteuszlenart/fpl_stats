# fpl_stats

**fpl_stats** is an application for analyzing and generating statistical reports based on Fantasy Premier League data.  
It allows you to process manager results, create season summaries, visualize statistics, and select winners in various categories.  
The results are presented as clear PDF reports and charts.

## Features

- Aggregation and analysis of FPL manager statistics
- Automatic generation of season summary reports (PDF)
- Visualization of key statistics (matplotlib, seaborn)
- Awards for best and worst performances in various categories
- Player name normalization and mapping

## Technologies Used

- **Python 3**
- **pandas** – data processing and analysis
- **matplotlib** & **seaborn** – data visualization
- **json** – reading and writing player data
- **unicodedata** & **re** – player name normalization
- **matplotlib.backends.backend_pdf.PdfPages** – PDF report generation

## How to Use

1. **Install dependencies**  
   Make sure you have Python 3 installed.  
   Install all required libraries using pip:
   ```bash
   pip install -r requirements.txt
   ```

2. Create your own `.env` file in the project root directory.  
   Add your session cookie from [https://fantasy.premierleague.com/api/me](https://fantasy.premierleague.com/api/me) and your league ID, for example:
   ```
   FPL_COOKIE=your_fpl_cookie_here
   LEAGUE_ID=your_league_id_here
   ```

3. Run the main fetcher script to download data:
   ```bash
   python fetch_fpl_league_data.py
   ```

3. Run script to generate reports:
   ```bash
   python fpl_generate_report_v3.py
   ```

4. The output PDFs, stats and awards, will be saved in the `fpl_output/` directory.

---

**Wybieramy Steczka Roku!**  
Let the best manager win!