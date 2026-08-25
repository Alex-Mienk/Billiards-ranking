"use strict";

const errorMessage = document.querySelector("#error-message");
const profileDetails = document.querySelector("#profile-details");
const historyBody = document.querySelector("#history-body");


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
        const response = await fetch(
            `./players/${encodeURIComponent(playerId)}.json`,
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
