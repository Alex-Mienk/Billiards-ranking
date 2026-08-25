import argparse
import csv

from scrape_tournament import parse_date, save_results, scrape_tournament
from yearly_ranking import build_ranking


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Import one Tournament Service tournament and rebuild "
            "the website rankings."
        )
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
        print(f"Saved: {output_path}")
        print(f"Rebuilding {arguments.tournament_date.year} rankings...")
        build_ranking(arguments.tournament_date.year)
    except (OSError, csv.Error, RuntimeError) as error:
        parser.exit(1, f"Error: {error}\n")

    print("Import and website rebuild completed.")


if __name__ == "__main__":
    main()
