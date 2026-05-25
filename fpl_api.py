"""HTTP client and FPL API endpoint helpers."""

import json
import os
import time

import requests
from dotenv import load_dotenv

load_dotenv()

COOKIE = os.getenv("FPL_COOKIE")

REQUEST_TIMEOUT = 30
MAX_RETRIES = 4
INITIAL_BACKOFF = 1.0

BOOTSTRAP_URL = "https://fantasy.premierleague.com/api/bootstrap-static/"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Cookie": COOKIE,
}


class FplApiError(Exception):
    """FPL HTTP/API failure."""


class FplAuthError(FplApiError):
    """401/403 — invalid or expired session cookie."""


class FplNotFoundError(FplApiError):
    """404 — resource not found."""


class FplGameweekNotAvailableError(FplNotFoundError):
    """404 for a gameweek that is not finished / not yet published."""


class FplRateLimitError(FplApiError):
    """429 — rate limited after retries."""


class FplResponseError(FplApiError):
    """JSON parse failure or unexpected response shape."""


def _status_message(status_code, url):
    if status_code in (401, 403):
        return (
            f"HTTP {status_code} (authentication failed). "
            "Check FPL_COOKIE in .env — copy a fresh session cookie from "
            "https://fantasy.premierleague.com while logged in."
        )
    if status_code == 404:
        return f"HTTP 404 (not found): {url}"
    if status_code == 429:
        return "HTTP 429 (rate limited). Try again later or reduce request frequency."
    return f"HTTP {status_code}: {url}"


def fpl_get(url, *, context="", retries=MAX_RETRIES, backoff=INITIAL_BACKOFF):
    """GET JSON from the FPL API with status checks and transient retries."""
    prefix = f"{context}: " if context else ""
    last_error = None

    for attempt in range(retries):
        try:
            response = requests.get(
                url, headers=HEADERS, timeout=REQUEST_TIMEOUT
            )
        except requests.Timeout as exc:
            last_error = FplApiError(
                f"{prefix}Request timed out after {REQUEST_TIMEOUT}s: {url}"
            )
            last_error.__cause__ = exc
        except requests.RequestException as exc:
            last_error = FplApiError(
                f"{prefix}Network error for {url}: {exc}"
            )
            last_error.__cause__ = exc
        else:
            status = response.status_code
            if status in (401, 403):
                raise FplAuthError(prefix + _status_message(status, url))
            if status == 404:
                raise FplNotFoundError(prefix + _status_message(status, url))
            if status == 429 or status >= 500:
                last_error = (
                    FplRateLimitError(prefix + _status_message(status, url))
                    if status == 429
                    else FplApiError(prefix + _status_message(status, url))
                )
            elif not response.ok:
                raise FplApiError(prefix + _status_message(status, url))
            else:
                try:
                    return response.json()
                except json.JSONDecodeError as exc:
                    snippet = response.text[:200].strip()
                    raise FplResponseError(
                        f"{prefix}Invalid JSON from {url}: {exc}. "
                        f"Body starts with: {snippet!r}"
                    ) from exc

        if attempt < retries - 1:
            delay = backoff * (2**attempt)
            print(
                f"{prefix}Retry {attempt + 1}/{retries - 1} in {delay:.1f}s "
                f"({last_error})"
            )
            time.sleep(delay)

    raise last_error


def get_bootstrap_events():
    """Return gameweek metadata from bootstrap-static."""
    data = fpl_get(BOOTSTRAP_URL, context="Bootstrap static")
    events = data.get("events")
    if not isinstance(events, list) or not events:
        raise FplResponseError("Bootstrap static: missing or empty 'events'")
    return events


def get_league_entries(league_id):
    entries = []
    page = 1
    while True:
        url = (
            f"https://fantasy.premierleague.com/api/leagues-classic/"
            f"{league_id}/standings/?page_standings={page}"
        )
        data = fpl_get(url, context=f"League {league_id} standings page {page}")
        try:
            standings = data["standings"]
            entries.extend(standings["results"])
            if not standings["has_next"]:
                break
            page += 1
        except (KeyError, TypeError) as exc:
            raise FplResponseError(
                f"League {league_id} standings page {page}: "
                f"unexpected response shape ({exc})"
            ) from exc
    return entries
