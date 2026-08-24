import argparse
import csv
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path


SEASON_START_MONTH = 8
SEASON_START_DAY = 24


def season_dates(
    season_year: int,
) -> tuple[date, date]:
    """Return the inclusive start and exclusive end of a season."""
    start = date(
        season_year,
        SEASON_START_MONTH,
        SEASON_START_DAY,
    )

    end = date(
        season_year + 1,
        SEASON_START_MONTH,
        SEASON_START_DAY,
    )

    return start, end


def read_tournament_file(
    csv_path: Path,
) -> list[dict]:
    try:
        with csv_path.open(
            encoding="utf-8-sig",
            newline="",
        ) as file:
            return list(csv.DictReader(file))
    except (OSError, csv.Error) as error:
        print(f"Warning: could not read {csv_path}: {error}")
        return []


def build_ranking(season_year: int) -> None:
    season_start, season_end = season_dates(season_year)
    display_end = season_end - timedelta(days=1)

    players = {}
    included_tournaments = {}

    data_directory = Path("data")

    if not data_directory.exists():
        raise SystemExit(
            "The data directory does not exist. "
            "Scrape at least one tournament first."
        )

    tournament_files = sorted(
        data_directory.glob("*/tournament_*.csv")
    )

    if not tournament_files:
        raise SystemExit(
            "No tournament CSV files were found in data/."
        )

    for csv_path in tournament_files:
        rows = read_tournament_file(csv_path)

        if not rows:
            continue

        first_row = rows[0]

        try:
            tournament_date = date.fromisoformat(
                first_row["tournament_date"]
            )
        except (KeyError, ValueError):
            print(
                f"Warning: skipped {csv_path}; "
                "it has no valid tournament_date."
            )
            continue

        # Include the season's first day, but exclude the first day
        # of the following season.
        if not season_start <= tournament_date < season_end:
            continue

        tournament_id = first_row.get(
            "tournament_id",
            csv_path.stem,
        )

        tournament_name = first_row.get(
            "tournament_name",
            f"Tournament {tournament_id}",
        )

        # The ID is the unique key, so the same tournament cannot be
        # counted twice.
        included_tournaments[str(tournament_id)] = {
            "tournament_id": str(tournament_id),
            "tournament_name": tournament_name,
            "tournament_date": tournament_date.isoformat(),
        }

        seen_players_in_file = set()

        for row in rows:
            try:
                player_id = int(row["player_id"])
                points = float(
                    row["points"].replace(",", ".")
                )
            except (KeyError, TypeError, ValueError):
                print(
                    f"Warning: skipped an invalid row in {csv_path}."
                )
                continue

            # Prevent an accidental duplicate player row inside one
            # tournament file.
            if player_id in seen_players_in_file:
                print(
                    f"Warning: player {player_id} appears more than "
                    f"once in {csv_path}; duplicate ignored."
                )
                continue

            seen_players_in_file.add(player_id)

            player = players.setdefault(
                player_id,
                {
                    "player_id": player_id,
                    "player_name": row.get(
                        "player_name",
                        f"Player {player_id}",
                    ),
                    "country": row.get("country", ""),
                    "tournaments": 0,
                    "total_points": 0.0,
                    "results": [],
                },
            )

            # Use the most recent non-empty name and country.
            if row.get("player_name"):
                player["player_name"] = row["player_name"]

            if row.get("country"):
                player["country"] = row["country"]

            player["total_points"] += points
            player["tournaments"] += 1

            player["results"].append(
                {
                    "tournament_id": str(tournament_id),
                    "tournament_name": tournament_name,
                    "tournament_date": (
                        tournament_date.isoformat()
                    ),
                    "place": row.get("place", ""),
                    "points": round(points, 2),
                }
            )

    ranking = sorted(
        players.values(),
        key=lambda player: (
            -player["total_points"],
            -player["tournaments"],
            player["player_name"].casefold(),
        ),
    )

    for position, player in enumerate(ranking, start=1):
        player["rank"] = position
        player["total_points"] = round(
            player["total_points"],
            2,
        )

        player["results"].sort(
            key=lambda result: result["tournament_date"],
            reverse=True,
        )

    save_ranking_csv(
        ranking=ranking,
        season_year=season_year,
    )

    save_website_json(
        ranking=ranking,
        tournaments=list(
            included_tournaments.values()
        ),
        season_start=season_start,
        display_end=display_end,
    )

    print()
    print(
        f"Season: {season_start.isoformat()} through "
        f"{display_end.isoformat()}"
    )
    print(
        f"Tournaments included: "
        f"{len(included_tournaments)}"
    )
    print(f"Players included: {len(ranking)}")
    print(
        f"Saved CSV: "
        f"ranking_{season_year}_{season_year + 1}.csv"
    )
    print("Saved website data: docs/ranking.json")


def save_ranking_csv(
    ranking: list[dict],
    season_year: int,
) -> None:
    output_path = Path(
        f"ranking_{season_year}_{season_year + 1}.csv"
    )

    fieldnames = [
        "rank",
        "player_id",
        "player_name",
        "country",
        "tournaments",
        "total_points",
    ]

    with output_path.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        for player in ranking:
            writer.writerow(
                {
                    key: player[key]
                    for key in fieldnames
                }
            )


def save_website_json(
    ranking: list[dict],
    tournaments: list[dict],
    season_start: date,
    display_end: date,
) -> None:
    website_directory = Path("docs")
    website_directory.mkdir(exist_ok=True)

    tournaments.sort(
        key=lambda tournament: (
            tournament["tournament_date"],
            tournament["tournament_name"].casefold(),
        ),
        reverse=True,
    )

    website_data = {
        "title": "Annual Player Ranking",
        "season": (
            f"{season_start:%d.%m.%Y}"
            f"–{display_end:%d.%m.%Y}"
        ),
        "season_start": season_start.isoformat(),
        "season_end": display_end.isoformat(),
        "updated_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "tournament_count": len(tournaments),
        "player_count": len(ranking),
        "tournaments": tournaments,
        "players": ranking,
    }

    output_path = website_directory / "ranking.json"
    temporary_path = output_path.with_suffix(".tmp")

    with temporary_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            website_data,
            file,
            ensure_ascii=False,
            indent=2,
        )

    temporary_path.replace(output_path)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Build a seasonal player ranking from tournament CSV files."
        )
    )

    parser.add_argument(
        "season_year",
        type=int,
        help=(
            "The year in which the season starts, "
            "for example 2026."
        ),
    )

    arguments = parser.parse_args()

    if arguments.season_year < 2000:
        parser.error("The season year is not valid.")

    build_ranking(arguments.season_year)


if __name__ == "__main__":
    main()