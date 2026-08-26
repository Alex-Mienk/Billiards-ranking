import argparse
import csv
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from stream_videos import (
    load_stream_config,
    parse_timestamp,
    timestamped_video_url,
)


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
    10481: {
        "player_name": "Babliuk Yevhenii",
        "country": "UKR",
    },
    17811: {
        "player_name": "Dementii Danylo",
        "country": "POL",
    },
    33264: {
        "player_name": "Bilyi Lyubomir",
        "country": "UKR",
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
        "player_name": "Oleksii Miienko",
        "country": "UKR",
    },
    53732: {
        "player_name": "Kondratiuk Alexandr",
        "country": "POL",
    },
    87671: {
        "player_name": "Skukis Volodymyr",
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
    89467: {
        "player_name": "Didenko Genadii",
        "country": "POL",
    },
    91311: {
        "player_name": "Mishchenko Adrian",
        "country": "UKR",
    },
    94439: {
        "player_name": "Dmytriuk Andrii",
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
    100954: {
        "player_name": "Rodionov Vladislav",
        "country": "TBA",
    },
}

# Tournament Service contains a mixture of Latin, Ukrainian, Russian,
# and Belarusian player registrations. Keep a player's existing Latin
# registration; transliterate Cyrillic-only registrations consistently for
# the English-language website.
CYRILLIC_TO_LATIN = str.maketrans(
    {
        "А": "A", "а": "a", "Б": "B", "б": "b",
        "В": "V", "в": "v", "Г": "G", "г": "g",
        "Ґ": "G", "ґ": "g", "Д": "D", "д": "d",
        "Е": "E", "е": "e", "Ё": "Yo", "ё": "yo",
        "Є": "Ye", "є": "ye", "Ж": "Zh", "ж": "zh",
        "З": "Z", "з": "z", "И": "I", "и": "i",
        "І": "I", "і": "i", "Ї": "Yi", "ї": "yi",
        "Й": "I", "й": "i", "К": "K", "к": "k",
        "Л": "L", "л": "l", "М": "M", "м": "m",
        "Н": "N", "н": "n", "О": "O", "о": "o",
        "П": "P", "п": "p", "Р": "R", "р": "r",
        "С": "S", "с": "s", "Т": "T", "т": "t",
        "У": "U", "у": "u", "Ў": "U", "ў": "u",
        "Ф": "F", "ф": "f", "Х": "Kh", "х": "kh",
        "Ц": "Ts", "ц": "ts", "Ч": "Ch", "ч": "ch",
        "Ш": "Sh", "ш": "sh", "Щ": "Shch", "щ": "shch",
        "Ъ": "", "ъ": "", "Ы": "Y", "ы": "y",
        "Ь": "", "ь": "", "Э": "E", "э": "e",
        "Ю": "Yu", "ю": "yu", "Я": "Ya", "я": "ya",
    }
)


def standardize_player_name(value: str) -> str:
    """Return a stable Latin-script display name."""
    return " ".join(value.translate(CYRILLIC_TO_LATIN).split())

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

DISCIPLINE_NAMES = {
    "combined": "Combined pyramid",
    "continuation": "Free pyramid with continuation",
    "dynamic": "Dynamic pyramid",
    "multi": "Multi-discipline pyramid",
}


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

        tournament_name = (
            first_row.get("tournament_name")
            or f"Tournament {tournament_id}"
        )
        discipline = first_row.get("discipline", "")
        discipline_name = first_row.get("discipline_name", "")

        # The ID is the unique key, so the same tournament cannot be
        # counted twice.
        included_tournaments[str(tournament_id)] = {
            "tournament_id": str(tournament_id),
            "tournament_name": tournament_name,
            "tournament_date": tournament_date.isoformat(),
            "discipline": discipline,
            "discipline_name": discipline_name,
            "source_url": first_row.get("source_url", ""),
            "player_count": 0,
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
                    "discipline": discipline,
                    "discipline_name": discipline_name,
                    "place": row.get("place", ""),
                    "points": round(points, 2),
                    "source_url": row.get("source_url", ""),
                }
            )

        included_tournaments[str(tournament_id)]["player_count"] = len(
            seen_players_in_file
        )

    for player in players.values():
        player["player_name"] = standardize_player_name(
            player["player_name"]
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

    annotate_rank_movement(
        ranking=ranking,
        tournaments=list(included_tournaments.values()),
    )

    attach_player_matches(
        ranking=ranking,
        tournaments=list(included_tournaments.values()),
        season_year=season_year,
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
        discipline_rankings=build_discipline_rankings(
            ranking=ranking,
            tournaments=list(included_tournaments.values()),
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
    print(
        "Saved website data: "
        f"docs/data/{season_year}/ranking.json"
    )


def attach_player_matches(
    ranking: list[dict],
    tournaments: list[dict],
    season_year: int,
) -> None:
    players_by_id = {
        player["player_id"]: player
        for player in ranking
    }
    tournaments_by_id = {
        tournament["tournament_id"]: tournament
        for tournament in tournaments
    }
    stream_configs = {}

    for player in ranking:
        player["matches"] = []

    for matches_path in sorted(
        (Path("data") / str(season_year)).glob("matches_*.csv")
    ):
        rows = read_tournament_file(matches_path)

        for row in rows:
            tournament_id = row.get("tournament_id", "")
            tournament = tournaments_by_id.get(tournament_id)

            if tournament is None:
                continue

            if tournament_id not in stream_configs:
                stream_configs[tournament_id] = load_stream_config(
                    tournament_id
                )

            config = stream_configs[tournament_id]
            streams_by_table = {
                str(stream.get("table_number", "")): stream
                for stream in config.get("streams", [])
            }
            match_id = row.get("match_id", "")
            override = config.get("match_overrides", {}).get(
                match_id,
                {},
            )

            table_number = str(
                override.get(
                    "table_number",
                    row.get("table_number", ""),
                )
            )
            stream = streams_by_table.get(table_number)

            try:
                raw_player_a_id = int(row["player_a_id"])
                raw_player_b_id = int(row["player_b_id"])
            except (KeyError, ValueError):
                continue

            player_a_id = PLAYER_ID_ALIASES.get(
                raw_player_a_id,
                raw_player_a_id,
            )
            player_b_id = PLAYER_ID_ALIASES.get(
                raw_player_b_id,
                raw_player_b_id,
            )
            player_a = players_by_id.get(player_a_id)
            player_b = players_by_id.get(player_b_id)

            if player_a is None or player_b is None:
                continue

            match_start = None
            match_end = None

            try:
                match_start = parse_timestamp(row["started_at"])
                match_end = parse_timestamp(row["ended_at"])
            except (KeyError, ValueError):
                pass

            video_url = ""
            offset_seconds = None

            if override.get("video_url") and not override.get("hidden"):
                video_url = str(override["video_url"])
            elif stream is not None and not override.get("hidden"):
                try:
                    stream_start = parse_timestamp(stream["started_at"])

                    if match_start is None:
                        raise ValueError("Match start time is unavailable.")

                    if "offset_seconds" in override:
                        offset_seconds = int(override["offset_seconds"])
                    else:
                        offset_seconds = round(
                            (match_start - stream_start).total_seconds()
                        )
                        offset_seconds += int(
                            stream.get("adjustment_seconds", 0)
                        )
                        offset_seconds -= int(
                            stream.get("lead_in_seconds", 30)
                        )

                    offset_seconds = max(0, offset_seconds)
                    video_url = timestamped_video_url(
                        stream["video_url"],
                        offset_seconds,
                    )
                except (KeyError, TypeError, ValueError):
                    print(
                        f"Warning: no video link created for match "
                        f"{match_id} in {matches_path}; its timing "
                        "or stream configuration is invalid."
                    )

            common = {
                "match_id": match_id,
                "tournament_id": tournament_id,
                "tournament_name": tournament["tournament_name"],
                "tournament_date": tournament["tournament_date"],
                "round": row.get("round", ""),
                "round_name": row.get("round_name", ""),
                "match_number": row.get("match_number", ""),
                "table_number": table_number,
                "started_at": row.get("started_at", ""),
                "ended_at": row.get("ended_at", ""),
                "duration_seconds": (
                    max(
                        0,
                        round((match_end - match_start).total_seconds()),
                    )
                    if match_start is not None and match_end is not None
                    else None
                ),
                "video_url": video_url,
                "video_offset_seconds": offset_seconds,
            }
            player_a["matches"].append(
                {
                    **common,
                    "opponent_id": player_b_id,
                    "opponent_name": player_b["player_name"],
                    "score_for": row.get("player_a_score", ""),
                    "score_against": row.get("player_b_score", ""),
                }
            )
            player_b["matches"].append(
                {
                    **common,
                    "opponent_id": player_a_id,
                    "opponent_name": player_a["player_name"],
                    "score_for": row.get("player_b_score", ""),
                    "score_against": row.get("player_a_score", ""),
                }
            )

    for player in ranking:
        player["matches"].sort(
            key=lambda match: (
                match["started_at"],
                match["match_id"],
            ),
            reverse=True,
        )


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
            lineterminator="\n",
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


def build_discipline_rankings(
    ranking: list[dict],
    tournaments: list[dict],
) -> list[dict]:
    disciplines = []

    for discipline_id, discipline_label in DISCIPLINE_NAMES.items():
        discipline_tournaments = [
            tournament
            for tournament in tournaments
            if tournament.get("discipline") == discipline_id
        ]

        # Do not create an empty tab for a discipline that has not
        # occurred in the imported tournament files.
        if not discipline_tournaments:
            continue

        discipline_players = []

        for annual_player in ranking:
            results = [
                result
                for result in annual_player["results"]
                if result.get("discipline") == discipline_id
            ]

            if not results:
                continue

            discipline_players.append(
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
                }
            )

        discipline_players.sort(
            key=lambda player: (
                -player["total_points"],
                -player["tournaments"],
                player["player_name"].casefold(),
            )
        )

        for position, player in enumerate(
            discipline_players,
            start=1,
        ):
            player["rank"] = position

        latest_tournament = max(
            discipline_tournaments,
            key=lambda tournament: tournament["tournament_date"],
        )
        podium = []

        for annual_player in ranking:
            latest_result = next(
                (
                    result
                    for result in annual_player["results"]
                    if result["tournament_id"]
                    == latest_tournament["tournament_id"]
                ),
                None,
            )

            if latest_result is None:
                continue

            place = latest_result.get("place", "").replace("–", "-")

            try:
                podium_place = int(place.split("-", 1)[0])
            except ValueError:
                continue

            if podium_place > 3:
                continue

            podium.append(
                {
                    "place": place,
                    "player_id": annual_player["player_id"],
                    "player_name": annual_player["player_name"],
                    "country": annual_player["country"],
                }
            )

        podium.sort(
            key=lambda player: (
                int(player["place"].split("-", 1)[0]),
                player["player_name"].casefold(),
            )
        )

        disciplines.append(
            {
                "id": discipline_id,
                "label": discipline_label,
                "tournament_count": len(discipline_tournaments),
                "player_count": len(discipline_players),
                "latest_tournament": {
                    "tournament_id": latest_tournament["tournament_id"],
                    "tournament_name": latest_tournament["tournament_name"],
                    "tournament_date": latest_tournament["tournament_date"],
                    "source_url": latest_tournament["source_url"],
                    "podium": podium,
                },
                "players": discipline_players,
            }
        )

    return disciplines


def annotate_rank_movement(
    ranking: list[dict],
    tournaments: list[dict],
) -> None:
    """Compare current ranks with standings before the latest event."""
    if not tournaments:
        return

    latest_tournament = max(
        tournaments,
        key=lambda tournament: (
            tournament["tournament_date"],
            str(tournament["tournament_id"]),
        ),
    )
    latest_id = str(latest_tournament["tournament_id"])
    previous_players = []

    for player in ranking:
        earlier_results = [
            result
            for result in player["results"]
            if str(result["tournament_id"]) != latest_id
        ]

        if earlier_results:
            previous_players.append(
                {
                    "player_id": player["player_id"],
                    "player_name": player["player_name"],
                    "tournaments": len(earlier_results),
                    "total_points": round(
                        sum(result["points"] for result in earlier_results),
                        2,
                    ),
                }
            )

    previous_players.sort(
        key=lambda player: (
            -player["total_points"],
            -player["tournaments"],
            player["player_name"].casefold(),
        )
    )
    previous_ranks = {
        player["player_id"]: position
        for position, player in enumerate(previous_players, start=1)
    }

    for player in ranking:
        previous_rank = previous_ranks.get(player["player_id"])
        player["previous_rank"] = previous_rank
        player["rank_change"] = (
            previous_rank - player["rank"]
            if previous_rank is not None
            else 0
        )


def ranking_player_summary(player: dict) -> dict:
    return {
        key: player[key]
        for key in (
            "rank",
            "player_id",
            "player_name",
            "country",
            "tournaments",
            "total_points",
            "previous_rank",
            "rank_change",
        )
    }


def write_json_atomic(output_path: Path, data) -> None:
    temporary_path = output_path.with_suffix(".tmp")

    with temporary_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2,
        )

    temporary_path.replace(output_path)


def save_player_profiles(
    ranking: list[dict],
    ranking_periods: list[dict],
    discipline_rankings: list[dict],
    season_year: int,
    season: str,
    updated_at: str,
    website_directory: Path,
) -> None:
    players_directory = website_directory / "players"
    players_directory.mkdir(exist_ok=True)

    # A player can appear in more than one period, so build the lookup
    # as lists instead of allowing later entries to replace earlier ones.
    periods_by_player = {}

    for period in ranking_periods:
        for player in period["players"]:
            periods_by_player.setdefault(
                player["player_id"],
                [],
            ).append(
                {
                    "id": period["id"],
                    "label": period["label"],
                    "date_range": period["date_range"],
                    "rank": player["rank"],
                    "tournaments": player["tournaments"],
                    "total_points": player["total_points"],
                }
            )

    disciplines_by_player = {}

    for discipline in discipline_rankings:
        for player in discipline["players"]:
            disciplines_by_player.setdefault(
                player["player_id"],
                [],
            ).append(
                {
                    "id": discipline["id"],
                    "label": discipline["label"],
                    "rank": player["rank"],
                    "tournaments": player["tournaments"],
                    "total_points": player["total_points"],
                }
            )

    for player in ranking:
        player_id = player["player_id"]
        profile = {
            "player_id": player_id,
            "player_name": player["player_name"],
            "country": player["country"],
            "year": season_year,
            "season": season,
            "updated_at": updated_at,
            "annual": {
                "rank": player["rank"],
                "tournaments": player["tournaments"],
                "total_points": player["total_points"],
            },
            "periods": periods_by_player.get(player_id, []),
            "disciplines": disciplines_by_player.get(player_id, []),
            "results": player["results"],
            "matches": player.get("matches", []),
        }
        write_json_atomic(
            players_directory / f"{player_id}.json",
            profile,
        )


def save_website_json(
    ranking: list[dict],
    tournaments: list[dict],
    season_start: date,
    display_end: date,
    ranking_periods: list[dict],
    discipline_rankings: list[dict],
) -> None:
    website_directory = Path("docs")
    website_directory.mkdir(exist_ok=True)
    season_year = season_start.year
    archive_directory = (
        website_directory / "data" / str(season_year)
    )
    archive_directory.mkdir(parents=True, exist_ok=True)

    tournaments.sort(
        key=lambda tournament: (
            tournament["tournament_date"],
            tournament["tournament_name"].casefold(),
        ),
        reverse=True,
    )

    season = (
        f"{season_start:%d.%m.%Y}"
        f"–{display_end:%d.%m.%Y}"
    )
    updated_at = datetime.now(timezone.utc).isoformat()

    website_data = {
        "title": "Annual Player Ranking",
        "year": season_year,
        "season": season,
        "season_start": season_start.isoformat(),
        "season_end": display_end.isoformat(),
        "updated_at": updated_at,
        "tournament_count": len(tournaments),
        "player_count": len(ranking),
        "players": [
            ranking_player_summary(player)
            for player in ranking
        ],
        "periods": ranking_periods,
        "disciplines": discipline_rankings,
    }

    tournament_data = {
        "year": season_year,
        "season": season,
        "updated_at": updated_at,
        "tournament_count": len(tournaments),
        "tournaments": tournaments,
    }

    write_json_atomic(archive_directory / "ranking.json", website_data)
    write_json_atomic(
        archive_directory / "tournaments.json",
        tournament_data,
    )
    save_player_profiles(
        ranking=ranking,
        ranking_periods=ranking_periods,
        discipline_rankings=discipline_rankings,
        season_year=season_year,
        season=season,
        updated_at=updated_at,
        website_directory=archive_directory,
    )

    manifest_path = website_directory / "years.json"

    try:
        with manifest_path.open(encoding="utf-8") as file:
            manifest = json.load(file)
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        manifest = {"years": []}

    years_by_number = {
        int(entry["year"]): entry
        for entry in manifest.get("years", [])
        if isinstance(entry, dict)
        and str(entry.get("year", "")).isdigit()
    }
    years_by_number[season_year] = {
        "year": season_year,
        "season": season,
        "path": f"data/{season_year}",
    }
    available_years = sorted(years_by_number, reverse=True)
    manifest = {
        "latest_year": available_years[0],
        "years": [
            years_by_number[year]
            for year in available_years
        ],
    }
    write_json_atomic(manifest_path, manifest)

    # Keep the original root-level files as aliases for integrations that
    # still expect them. Rebuilding an older year cannot replace the newest
    # aliases or any archived year.
    if season_year == manifest["latest_year"]:
        write_json_atomic(
            website_directory / "ranking.json",
            website_data,
        )
        write_json_atomic(
            website_directory / "tournaments.json",
            tournament_data,
        )
        save_player_profiles(
            ranking=ranking,
            ranking_periods=ranking_periods,
            discipline_rankings=discipline_rankings,
            season_year=season_year,
            season=season,
            updated_at=updated_at,
            website_directory=website_directory,
        )


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
