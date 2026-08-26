# Tournament streams

Create one entry per streamed table with:

```bash
python3 stream_videos.py 55931 1 \
  "https://www.youtube.com/watch?v=VIDEO_ID" \
  --started-at "2026-08-23T10:55:00+02:00"
```

If `YOUTUBE_API_KEY` is set, `--started-at` can be omitted and the command
will read YouTube's `liveStreamingDetails.actualStartTime` value.

The generated `streams/<tournament_id>.json` file may include a
`match_overrides` object for corrections. An override can supply an exact
video offset or hide a match:

```json
{
  "match_overrides": {
    "2919078": {
      "offset_seconds": 925,
      "hidden": false
    }
  }
}
```

By default, links open 30 seconds before Tournament Service's recorded
match start. Use `--lead-in-seconds` or `--adjustment-seconds` when a
camera clock or operator timing needs calibration.
