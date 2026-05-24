"""Awards HTML/PDF assets resolve from project root without external URLs."""

import os

from fpl_generate_report_v3 import build_awards_html, report_project_root


def test_awards_html_uses_local_assets_only():
    awards = [
        {
            "Nagroda": "Test",
            "Drużyna": "FC Test",
            "Za co": "test",
            "Wartość": "1 pkt",
        }
    ]
    html = build_awards_html(awards, "2024/25")
    assert "em-content.zobj.net" not in html
    assert "http://" not in html
    assert "https://" not in html
    assert 'href="css/style.css"' in html
    assert 'src="img/seal.png"' in html
    assert "🏆" in html


def test_report_project_root_contains_css_and_img():
    root = report_project_root()
    assert os.path.isfile(os.path.join(root, "css", "style.css"))
    assert os.path.isfile(os.path.join(root, "img", "seal.png"))
