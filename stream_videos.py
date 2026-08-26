import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import requests


YOUTUBE_API_URL = "https://www.googleapis.com/youtube/v3/videos"


def parse_timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(
            f"Invalid timestamp {value!r}; use ISO 8601 with a timezone."
        ) from error

    if parsed.tzinfo is None:
        raise ValueError(
            f"Timestamp {value!r} has no timezone offset."
        )

    return parsed


def youtube_video_id(video_url: str) -> str:
    parsed = urlparse(video_url)
    hostname = parsed.hostname or ""

    if hostname in {"youtu.be", "www.youtu.be"}:
        return parsed.path.strip("/").split("/", 1)[0]

    if hostname.endswith("youtube.com"):
        query_id = parse_qs(parsed.query).get("v", [""])[0]

        if query_id:
            return query_id

        parts = [part for part in parsed.path.split("/") if part]

        if len(parts) >= 2 and parts[0] in {"live", "embed", "shorts"}:
            return parts[1]

    return ""


def fetch_youtube_start(video_url: str, api_key: str) -> str:
    video_id = youtube_video_id(video_url)

    if not video_id:
        raise RuntimeError("The supplied URL is not a recognized YouTube URL.")

    try:
        response = requests.get(
            YOUTUBE_API_URL,
            params={
                "part": "liveStreamingDetails",
                "id": video_id,
                "key": api_key,
            },
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as error:
        raise RuntimeError(
            f"Could not read the YouTube broadcast start time: {error}"
        ) from error

    items = payload.get("items", [])
    start_time = (
        items[0].get("liveStreamingDetails", {}).get("actualStartTime")
        if items
        else None
    )

    if not start_time:
        raise RuntimeError(
            "YouTube did not return an actual live-stream start time. "
            "Provide --started-at manually."
        )

    parse_timestamp(start_time)
    return start_time


def timestamped_video_url(video_url: str, offset_seconds: int) -> str:
    parsed = urlparse(video_url)
    query = parse_qs(parsed.query, keep_blank_values=True)
    query["t"] = [f"{max(0, offset_seconds)}s"]
    return urlunparse(
        parsed._replace(query=urlencode(query, doseq=True))
    )


def load_stream_config(tournament_id: str) -> dict:
    config_path = Path("streams") / f"{tournament_id}.json"

    if not config_path.exists():
        return {"tournament_id": str(tournament_id), "streams": []}

    try:
        with config_path.open(encoding="utf-8") as file:
            config = json.load(file)
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(f"Could not read {config_path}: {error}") from error

    if not isinstance(config.get("streams"), list):
        raise RuntimeError(f"{config_path} has no valid streams list.")

    return config


def save_stream(
    tournament_id: int,
    table_number: str,
    video_url: str,
    started_at: str,
    lead_in_seconds: int,
    adjustment_seconds: int,
) -> Path:
    config = load_stream_config(str(tournament_id))
    streams = {
        str(stream["table_number"]): stream
        for stream in config.get("streams", [])
        if stream.get("table_number") is not None
    }
    streams[str(table_number)] = {
        "table_number": str(table_number),
        "video_url": video_url,
        "started_at": started_at,
        "lead_in_seconds": lead_in_seconds,
        "adjustment_seconds": adjustment_seconds,
    }
    config = {
        "tournament_id": str(tournament_id),
        "streams": sorted(
            streams.values(),
            key=lambda stream: stream["table_number"],
        ),
        "match_overrides": config.get("match_overrides", {}),
    }
    output_directory = Path("streams")
    output_directory.mkdir(exist_ok=True)
    output_path = output_directory / f"{tournament_id}.json"
    temporary_path = output_path.with_suffix(".tmp")

    with temporary_path.open("w", encoding="utf-8") as file:
        json.dump(config, file, ensure_ascii=False, indent=2)

    temporary_path.replace(output_path)
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Connect one table's live-stream recording to a tournament."
    )
    parser.add_argument("tournament_id", type=int)
    parser.add_argument("table_number")
    parser.add_argument("video_url")
    parser.add_argument(
        "--started-at",
        help="Actual broadcast start in ISO 8601, including timezone.",
    )
    parser.add_argument("--lead-in-seconds", type=int, default=30)
    parser.add_argument("--adjustment-seconds", type=int, default=0)
    arguments = parser.parse_args()

    if arguments.tournament_id <= 0:
        parser.error("The tournament ID must be positive.")

    started_at = arguments.started_at

    if started_at:
        try:
            parse_timestamp(started_at)
        except ValueError as error:
            parser.error(str(error))
    else:
        api_key = os.environ.get("YOUTUBE_API_KEY", "")

        if not api_key:
            parser.error(
                "Provide --started-at, or set YOUTUBE_API_KEY so the "
                "YouTube live-stream start can be detected automatically."
            )

        try:
            started_at = fetch_youtube_start(arguments.video_url, api_key)
        except RuntimeError as error:
            parser.exit(1, f"Error: {error}\n")

    try:
        output_path = save_stream(
            tournament_id=arguments.tournament_id,
            table_number=arguments.table_number,
            video_url=arguments.video_url,
            started_at=started_at,
            lead_in_seconds=max(0, arguments.lead_in_seconds),
            adjustment_seconds=arguments.adjustment_seconds,
        )
    except (OSError, RuntimeError) as error:
        parser.exit(1, f"Error: {error}\n")

    print(f"Saved: {output_path}")


if __name__ == "__main__":
    main()
