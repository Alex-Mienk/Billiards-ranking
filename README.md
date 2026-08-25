# Annual Player Ranking

A seasonal player ranking generated from publicly available
Tournament Service standings.

## Season dates

The current ranking season follows the calendar year, from
1 January through 31 December.

## Installation

Create and activate a Python virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Import a tournament

Import a tournament and rebuild all website rankings by providing its
Tournament Service ID and date:

```bash
python3 import_tournament.py 55931 2026-08-24
```

The scraper also reads the tournament name and discipline from the
structured Tournament Service archive entry for that month. Supported
discipline categories are combined pyramid, free pyramid with
continuation, dynamic pyramid, and multi-discipline pyramid.

The import command saves the tournament CSV and automatically rebuilds
the annual, winter, spring, summer, discipline, tournament, and player
data for the year supplied in the date.

To rebuild a year's website data without importing a tournament, run:

```bash
python3 yearly_ranking.py 2026
```

This generates the annual ranking together with winter, spring,
summer, and per-discipline rankings for the website. A discipline tab
is included only when at least one imported tournament uses it.

## Generated website data

The website uses normalized static JSON files:

- `docs/ranking.json` contains compact annual, seasonal, and discipline
  ranking summaries.
- `docs/tournaments.json` contains tournament dates, disciplines,
  player counts, names, and source links.
- `docs/players/<player_id>.json` contains one player's complete
  tournament history and ranking breakdowns.

Player names in every ranking link to the shared player profile page.
