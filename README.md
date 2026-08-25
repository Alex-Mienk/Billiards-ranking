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

## Usage

Scrape a tournament by providing its Tournament Service ID and date:

```bash
python3 scrape_tournament.py 55931 2026-08-24
```

The scraper also reads the tournament name and discipline from the
structured Tournament Service archive entry for that month. Supported
discipline categories are combined pyramid, free pyramid with
continuation, dynamic pyramid, and multi-discipline pyramid.

Then rebuild the website ranking for the season that starts in 2026:

```bash
python3 yearly_ranking.py 2026
```

This generates the annual ranking together with winter, spring,
summer, and per-discipline rankings for the website. A discipline tab
is included only when at least one imported tournament uses it.
