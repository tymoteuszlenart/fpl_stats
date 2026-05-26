"""Build sanitized player ID → name mapping from FPL bootstrap-static data."""

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

import requests

BOOTSTRAP_URL = "https://fantasy.premierleague.com/api/bootstrap-static/"
DEFAULT_MAP_PATH = Path("json/player_id_map.json")
DEFAULT_MAPPED_PATH = Path("json/player_id_mapped.json")
REQUEST_TIMEOUT = 30


def sanitize_web_name(input_str):
    """Normalize FPL web_name to ASCII-friendly display text."""
    replacements = {
        "Ø": "O",
        "ø": "o",
        "Å": "A",
        "å": "a",
        "Æ": "Ae",
        "æ": "ae",
        "ß": "ss",
        "Ç": "C",
        "ç": "c",
        "Ñ": "N",
        "ñ": "n",
        "Ü": "U",
        "ü": "u",
        "Ö": "O",
        "ö": "o",
        "É": "E",
        "é": "e",
        "È": "E",
        "è": "e",
        "Á": "A",
        "á": "a",
        "Í": "I",
        "í": "i",
        "Ó": "O",
        "ó": "o",
        "Ú": "U",
        "ú": "u",
        "Ý": "Y",
        "ý": "y",
        "Ž": "Z",
        "ž": "z",
        "Š": "S",
        "š": "s",
        "Č": "C",
        "č": "c",
        "Ł": "L",
        "ł": "l",
        "Đ": "D",
        "đ": "d",
        "Ć": "C",
        "ć": "c",
        "Ę": "E",
        "ę": "e",
        "Ą": "A",
        "ą": "a",
        "Ś": "S",
        "ś": "s",
        "Ź": "Z",
        "ź": "z",
        "Ż": "Z",
        "ż": "z",
        "Ń": "N",
        "ń": "n",
        "Ů": "U",
        "ů": "u",
        "Ř": "R",
        "ř": "r",
        "Ť": "T",
        "ť": "t",
        "Ň": "N",
        "ň": "n",
        "Ě": "E",
        "ě": "e",
        "Ĺ": "L",
        "ĺ": "l",
        "Ľ": "L",
        "ľ": "l",
        "Ď": "D",
        "ď": "d",
        "Ť": "T",
        "ť": "t",
        "Ň": "N",
        "ň": "n",
        "Ŕ": "R",
        "ŕ": "r",
        "Ÿ": "Y",
        "ÿ": "y",
        "Õ": "O",
        "õ": "o",
        "Ã": "A",
        "ã": "a",
        "Œ": "Oe",
        "œ": "oe",
        "ğ": "g",
        "ı": "i",
    }
    for src, target in replacements.items():
        input_str = input_str.replace(src, target)
    nfkd_form = unicodedata.normalize("NFKD", input_str)
    only_ascii = "".join(c for c in nfkd_form if not unicodedata.combining(c))
    return re.sub(r"[^A-Za-z0-9. ]+", "", only_ascii)


def build_mapped_players(elements):
    """Return [{id, name}, ...] from bootstrap 'elements' list."""
    mapped = []
    for element in elements:
        if "id" not in element or "web_name" not in element:
            continue
        mapped.append(
            {
                "id": element["id"],
                "name": sanitize_web_name(element["web_name"]),
            }
        )
    return mapped


def fetch_bootstrap_static(url=BOOTSTRAP_URL, timeout=REQUEST_TIMEOUT):
    """Download bootstrap-static JSON (no FPL cookie required)."""
    response = requests.get(
        url,
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()


def load_bootstrap_file(map_path=DEFAULT_MAP_PATH):
    """Load committed or previously saved bootstrap snapshot."""
    with open(map_path, encoding="utf-8") as file:
        data = json.load(file)
    elements = data.get("elements")
    if not isinstance(elements, list):
        raise ValueError(f"{map_path}: missing or invalid 'elements' list")
    return elements


def write_mapped_json(mapped, mapped_path=DEFAULT_MAPPED_PATH):
    mapped_path = Path(mapped_path)
    mapped_path.parent.mkdir(parents=True, exist_ok=True)
    with open(mapped_path, "w", encoding="utf-8") as file:
        json.dump(mapped, file, ensure_ascii=False, indent=2)


def write_bootstrap_snapshot(bootstrap_data, map_path=DEFAULT_MAP_PATH):
    """Persist full bootstrap payload (elements used for mapping)."""
    map_path = Path(map_path)
    map_path.parent.mkdir(parents=True, exist_ok=True)
    with open(map_path, "w", encoding="utf-8") as file:
        json.dump(bootstrap_data, file, ensure_ascii=False, indent=2)


def refresh_from_bootstrap(
    *,
    url=BOOTSTRAP_URL,
    map_path=DEFAULT_MAP_PATH,
    mapped_path=DEFAULT_MAPPED_PATH,
):
    """Download bootstrap-static and update map + mapped JSON files."""
    bootstrap_data = fetch_bootstrap_static(url=url)
    elements = bootstrap_data.get("elements")
    if not isinstance(elements, list):
        raise ValueError("bootstrap-static: missing or invalid 'elements'")
    write_bootstrap_snapshot(bootstrap_data, map_path)
    mapped = build_mapped_players(elements)
    write_mapped_json(mapped, mapped_path)
    return mapped


def refresh_from_local_map(map_path=DEFAULT_MAP_PATH, mapped_path=DEFAULT_MAPPED_PATH):
    """Regenerate player_id_mapped.json from existing player_id_map.json."""
    elements = load_bootstrap_file(map_path)
    mapped = build_mapped_players(elements)
    write_mapped_json(mapped, mapped_path)
    return mapped


def main(argv=None):
    parser = argparse.ArgumentParser(description="Refresh FPL player ID → name mapping files.")
    parser.add_argument(
        "--fetch",
        action="store_true",
        help="Download bootstrap-static and update json/player_id_map.json "
        "and json/player_id_mapped.json",
    )
    parser.add_argument(
        "--map-path",
        type=Path,
        default=DEFAULT_MAP_PATH,
        help=f"Bootstrap snapshot path (default: {DEFAULT_MAP_PATH})",
    )
    parser.add_argument(
        "--mapped-path",
        type=Path,
        default=DEFAULT_MAPPED_PATH,
        help=f"Sanitized mapping output (default: {DEFAULT_MAPPED_PATH})",
    )
    args = parser.parse_args(argv)

    try:
        if args.fetch:
            mapped = refresh_from_bootstrap(
                map_path=args.map_path,
                mapped_path=args.mapped_path,
            )
            print(
                f"Downloaded bootstrap-static → {args.map_path}, "
                f"{len(mapped)} players → {args.mapped_path}"
            )
        else:
            mapped = refresh_from_local_map(
                map_path=args.map_path,
                mapped_path=args.mapped_path,
            )
            print(f"Regenerated {len(mapped)} players from {args.map_path} → {args.mapped_path}")
    except (OSError, ValueError, requests.RequestException) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
