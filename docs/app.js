"use strict";

const tableBody = document.querySelector("#ranking-body");
const searchInput = document.querySelector("#search");
const emptyMessage = document.querySelector("#empty-message");
const errorMessage = document.querySelector("#error-message");

let players = [];


function createCell(text, className = "") {
    const cell = document.createElement("td");
    cell.textContent = String(text);

    if (className) {
        cell.className = className;
    }

    return cell;
}


function createRankCell(rank) {
    const cell = document.createElement("td");
    cell.className = "rank number-column";

    if (rank >= 1 && rank <= 3) {
        const medal = document.createElement("span");

        medal.className = `medal medal-${rank}`;
        medal.textContent = String(rank);
        medal.setAttribute("aria-label", `Rank ${rank}`);

        cell.append(medal);
    } else {
        cell.textContent = String(rank);
    }

    return cell;
}


function formatPoints(points) {
    return new Intl.NumberFormat(undefined, {
        maximumFractionDigits: 2,
    }).format(points);
}


function displayPlayers(searchText = "") {
    const query = searchText
        .trim()
        .toLocaleLowerCase();

    const filteredPlayers = players.filter((player) => {
        const name = String(
            player.player_name || ""
        ).toLocaleLowerCase();

        const country = String(
            player.country || ""
        ).toLocaleLowerCase();

        return name.includes(query) || country.includes(query);
    });

    const fragment = document.createDocumentFragment();

    for (const player of filteredPlayers) {
        const row = document.createElement("tr");

        row.append(
            createRankCell(player.rank),
            createCell(
                player.player_name || `Player ${player.player_id}`,
                "player",
            ),
            createCell(player.country || "—", "country"),
            createCell(
                player.tournaments,
                "number-column",
            ),
            createCell(
                formatPoints(player.total_points),
                "number-column points",
            ),
        );

        fragment.append(row);
    }

    tableBody.replaceChildren(fragment);
    emptyMessage.hidden = filteredPlayers.length !== 0;
}


function formatUpdatedDate(value) {
    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
        return "Update time unavailable";
    }

    return `Updated ${new Intl.DateTimeFormat(undefined, {
        dateStyle: "medium",
        timeStyle: "short",
    }).format(date)}`;
}


async function loadRanking() {
    errorMessage.hidden = true;

    try {
        const response = await fetch(
            "./ranking.json",
            { cache: "no-cache" },
        );

        if (!response.ok) {
            throw new Error(
                `The server returned status ${response.status}.`
            );
        }

        const ranking = await response.json();

        if (!Array.isArray(ranking.players)) {
            throw new Error(
                "The ranking data does not contain a player list."
            );
        }

        players = ranking.players;

        document.title =
            `${ranking.title || "Annual Player Ranking"} — ` +
            `${ranking.season || ""}`;

        document.querySelector("#season").textContent =
            ranking.season
                ? `Season ${ranking.season}`
                : "Current season";

        document.querySelector("#player-count").textContent =
            String(ranking.player_count ?? players.length);

        document.querySelector("#tournament-count").textContent =
            String(ranking.tournament_count ?? 0);

        document.querySelector("#updated").textContent =
            formatUpdatedDate(ranking.updated_at);

        displayPlayers(searchInput.value);
    } catch (error) {
        console.error(error);

        document.querySelector("#updated").textContent =
            "Ranking unavailable";

        errorMessage.textContent =
            "The ranking could not be loaded. Please try again later.";

        errorMessage.hidden = false;
    }
}


searchInput.addEventListener("input", (event) => {
    displayPlayers(event.target.value);
});


loadRanking();