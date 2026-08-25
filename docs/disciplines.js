"use strict";

const tableBody = document.querySelector("#ranking-body");
const searchInput = document.querySelector("#search");
const emptyMessage = document.querySelector("#empty-message");
const errorMessage = document.querySelector("#error-message");
const disciplineTabs = document.querySelector("#discipline-tabs");
const latestPodium = document.querySelector("#latest-podium");
const podiumPlayers = document.querySelector("#podium-players");

let rankingData = null;
let activeDiscipline = null;


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


function createPlayerCell(player) {
    const cell = document.createElement("td");
    const link = document.createElement("a");

    cell.className = "player";
    link.className = "player-link";
    link.href = RankingYears.playerUrl(player.player_id);
    link.textContent =
        player.player_name || `Player ${player.player_id}`;
    cell.append(link);

    return cell;
}


function formatPoints(points) {
    return new Intl.NumberFormat(undefined, {
        maximumFractionDigits: 2,
    }).format(points);
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


function formatTournamentDate(value) {
    const tournamentDate = new Date(`${value}T00:00:00`);

    if (Number.isNaN(tournamentDate.getTime())) {
        return value;
    }

    return new Intl.DateTimeFormat(undefined, {
        dateStyle: "long",
    }).format(tournamentDate);
}


function displayLatestPodium() {
    const tournament = activeDiscipline?.latest_tournament;
    const players = tournament?.podium;

    if (!tournament || !Array.isArray(players) || players.length === 0) {
        latestPodium.hidden = true;
        podiumPlayers.replaceChildren();
        return;
    }

    const fragment = document.createDocumentFragment();

    for (const player of players) {
        const placeNumber = Number.parseInt(player.place, 10);
        const card = document.createElement("article");
        const place = document.createElement("span");
        const link = document.createElement("a");
        const country = document.createElement("span");

        card.className = `podium-player podium-place-${placeNumber}`;
        place.className = "podium-place";
        place.textContent = placeNumber === 3 ? "3–4" : String(placeNumber);
        link.className = "podium-player-link";
        link.href = RankingYears.playerUrl(player.player_id);
        link.textContent = player.player_name;
        country.className = "podium-country";
        country.textContent = player.country || "—";
        card.append(place, link, country);
        fragment.append(card);
    }

    podiumPlayers.replaceChildren(fragment);
    document.querySelector("#latest-podium-title").textContent =
        tournament.tournament_name;
    document.querySelector("#latest-tournament-date").textContent =
        formatTournamentDate(tournament.tournament_date);

    const tournamentLink = document.querySelector(
        "#latest-tournament-link",
    );
    tournamentLink.href = tournament.source_url;
    latestPodium.hidden = false;
}


function displayPlayers() {
    const query = searchInput.value.trim().toLocaleLowerCase();
    const players = activeDiscipline?.players || [];
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
            createPlayerCell(player),
            createCell(player.country || "—", "country"),
            createCell(player.tournaments, "number-column"),
            createCell(
                formatPoints(player.total_points),
                "number-column points",
            ),
            createCell(
                player.annual_rank,
                "number-column annual-rank-column annual-rank",
            ),
        );
        fragment.append(row);
    }

    tableBody.replaceChildren(fragment);
    emptyMessage.hidden = filteredPlayers.length !== 0;
}


function selectDiscipline(disciplineId) {
    const selectedDiscipline = rankingData.disciplines.find(
        (discipline) => discipline.id === disciplineId,
    );

    if (!selectedDiscipline) {
        return;
    }

    activeDiscipline = selectedDiscipline;

    for (const tab of disciplineTabs.querySelectorAll("button")) {
        const isSelected = tab.dataset.discipline === disciplineId;
        tab.setAttribute("aria-selected", String(isSelected));
        tab.tabIndex = isSelected ? 0 : -1;
    }

    document.querySelector("#discipline-title").textContent =
        `${activeDiscipline.label} ranking`;
    document.querySelector("#season").textContent =
        rankingData.season
            ? `Season ${rankingData.season}`
            : activeDiscipline.label;
    document.querySelector("#player-count").textContent =
        String(activeDiscipline.player_count);
    document.querySelector("#tournament-count").textContent =
        String(activeDiscipline.tournament_count);
    document.title =
        `${activeDiscipline.label} Ranking — Złota Bila`;

    displayLatestPodium();
    displayPlayers();
}


function createDisciplineTabs(disciplines) {
    const fragment = document.createDocumentFragment();

    for (const discipline of disciplines) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "period-tab";
        button.dataset.discipline = discipline.id;
        button.setAttribute("role", "tab");
        button.setAttribute("aria-selected", "false");
        button.textContent = discipline.label;
        button.addEventListener("click", () => {
            selectDiscipline(discipline.id);
        });
        fragment.append(button);
    }

    disciplineTabs.replaceChildren(fragment);
}


async function loadRanking() {
    errorMessage.hidden = true;

    try {
        await RankingYears.initialize();
        const response = await fetch(
            `${RankingYears.dataRoot}/ranking.json`,
            { cache: "no-cache" },
        );

        if (!response.ok) {
            throw new Error(
                `The server returned status ${response.status}.`
            );
        }

        rankingData = await response.json();

        if (!Array.isArray(rankingData.disciplines)) {
            throw new Error(
                "The ranking data does not contain disciplines."
            );
        }

        if (rankingData.disciplines.length === 0) {
            throw new Error(
                "No imported tournaments have discipline metadata."
            );
        }

        createDisciplineTabs(rankingData.disciplines);
        document.querySelector("#updated").textContent =
            formatUpdatedDate(rankingData.updated_at);
        selectDiscipline(rankingData.disciplines[0].id);
    } catch (error) {
        console.error(error);
        document.querySelector("#updated").textContent =
            "Ranking unavailable";
        errorMessage.textContent =
            "The discipline rankings could not be loaded. "
            + "Please try again later.";
        errorMessage.hidden = false;
    }
}


searchInput.addEventListener("input", displayPlayers);


disciplineTabs.addEventListener("keydown", (event) => {
    if (!["ArrowLeft", "ArrowRight"].includes(event.key)) {
        return;
    }

    const tabs = [...disciplineTabs.querySelectorAll("button")];
    const currentIndex = tabs.indexOf(document.activeElement);

    if (currentIndex === -1) {
        return;
    }

    event.preventDefault();
    const direction = event.key === "ArrowRight" ? 1 : -1;
    const nextIndex = (currentIndex + direction + tabs.length)
        % tabs.length;
    tabs[nextIndex].focus();
    selectDiscipline(tabs[nextIndex].dataset.discipline);
});


loadRanking();
