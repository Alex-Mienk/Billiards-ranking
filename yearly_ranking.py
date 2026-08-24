import argparse
import csv
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path


SEASON_START_MONTH = 1
SEASON_START_DAY = 1

# Tournament Service may assign more than one player ID to the same
# person. Map duplicate IDs to the ID used for the combined ranking.
PLAYER_ID_ALIASES = {
    85: 91311,
    10378: 94439,
    56346: 17811,
    76844: 53373,
    79229: 96995,
    85155: 45929,
    87663: 100787,
    99885: 99887,
    96997: 87815,
    100786: 45956,
    100957: 53373,
    103855: 87816,
    87818: 53732,
}

PLAYER_PROFILES = {
    17811: {
        "player_name": "Dementii Danylo",
        "country": "POL",
    },
    45929: {
        "player_name": "Havadziuk Serhii",
        "country": "UKR",
    },
    45956: {
        "player_name": "Bikmetov Maxim",
        "country": "UKR",
    },
    53373: {
        "player_name": "Олексій Мієнко",
        "country": "UKR",
    },
    53732: {
        "player_name": "Kondratiuk Alexandr",
        "country": "POL",
    },
    87815: {
        "player_name": "Klubkov Dmytro",
        "country": "POL",
    },
    87816: {
        "player_name": "Kurchevskyi Daniil",
        "country": "POL",
    },
    91311: {
        "player_name": "Міщенко Адріан",
        "country": "UKR",
    },
    94439: {
        "player_name": "Дмитрюк Андрій",
        "country": "POL",
    },
    96995: {
        "player_name": "Lobov Maksym",
        "country": "CYP",
    },
    99887: {
        "player_name": "Papou Vladimir",
        "country": "POL",
    },
    100787: {
        "player_name": "Zhygimont Aleh",
        "country": "POL",
    },
}

RANKING_PERIODS = (
    {
        "id": "winter",
        "label": "Winter",
        "months": (1, 2),
    },
    {
        "id": "spring",
        "label": "Spring",
        "months": (3, 4, 5),
    },
    {
        "id": "summer",
        "label": "Summer",
        "months": (6, 7, 8),
    },
)


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

            player_id = PLAYER_ID_ALIASES.get(
                player_id,
                player_id,
            )

            # Prevent an accidental duplicate player row inside one
            # tournament file.
            if player_id in seen_players_in_file:
                print(
                    f"Warning: player {player_id} appears more than "
                    f"once in {csv_path}; duplicate ignored."
                )
                continue

            seen_players_in_file.add(player_id)

            canonical_profile = PLAYER_PROFILES.get(player_id)

            player = players.setdefault(
                player_id,
                {
                    "player_id": player_id,
                    "player_name": (
                        canonical_profile["player_name"]
                        if canonical_profile
                        else row.get(
                            "player_name",
                            f"Player {player_id}",
                        )
                    ),
                    "country": (
                        canonical_profile["country"]
                        if canonical_profile
                        else row.get("country", "")
                    ),
                    "tournaments": 0,
                    "total_points": 0.0,
                    "results": [],
                },
            )

            # Use the most recent non-empty name and country.
            if not canonical_profile and row.get("player_name"):
                player["player_name"] = row["player_name"]

            if not canonical_profile and row.get("country"):
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
        ranking_periods=build_period_rankings(
            ranking=ranking,
            tournaments=list(included_tournaments.values()),
            season_year=season_year,
        ),
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


def build_period_rankings(
    ranking: list[dict],
    tournaments: list[dict],
    season_year: int,
) -> list[dict]:
    periods = []

    for period_definition in RANKING_PERIODS:
        months = period_definition["months"]
        period_players = []

        for annual_player in ranking:
            results = [
                result
                for result in annual_player["results"]
                if date.fromisoformat(
                    result["tournament_date"]
                ).month in months
                and date.fromisoformat(
                    result["tournament_date"]
                ).year == season_year
            ]

            if not results:
                continue

            period_players.append(
                {
                    "player_id": annual_player["player_id"],
                    "player_name": annual_player["player_name"],
                    "country": annual_player["country"],
                    "tournaments": len(results),
                    "total_points": round(
                        sum(result["points"] for result in results),
                        2,
                    ),
                    "annual_rank": annual_player["rank"],
                    "results": results,
                }
            )

        period_players.sort(
            key=lambda player: (
                -player["total_points"],
                -player["tournaments"],
                player["player_name"].casefold(),
            )
        )

        for position, player in enumerate(
            period_players,
            start=1,
        ):
            player["rank"] = position

        period_tournaments = [
            tournament
            for tournament in tournaments
            if date.fromisoformat(
                tournament["tournament_date"]
            ).month in months
            and date.fromisoformat(
                tournament["tournament_date"]
            ).year == season_year
        ]

        start_month = months[0]
        end_month = months[-1]
        period_start = date(season_year, start_month, 1)
        next_month = date(
            season_year + (end_month == 12),
            end_month % 12 + 1,
            1,
        )
        period_end = next_month - timedelta(days=1)

        periods.append(
            {
                "id": period_definition["id"],
                "label": period_definition["label"],
                "date_range": (
                    f"{period_start:%d.%m.%Y}"
                    f"–{period_end:%d.%m.%Y}"
                ),
                "tournament_count": len(period_tournaments),
                "player_count": len(period_players),
                "players": period_players,
            }
        )

    return periods


def save_website_json(
    ranking: list[dict],
    tournaments: list[dict],
    season_start: date,
    display_end: date,
    ranking_periods: list[dict],
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
        "periods": ranking_periods,
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
