"use strict";

const errorMessage = document.querySelector("#error-message");
const profileDetails = document.querySelector("#profile-details");
const historyBody = document.querySelector("#history-body");
const recordedMatchesCard = document.querySelector(
    "#recorded-matches-card",
);
const recordedMatches = document.querySelector("#recorded-matches");


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


function formatUpdatedDate(value) {
    const updatedDate = new Date(value);

    if (Number.isNaN(updatedDate.getTime())) {
        return "Update time unavailable";
    }

    return `Updated ${new Intl.DateTimeFormat(undefined, {
        dateStyle: "medium",
        timeStyle: "short",
    }).format(updatedDate)}`;
}


function createBreakdownItem(item) {
    const element = document.createElement("article");
    const heading = document.createElement("h3");
    const details = document.createElement("p");
    const rank = document.createElement("strong");

    element.className = "breakdown-item";
    heading.textContent = item.label;
    details.textContent =
        `${item.tournaments} event${item.tournaments === 1 ? "" : "s"}`
        + ` · ${formatPoints(item.total_points)} points`;
    rank.textContent = `#${item.rank}`;
    rank.setAttribute("aria-label", `Rank ${item.rank}`);
    element.append(heading, details, rank);

    return element;
}


function displayBreakdowns(containerId, items) {
    const container = document.querySelector(containerId);
    const fragment = document.createDocumentFragment();

    for (const item of items) {
        fragment.append(createBreakdownItem(item));
    }

    if (items.length === 0) {
        const message = document.createElement("p");
        message.className = "breakdown-empty";
        message.textContent = "No results available.";
        fragment.append(message);
    }

    container.replaceChildren(fragment);
}


function createHistoryRow(result) {
    const row = document.createElement("tr");
    const dateCell = document.createElement("td");
    const tournamentCell = document.createElement("td");
    const tournamentLink = document.createElement("a");
    const disciplineCell = document.createElement("td");
    const placeCell = document.createElement("td");
    const pointsCell = document.createElement("td");

    dateCell.textContent = formatDate(result.tournament_date);
    tournamentLink.textContent = result.tournament_name;
    tournamentLink.className = "player-link";
    tournamentLink.href = result.source_url;
    tournamentLink.target = "_blank";
    tournamentLink.rel = "noopener noreferrer";
    tournamentCell.append(tournamentLink);
    disciplineCell.textContent = result.discipline_name || "—";
    placeCell.textContent = result.place || "—";
    placeCell.className = "number-column";
    pointsCell.textContent = formatPoints(result.points);
    pointsCell.className = "number-column points";
    row.append(
        dateCell,
        tournamentCell,
        disciplineCell,
        placeCell,
        pointsCell,
    );

    return row;
}


function formatDuration(value) {
    const minutes = Math.max(1, Math.round(Number(value) / 60));
    return `${minutes} min`;
}


function createRecordedMatch(match) {
    const article = document.createElement("article");
    const information = document.createElement("div");
    const meta = document.createElement("p");
    const opponent = document.createElement("a");
    const details = document.createElement("p");
    const score = document.createElement("strong");
    const watchLink = document.createElement("a");

    article.className = "recorded-match";
    information.className = "recorded-match-information";
    meta.className = "recorded-match-meta";
    meta.textContent = [
        formatDate(match.tournament_date),
        `Table ${match.table_number}`,
        match.round ? `${match.round} #${match.match_number}` : "",
    ].filter(Boolean).join(" · ");
    opponent.className = "recorded-opponent";
    opponent.href = RankingYears.playerUrl(match.opponent_id);
    opponent.textContent = `vs ${match.opponent_name}`;
    details.className = "recorded-match-details";
    details.textContent = [
        match.tournament_name,
        formatDuration(match.duration_seconds),
    ].filter(Boolean).join(" · ");
    score.className = "recorded-score";
    score.textContent = `${match.score_for}–${match.score_against}`;
    watchLink.className = "watch-match-link";
    watchLink.href = match.video_url;
    watchLink.target = "_blank";
    watchLink.rel = "noopener noreferrer";
    watchLink.textContent = "Watch match";
    information.append(meta, opponent, details);
    article.append(information, score, watchLink);
    return article;
}


function displayRecordedMatches(matches) {
    if (!Array.isArray(matches) || matches.length === 0) {
        recordedMatchesCard.hidden = true;
        recordedMatches.replaceChildren();
        return;
    }

    const fragment = document.createDocumentFragment();

    for (const match of matches) {
        fragment.append(createRecordedMatch(match));
    }

    recordedMatches.replaceChildren(fragment);
    recordedMatchesCard.hidden = false;
}


function displayProfile(profile) {
    document.title = `${profile.player_name} — Złota Bila`;
    document.querySelector("#player-name").textContent =
        profile.player_name;
    document.querySelector("#player-meta").textContent =
        [profile.country, `Season ${profile.season}`]
            .filter(Boolean)
            .join(" · ");
    document.querySelector("#annual-rank").textContent =
        `#${profile.annual.rank}`;
    document.querySelector("#total-points").textContent =
        formatPoints(profile.annual.total_points);
    document.querySelector("#event-count").textContent =
        String(profile.annual.tournaments);
    document.querySelector("#updated").textContent =
        formatUpdatedDate(profile.updated_at);

    displayBreakdowns("#period-breakdown", profile.periods);
    displayBreakdowns(
        "#discipline-breakdown",
        profile.disciplines,
    );
    displayRecordedMatches(profile.recorded_matches);

    const fragment = document.createDocumentFragment();

    for (const result of profile.results) {
        fragment.append(createHistoryRow(result));
    }

    historyBody.replaceChildren(fragment);
    profileDetails.hidden = false;
}


async function loadProfile() {
    const playerId = new URLSearchParams(window.location.search).get("id");

    if (!playerId || !/^\d+$/.test(playerId)) {
        errorMessage.textContent =
            "This player profile link is not valid.";
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

        if (!profile.annual || !Array.isArray(profile.results)) {
            throw new Error("The player profile is incomplete.");
        }

        displayProfile(profile);
    } catch (error) {
        console.error(error);
        errorMessage.textContent =
            "This player profile could not be loaded.";
        errorMessage.hidden = false;
    }
}


loadProfile();
