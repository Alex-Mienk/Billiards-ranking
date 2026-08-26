import argparse
import csv
import html
import json
from datetime import date, datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from scrape_tournament import BASE_URL, REQUEST_HEADERS, parse_date


MATCH_FIELDNAMES = [
    "tournament_id",
    "tournament_date",
    "match_id",
    "round",
    "round_name",
    "match_number",
    "player_a_id",
    "player_a_name",
    "player_a_score",
    "player_b_id",
    "player_b_name",
    "player_b_score",
    "table_number",
    "started_at",
    "ended_at",
    "source_url",
]


class MatchRowParser(HTMLParser):
    """Parse Tournament Service's intentionally compact match table."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows = []
        self.current_row = None
        self.current_cell = None

    def finish_cell(self) -> None:
        if self.current_row is None or self.current_cell is None:
            return

        self.current_cell["text"] = " ".join(
            self.current_cell["text"].split()
        )
        self.current_row["cells"].append(self.current_cell)
        self.current_cell = None

    def finish_row(self) -> None:
        if self.current_row is None:
            return

        self.finish_cell()
        self.rows.append(self.current_row)
        self.current_row = None

    def handle_starttag(self, tag, attrs) -> None:
        attributes = dict(attrs)

        if tag == "tr" and attributes.get("data-match"):
            self.finish_row()
            self.current_row = {
                "attributes": attributes,
                "cells": [],
            }
        elif tag == "td" and self.current_row is not None:
            self.finish_cell()
            self.current_cell = {
                "attributes": attributes,
                "text": "",
            }

    def handle_data(self, data) -> None:
        if self.current_cell is not None:
            self.current_cell["text"] += f" {data}"

    def close(self) -> None:
        super().close()
        self.finish_row()


def timestamp_from_epoch(value: str) -> str:
    if not value or not value.isdigit():
        return ""

    return datetime.fromtimestamp(
        int(value),
        tz=timezone.utc,
    ).isoformat()


def participant_name(participants: dict, player_id: str) -> str:
    player = participants.get(player_id, [])
    return " ".join(
        str(value).strip()
        for value in player[:2]
        if value
    )


def parse_matches(
    page_text: str,
    tournament_id: int,
    tournament_date: date,
    source_url: str,
) -> list[dict]:
    soup = BeautifulSoup(page_text, "html.parser")
    participants_element = soup.select_one("textarea#participants")

    if participants_element is None:
        raise RuntimeError("The match participant data was not found.")

    try:
        participants = json.loads(
            html.unescape(participants_element.get_text())
        )
    except json.JSONDecodeError as error:
        raise RuntimeError(
            "The match participant data could not be decoded."
        ) from error

    parser = MatchRowParser()
    parser.feed(page_text)
    parser.close()
    matches = []

    for parsed_row in parser.rows:
        attributes = parsed_row["attributes"]
        cells = parsed_row["cells"]
        player_ids = [
            class_name[1:]
            for class_name in attributes.get("class", "").split()
            if class_name.startswith("p") and class_name[1:].isdigit()
        ]
        parameters = attributes.get("data-params", "").split("×")

        if len(player_ids) != 2 or len(cells) < 5:
            continue

        start_epoch = parameters[6] if len(parameters) > 6 else ""
        end_epoch = parameters[7] if len(parameters) > 7 else ""
        table_number = parameters[9] if len(parameters) > 9 else ""

        matches.append(
            {
                "tournament_id": str(tournament_id),
                "tournament_date": tournament_date.isoformat(),
                "match_id": attributes["data-match"],
                "round": cells[0]["text"],
                "round_name": cells[0]["attributes"].get("title", ""),
                "match_number": cells[1]["text"].lstrip("#"),
                "player_a_id": player_ids[0],
                "player_a_name": participant_name(
                    participants,
                    player_ids[0],
                ),
                "player_a_score": cells[3]["text"],
                "player_b_id": player_ids[1],
                "player_b_name": participant_name(
                    participants,
                    player_ids[1],
                ),
                "player_b_score": cells[4]["text"],
                "table_number": table_number,
                "started_at": timestamp_from_epoch(start_epoch),
                "ended_at": timestamp_from_epoch(end_epoch),
                "source_url": source_url,
            }
        )

    if not matches:
        raise RuntimeError("No completed match records were found.")

    return matches


def scrape_matches(
    tournament_id: int,
    tournament_date: date,
) -> list[dict]:
    source_url = BASE_URL.format(tournament_id=tournament_id)

    try:
        response = requests.get(
            source_url,
            headers=REQUEST_HEADERS,
            timeout=30,
        )
        response.raise_for_status()
    except requests.RequestException as error:
        raise RuntimeError(
            f"Could not download matches for {tournament_id}: {error}"
        ) from error

    page_text = response.content.decode("utf-8", errors="replace")
    return parse_matches(
        page_text,
        tournament_id,
        tournament_date,
        source_url,
    )


def save_matches(
    matches: list[dict],
    tournament_id: int,
    tournament_date: date,
) -> Path:
    output_directory = Path("data") / str(tournament_date.year)
    output_directory.mkdir(parents=True, exist_ok=True)
    output_path = output_directory / f"matches_{tournament_id}.csv"

    with output_path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=MATCH_FIELDNAMES,
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(matches)

    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download match times and table assignments."
    )
    parser.add_argument("tournament_id", type=int)
    parser.add_argument("tournament_date", type=parse_date)
    arguments = parser.parse_args()

    if arguments.tournament_id <= 0:
        parser.error("The tournament ID must be a positive integer.")

    try:
        matches = scrape_matches(
            arguments.tournament_id,
            arguments.tournament_date,
        )
        output_path = save_matches(
            matches,
            arguments.tournament_id,
            arguments.tournament_date,
        )
    except (OSError, csv.Error, RuntimeError) as error:
        parser.exit(1, f"Error: {error}\n")

    print(f"Matches found: {len(matches)}")
    print(f"Saved: {output_path}")


if __name__ == "__main__":
    main()
