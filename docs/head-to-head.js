"use strict";

const comparisonForm = document.querySelector("#comparison-form");
const playerOneSelect = document.querySelector("#player-one");
const playerTwoSelect = document.querySelector("#player-two");
const comparisonResults = document.querySelector("#comparison-results");
const errorMessage = document.querySelector("#error-message");

let rankingPlayers = [];


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


function createOption(player) {
    const option = document.createElement("option");
    option.value = String(player.player_id);
    option.textContent = `#${player.rank} · ${player.player_name}`;
    return option;
}


function populateSelectors() {
    for (const player of rankingPlayers) {
        playerOneSelect.append(createOption(player));
        playerTwoSelect.append(createOption(player));
    }

    const parameters = new URLSearchParams(window.location.search);
    const requestedOne = parameters.get("player1");
    const requestedTwo = parameters.get("player2");
    const availableIds = new Set(
        rankingPlayers.map((player) => String(player.player_id)),
    );

    playerOneSelect.value = availableIds.has(requestedOne)
        ? requestedOne
        : String(rankingPlayers[0]?.player_id || "");
    playerTwoSelect.value = availableIds.has(requestedTwo)
        ? requestedTwo
        : String(rankingPlayers[1]?.player_id || "");
}


async function fetchProfile(playerId) {
    const response = await fetch(
        `${RankingYears.dataRoot}/players/`
        + `${encodeURIComponent(playerId)}.json`,
        { cache: "no-cache" },
    );

    if (!response.ok) {
        throw new Error(`The player profile returned ${response.status}.`);
    }

    return response.json();
}


function getMeetings(profile, opponentId) {
    const matches = Array.isArray(profile.matches)
        ? profile.matches
        : (profile.recorded_matches || []);

    return matches
        .filter(
            (match) => String(match.opponent_id) === String(opponentId),
        )
        .sort((left, right) => (
            right.started_at.localeCompare(left.started_at)
            || right.match_id.localeCompare(left.match_id)
        ));
}


function countWins(meetings) {
    let firstPlayerWins = 0;
    let secondPlayerWins = 0;

    for (const match of meetings) {
        const scoreFor = Number(match.score_for);
        const scoreAgainst = Number(match.score_against);

        if (scoreFor > scoreAgainst) {
            firstPlayerWins += 1;
        } else if (scoreAgainst > scoreFor) {
            secondPlayerWins += 1;
        }
    }

    return { firstPlayerWins, secondPlayerWins };
}


function createAnnualCard(profile, wins, meetingCount) {
    const card = document.createElement("article");
    const heading = document.createElement("h2");
    const profileLink = document.createElement("a");
    const country = document.createElement("p");
    const statistics = document.createElement("div");
    const values = [
        ["Annual rank", `#${profile.annual.rank}`],
        ["Annual points", formatPoints(profile.annual.total_points)],
        ["Events", profile.annual.tournaments],
        ["Head-to-head wins", `${wins} / ${meetingCount}`],
    ];

    card.className = "breakdown-card comparison-player-card";
    profileLink.href = RankingYears.playerUrl(profile.player_id);
    profileLink.textContent = profile.player_name;
    heading.append(profileLink);
    country.className = "comparison-player-country";
    country.textContent = profile.country || "Country unavailable";
    statistics.className = "comparison-statistics";

    for (const [label, value] of values) {
        const statistic = document.createElement("div");
        const strong = document.createElement("strong");
        const span = document.createElement("span");
        strong.textContent = String(value);
        span.textContent = label;
        statistic.append(strong, span);
        statistics.append(statistic);
    }

    card.append(heading, country, statistics);
    return card;
}


function disciplineText(discipline) {
    if (!discipline) {
        return "Not ranked";
    }

    return `#${discipline.rank} · ${discipline.tournaments} event`
        + `${discipline.tournaments === 1 ? "" : "s"}`
        + ` · ${formatPoints(discipline.total_points)} pts`;
}


function displayDisciplines(firstProfile, secondProfile) {
    const firstDisciplines = new Map(
        firstProfile.disciplines.map((item) => [item.id, item]),
    );
    const secondDisciplines = new Map(
        secondProfile.disciplines.map((item) => [item.id, item]),
    );
    const disciplineIds = new Set([
        ...firstDisciplines.keys(),
        ...secondDisciplines.keys(),
    ]);
    const rows = [...disciplineIds]
        .map((id) => ({
            id,
            first: firstDisciplines.get(id),
            second: secondDisciplines.get(id),
        }))
        .sort((left, right) => {
            const leftLabel = left.first?.label || left.second?.label || "";
            const rightLabel = right.first?.label || right.second?.label || "";
            return leftLabel.localeCompare(rightLabel);
        });
    const fragment = document.createDocumentFragment();

    document.querySelector("#discipline-player-one").textContent =
        firstProfile.player_name;
    document.querySelector("#discipline-player-two").textContent =
        secondProfile.player_name;

    for (const item of rows) {
        const row = document.createElement("tr");
        const label = item.first?.label || item.second?.label || item.id;

        for (const text of [
            label,
            disciplineText(item.first),
            disciplineText(item.second),
        ]) {
            const cell = document.createElement("td");
            cell.textContent = text;
            row.append(cell);
        }

        fragment.append(row);
    }

    document.querySelector("#discipline-body").replaceChildren(fragment);
}


