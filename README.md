# Annual Player Ranking

A seasonal player ranking generated from publicly available
Tournament Service standings.

## Season dates

A season starts on 1 August and ends on 31 July of the
following year.

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

Then rebuild the website ranking for the season that starts in 2026:

```bash
python3 yearly_ranking.py 2026
```
