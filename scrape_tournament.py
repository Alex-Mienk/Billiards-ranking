import csv
import html
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://tournamentservice.net/embed/{tournament_id}/standing"

REQUEST_HEADERS = {
    "User-Agent": (
        "TournamentRatingsBot/1.0 "
        "(public tournament results archive; "
        "contact: mienko.alex@gmail.com)"
    )
}


def clean_value(value) -> str:
    """Convert missing or false values into an empty string."""
    if value is None or value is False:
        return ""

    return str(value).strip()


def parse_date(value: str) -> date:
    """Parse a date supplied as YYYY-MM-DD."""
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise SystemExit(
            f"Invalid date: {value}\n"
            "Use YYYY-MM-DD format, for example 2026-08-30."
        ) from error


def scrape_tournament(
    tournament_id: int,
    tournament_date: date,
) -> list[dict]:
    url = BASE_URL.format(tournament_id=tournament_id)

    print(f"Downloading tournament {tournament_id}...")

    try:
        response = requests.get(
            url,
            headers=REQUEST_HEADERS,
            timeout=30,
        )
        response.raise_for_status()
    except requests.RequestException as error:
        raise RuntimeError(
            f"Could not download tournament {tournament_id}: {error}"
        ) from error

    # Tournament Service uses UTF-8, but requests may occasionally
    # detect a different encoding.
    response.encoding = "utf-8"

    soup = BeautifulSoup(response.text, "html.parser")

    tournament_name = (
        soup.title.get_text(" ", strip=True)
        if soup.title
        else f"Tournament {tournament_id}"
    )

    participants_element = soup.select_one("textarea#participants")

    if participants_element is None:
        raise RuntimeError(
            "The participant information was not found. "
            "The tournament may not exist, or the website structure "
            "may have changed."
        )

    participants_text = html.unescape(
        participants_element.get_text()
    )

    try:
        participants = json.loads(participants_text)
    except json.JSONDecodeError as error:
        raise RuntimeError(
            "The participant information could not be decoded."
        ) from error

    standings = soup.select_one("#tab-standing table.standing")

    if standings is None:
        raise RuntimeError(
            "The final standings table was not found. "
            "The tournament may not be finished yet."
        )

    scraped_at = datetime.now(timezone.utc).isoformat()
    results = []

    for row in standings.select("tr.player-row[data-id]"):
        player_id = row.get("data-id")

        if not player_id:
            continue

        points_element = row.select_one("td.points")

        if points_element is None:
            continue

        player = participants.get(player_id)

        if not player or len(player) < 7:
            continue