function createMeeting(match, firstProfile, secondProfile) {
    const article = document.createElement("article");
    const information = document.createElement("div");
    const meta = document.createElement("p");
    const tournamentLink = document.createElement("a");
    const details = document.createElement("p");
    const score = document.createElement("strong");

    article.className = "meeting-item";
    information.className = "meeting-information";
    meta.className = "recorded-match-meta";
    meta.textContent = [
        formatDate(match.tournament_date),
        match.round_name || match.round,
        match.table_number ? `Table ${match.table_number}` : "",
    ].filter(Boolean).join(" · ");
    tournamentLink.className = "recorded-opponent";
    tournamentLink.href = RankingYears.withYear(
        "tournament.html"
        + `?id=${encodeURIComponent(match.tournament_id)}`
        + `&player=${encodeURIComponent(firstProfile.player_id)}`,
    );
    tournamentLink.textContent = match.tournament_name;
    details.className = "recorded-match-details";
    details.textContent =
        `${firstProfile.player_name} vs ${secondProfile.player_name}`;
    score.className = "meeting-score";
    score.textContent = `${match.score_for}–${match.score_against}`;
    information.append(meta, tournamentLink, details);
    article.append(information, score);

    if (match.video_url) {
        const videoLink = document.createElement("a");
        videoLink.className = "watch-match-link";
        videoLink.href = match.video_url;
        videoLink.target = "_blank";
        videoLink.rel = "noopener noreferrer";
        videoLink.textContent = "Watch match";
        article.append(videoLink);
    }

    return article;
}


function displayMeetings(meetings, firstProfile, secondProfile, wins) {
    const fragment = document.createDocumentFragment();

    for (const meeting of meetings) {
        fragment.append(createMeeting(
            meeting,
            firstProfile,
            secondProfile,
        ));
    }

    document.querySelector("#meeting-list").replaceChildren(fragment);
    document.querySelector("#no-meetings").hidden = meetings.length > 0;
    document.querySelector("#meeting-summary").textContent = meetings.length
        ? `${meetings.length} match${meetings.length === 1 ? "" : "es"}`
            + ` · ${firstProfile.player_name} ${wins.firstPlayerWins}`
            + `–${wins.secondPlayerWins} ${secondProfile.player_name}`
        : "No direct meetings in the imported results.";
}


async function comparePlayers() {
    const firstId = playerOneSelect.value;
    const secondId = playerTwoSelect.value;

    errorMessage.hidden = true;

    if (!firstId || !secondId || firstId === secondId) {
        comparisonResults.hidden = true;
        errorMessage.textContent = "Please choose two different players.";
        errorMessage.hidden = false;
        return;
    }

    try {
        const [firstProfile, secondProfile] = await Promise.all([
            fetchProfile(firstId),
            fetchProfile(secondId),
        ]);
        const meetings = getMeetings(firstProfile, secondId);
        const wins = countWins(meetings);

        document.querySelector("#annual-comparison").replaceChildren(
            createAnnualCard(
                firstProfile,
                wins.firstPlayerWins,
                meetings.length,
            ),
            createAnnualCard(
                secondProfile,
                wins.secondPlayerWins,
                meetings.length,
            ),
        );
        displayDisciplines(firstProfile, secondProfile);
        displayMeetings(meetings, firstProfile, secondProfile, wins);
        comparisonResults.hidden = false;

        const url = new URL(window.location.href);
        url.searchParams.set("player1", firstId);
        url.searchParams.set("player2", secondId);
        window.history.replaceState(null, "", url);
        document.title =
            `${firstProfile.player_name} vs ${secondProfile.player_name}`
            + " — Złota Bila";
    } catch (error) {
        console.error(error);
        comparisonResults.hidden = true;
        errorMessage.textContent = "The comparison could not be loaded.";
        errorMessage.hidden = false;
    }
}


async function initializePage() {
    try {
        await RankingYears.initialize();
        const response = await fetch(
            `${RankingYears.dataRoot}/ranking.json`,
            { cache: "no-cache" },
        );

        if (!response.ok) {
            throw new Error(`The ranking returned ${response.status}.`);
        }

        const ranking = await response.json();
        rankingPlayers = Array.isArray(ranking.players)
            ? ranking.players
            : [];

        if (rankingPlayers.length < 2) {
            throw new Error("At least two players are required.");
        }

        document.querySelector("#season").textContent =
            `Season ${ranking.season}`;
        populateSelectors();
        await comparePlayers();
    } catch (error) {
        console.error(error);
        errorMessage.textContent =
            "Player comparison is unavailable for this year.";
        errorMessage.hidden = false;
    }
}


comparisonForm.addEventListener("submit", (event) => {
    event.preventDefault();
    comparePlayers();
});


initializePage();
