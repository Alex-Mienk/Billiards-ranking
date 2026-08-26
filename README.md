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

Player display names are standardized in Latin script during the rebuild.
An existing Latin Tournament Service registration is preserved; a
Cyrillic-only registration is transliterated consistently. Explicit merged
player profiles take precedence over both forms.

To rebuild a year's website data without importing a tournament, run:

```bash
python3 yearly_ranking.py 2026
```

This generates the annual ranking together with winter, spring,
summer, and per-discipline rankings for the website. A discipline tab
is included only when at least one imported tournament uses it.

## Generated website data

Each calendar year has its own permanent data directory:

- `docs/years.json` lists the available ranking years and identifies the
  newest year.
- `docs/data/<year>/ranking.json` contains annual, seasonal, and
  discipline ranking summaries for that year.
- `docs/data/<year>/tournaments.json` contains that year's tournament
  dates, disciplines, player counts, names, and source links.
- `docs/data/<year>/players/<player_id>.json` contains one player's
  history and ranking breakdowns for that year.

The website displays a year selector and defaults to the newest generated
year. Importing the first 2027 tournament will add `docs/data/2027`
without replacing `docs/data/2026`. Player links retain the selected year.

The root-level JSON files remain aliases for the newest year for backward
compatibility, but the website reads from the year-specific directories.

## Recorded match videos

Tournament imports also save every completed match to
`data/<year>/matches_<tournament_id>.csv`. Tournament Service supplies the
players, score, actual start and end timestamps, and table assignment.

Connect a table's recording by supplying its URL and actual broadcast
start time:

```bash
python3 stream_videos.py 55931 1 \
  "https://www.youtube.com/watch?v=VIDEO_ID" \
  --started-at "2026-08-23T10:55:00+02:00"
python3 yearly_ranking.py 2026
```

The rebuild calculates every match's position in the long recording and
adds a timestamped **Watch match** link to both players' profiles. Links
start 30 seconds early by default. See `streams/README.md` for timing
adjustments and individual match overrides.

For YouTube live-stream recordings, `--started-at` can be detected from
YouTube's `liveStreamingDetails.actualStartTime` when an API key is
available:

```bash
export YOUTUBE_API_KEY="your-key"
python3 stream_videos.py 55931 1 \
  "https://www.youtube.com/watch?v=VIDEO_ID"
```

The API key is used only while creating the stream configuration and must
not be committed to the repository.

## Rebuild on GitHub

After committing a website feature, open the repository's **Actions**
tab, select **Rebuild website**, and choose **Run workflow**. Confirm the
ranking year and start the workflow. It regenerates the website data from
the existing tournament CSV files, commits any generated changes, and
deploys the `docs` directory to GitHub Pages.
