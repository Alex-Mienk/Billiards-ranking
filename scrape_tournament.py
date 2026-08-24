import argparse
import csv
import html
import json
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

CSV_FIELDNAMES = [
    "tournament_id",
    "tournament_date",
    "player_id",
    "surname",
    "given_name",
    "player_name",
    "country",
    "city",
    "place",
    "points",
    "source_url",
    "scraped_at",
]


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
    page_text = response.content.decode("utf-8", errors="replace")
    soup = BeautifulSoup(page_text, "html.parser")

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

        surname = clean_value(player[0])
        given_name = clean_value(player[1])
        country = clean_value(player[2])
        city = clean_value(player[3])
        place = (
            clean_value(player[10])
            if len(player) > 10
            else ""
        )

        if not place:
            place_element = row.select_one("td")
            place = (
                place_element.get_text(" ", strip=True)
                if place_element
                else ""
            )

        points = points_element.get_text(" ", strip=True).replace(
            ",",
            ".",
        )

        try:
            float(points)
        except ValueError:
            continue

        results.append(
            {
                "tournament_id": tournament_id,
                "tournament_date": tournament_date.isoformat(),
                "player_id": player_id,
                "surname": surname,
                "given_name": given_name,
                "player_name": " ".join(
                    value
                    for value in (surname, given_name)
                    if value
                ),
                "country": country,
                "city": city,
                "place": place,
                "points": points,
                "source_url": url,
                "scraped_at": scraped_at,
            }
        )

    if not results:
        raise RuntimeError(
            "No player results were found in the standings table."
        )

    print(f"Tournament: {tournament_name}")
    print(f"Players found: {len(results)}")
    return results


def save_results(
    results: list[dict],
    tournament_id: int,
    tournament_date: date,
) -> Path:
    output_directory = Path("data") / str(tournament_date.year)
    output_directory.mkdir(parents=True, exist_ok=True)
    output_path = output_directory / f"tournament_{tournament_id}.csv"

    with output_path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        writer = csv.DictWriter(file, fieldnames=CSV_FIELDNAMES)
        writer.writeheader()
        writer.writerows(results)

    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download tournament standings to a CSV file."
    )
    parser.add_argument(
        "tournament_id",
        type=int,
        help="Tournament Service tournament ID, for example 55931.",
    )
    parser.add_argument(
        "tournament_date",
        type=parse_date,
        help="Tournament date in YYYY-MM-DD format.",
    )
    arguments = parser.parse_args()

    if arguments.tournament_id <= 0:
        parser.error("The tournament ID must be a positive integer.")

    try:
        results = scrape_tournament(
            arguments.tournament_id,
            arguments.tournament_date,
        )
        output_path = save_results(
            results,
            arguments.tournament_id,
            arguments.tournament_date,
        )
    except (OSError, csv.Error, RuntimeError) as error:
        parser.exit(1, f"Error: {error}\n")

    print(f"Saved: {output_path}")


if __name__ == "__main__":
    main()
