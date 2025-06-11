"""
FPL HTML Generation Functions

This module contains functions for generating HTML documents for the FPL season report.
"""

import logging
from typing import Dict, List
from pathlib import Path
from weasyprint import HTML

logger = logging.getLogger(__name__)

def generate_awards_documents(awards: List[Dict[str, str]], 
                          season: str, 
                          html_path: str,
                          pdf_path: str) -> None:
    """Generate HTML and PDF documents with awards.
    
    Args:
        awards: List of award dictionaries
        season: Current season string
        html_path: Path to save HTML file
        pdf_path: Path to save PDF file
    """
    try:
        logger.info("Generating awards section...")

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <link rel="stylesheet" href="../css/style.css" />
            <title>Ligowe Steczki - Nagrody</title>
        </head>
        <body>
        <div class="cover">
            <img class="emoji-icon" src="https://em-content.zobj.net/source/apple/391/trophy_1f3c6.png" alt="trophy">
            <h1>Ligowe Steczki</h1>
            <h2>Uroczyste Rozdanie Nagród</h2>
            <div class="season">Sezon {season}</div>
        </div>
        """

        for award in awards:
            html += f"""
            <div class="award">
                <div class="title">
                    <img class="emoji-icon" src="https://em-content.zobj.net/source/apple/391/trophy_1f3c6.png" alt="trophy">
                    {award['Nagroda']}
                </div>
                <div class="label">
                    <img class="emoji-icon" src="https://em-content.zobj.net/source/apple/391/t-shirt_1f455.png" alt="shirt">
                    <strong>Drużyna:</strong> {award['Drużyna']}
                </div>
                <div class="label">
                    <img class="emoji-icon" src="https://em-content.zobj.net/source/apple/391/direct-hit_1f3af.png" alt="target">
                    <strong>Za co:</strong> {award['Za co']}
                </div>
                <div class="label">
                    <img class="emoji-icon" src="https://em-content.zobj.net/source/apple/391/bar-chart_1f4ca.png" alt="chart">
                    <strong>Wartość:</strong> {award['Wartość']}
                </div>
                <img class="seal" src="../img/seal.png">
                <div class="signature">
                    <div class="sig-line">_________________________</div>
                    <div class="sig-title">Przewodniczący Komisji</div>
                    <div class="sig-sub">ds. Nagród Ligowych</div>
                    <div class="sig-org">FPL Steczek La Liga</div>
                </div>
                <div class="footer">Sezon {season}</div>
            </div>
            """

        html += "</body></html>"

        # Write HTML file
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)
            logger.info(f"Saved awards HTML to {html_path}")

        # Generate PDF
        logger.info("Converting awards HTML to PDF...")
        HTML(html_path).write_pdf(pdf_path)
        logger.info(f"Saved awards PDF to {pdf_path}")
        
    except Exception as e:
        logger.error(f"Error generating awards documents: {str(e)}")
        raise
