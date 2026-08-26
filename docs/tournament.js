"use strict";

const errorMessage = document.querySelector("#error-message");
const tournamentDetails = document.querySelector("#tournament-details");
const recordedMatches = document.querySelector("#recorded-matches");
const noRecordings = document.querySelector("#no-recordings");


function formatPoints(points) {
    return new Intl.NumberFormat(undefined, {
        maximumFractionDigits: 2,
    }).format(points);
}


function formatDate(value) {
    const parsedDate = new Date(`${value}T00:00:00`);

    if (Number.isNaN(parsedDate.getTime())) {
        return value;
    }

    return new Intl.DateTimeFormat(undefined, {
        dateStyle: "medium",
    }).format(parsedDate);
}


function formatDuration(value) {
    const seconds = Number(value);

    if (!Number.isFinite(seconds) || seconds <= 0) {
        return "Duration unavailable";
    }

    return `${Math.max(1, Math.round(seconds / 60))} min`;
}


function createRecordedMatch(match) {
    const article = document.createElement("article");
    const information = document.createElement("div");
    const meta = document.createElement("p");
    const opponent = document.createElement("a");
    const details = document.createElement("p");
    const score = document.createElement("strong");

    article.className = "recorded-match";
    information.className = "recorded-match-information";
    meta.className = "recorded-match-meta";
    meta.textContent = [
        `Table ${match.table_number}`,
        match.round ? `${match.round} #${match.match_number}` : "",
    ].filter(Boolean).join(" · ");
    opponent.className = "recorded-opponent";
    opponent.href = RankingYears.playerUrl(match.opponent_id);
    opponent.textContent = `vs ${match.opponent_name}`;
    details.className = "recorded-match-details";
    details.textContent = formatDuration(match.duration_seconds);
    score.className = "recorded-score";
    score.textContent = `${match.score_for}–${match.score_against}`;
    information.append(meta, opponent, details);
    article.append(information, score);

    if (match.video_url) {
        const watchLink = document.createElement("a");
        watchLink.className = "watch-match-link";
        watchLink.href = match.video_url;
        watchLink.target = "_blank";
        watchLink.rel = "noopener noreferrer";
        watchLink.textContent = "Watch match";
        article.append(watchLink);
    }
    return article;
}


function displayTournament(profile, result, matches) {
    document.title = `${result.tournament_name} — ${profile.player_name}`;
    document.querySelector("#tournament-name").textContent =
        result.tournament_name;
    document.querySelector("#tournament-meta").textContent = [
        profile.player_name,
        formatDate(result.tournament_date),
        result.discipline_name,
    ].filter(Boolean).join(" · ");
    document.querySelector("#player-place").textContent =
        result.place || "—";
    document.querySelector("#player-points").textContent =
        formatPoints(result.points);
    document.querySelector("#recording-total").textContent = String(
        matches.filter((match) => match.video_url).length,
    );
    document.querySelector("#matches-heading").textContent =
        `${profile.player_name}'s matches`;

    const fragment = document.createDocumentFragment();

    for (const match of matches) {
        fragment.append(createRecordedMatch(match));
    }

    recordedMatches.replaceChildren(fragment);
    noRecordings.hidden = matches.length > 0;
    document.querySelector("#standings-link").href = result.source_url;
    document.querySelector("#back-to-player").href =
        RankingYears.playerUrl(profile.player_id);
    tournamentDetails.hidden = false;
}


async function loadTournament() {
    const parameters = new URLSearchParams(window.location.search);
    const tournamentId = parameters.get("id");
    const playerId = parameters.get("player");

    if (
        !tournamentId || !/^\d+$/.test(tournamentId)
        || !playerId || !/^\d+$/.test(playerId)
    ) {
        errorMessage.textContent = "This tournament link is not valid.";
        errorMessage.hidden = false;
        return;
    }

    try {
        await RankingYears.initialize();
        const response = await fetch(
            `${RankingYears.dataRoot}/players/`
            + `${encodeURIComponent(playerId)}.json`,
            { cache: "no-cache" },
        );

        if (!response.ok) {
            throw new Error(`The server returned ${response.status}.`);
        }

        const profile = await response.json();
        const result = profile.results?.find(
            (entry) => String(entry.tournament_id) === tournamentId,
        );

        if (!result) {
            throw new Error("The tournament is not in this player profile.");
        }

        const playerMatches = Array.isArray(profile.matches)
            ? profile.matches
            : (profile.recorded_matches || []);
        const matches = playerMatches.filter(
                (match) => String(match.tournament_id) === tournamentId,
            );

        displayTournament(profile, result, matches);
    } catch (error) {
        console.error(error);
        errorMessage.textContent =
            "This tournament record could not be loaded.";
        errorMessage.hidden = false;
    }
}


loadTournament();
