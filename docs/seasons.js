"use strict";

const tableBody = document.querySelector("#ranking-body");
const searchInput = document.querySelector("#search");
const emptyMessage = document.querySelector("#empty-message");
const errorMessage = document.querySelector("#error-message");
const periodTabs = document.querySelector("#period-tabs");

let rankingData = null;
let activePeriod = null;


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


function displayPlayers() {
    const query = searchInput.value.trim().toLocaleLowerCase();
    const players = activePeriod?.players || [];
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


function selectPeriod(periodId, updateAddress = true) {
    const selectedPeriod = rankingData.periods.find(
        (period) => period.id === periodId,
    );

    if (!selectedPeriod) {
        return;
    }

    activePeriod = selectedPeriod;

    for (const tab of periodTabs.querySelectorAll("button")) {
        const isSelected = tab.dataset.period === periodId;
        tab.setAttribute("aria-selected", String(isSelected));
        tab.tabIndex = isSelected ? 0 : -1;
    }

    document.querySelector("#period-title").textContent =
        `${activePeriod.label} ranking`;
    document.querySelector("#season").textContent =
        activePeriod.date_range;
    document.querySelector("#player-count").textContent =
        String(activePeriod.player_count);
    document.querySelector("#tournament-count").textContent =
        String(activePeriod.tournament_count);
    document.title =
        `${activePeriod.label} Ranking — Złota Bila`;

    if (updateAddress) {
        const address = new URL(window.location.href);
        address.searchParams.set("period", periodId);
        window.history.replaceState({}, "", address);
    }

    displayPlayers();
}


function createPeriodTabs(periods) {
    const fragment = document.createDocumentFragment();

    for (const period of periods) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "period-tab";
        button.dataset.period = period.id;
        button.setAttribute("role", "tab");
        button.setAttribute("aria-selected", "false");
        button.textContent = period.label;
        button.addEventListener("click", () => {
            selectPeriod(period.id);
        });
        fragment.append(button);
    }

    periodTabs.replaceChildren(fragment);
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

        rankingData = await response.json();

        if (!Array.isArray(rankingData.periods)) {
            throw new Error(
                "The ranking data does not contain seasonal periods."
            );
        }

        createPeriodTabs(rankingData.periods);
        document.querySelector("#updated").textContent =
            formatUpdatedDate(rankingData.updated_at);

        const requestedPeriod = new URLSearchParams(
            window.location.search,
        ).get("period");
        const initialPeriod = rankingData.periods.some(
            (period) => period.id === requestedPeriod,
        )
            ? requestedPeriod
            : rankingData.periods[0]?.id;

        if (!initialPeriod) {
            throw new Error("No seasonal ranking periods are available.");
        }

        selectPeriod(initialPeriod, false);
    } catch (error) {
        console.error(error);
        document.querySelector("#updated").textContent =
            "Ranking unavailable";
        errorMessage.textContent =
            "The seasonal rankings could not be loaded. "
            + "Please try again later.";
        errorMessage.hidden = false;
    }
}


searchInput.addEventListener("input", displayPlayers);


periodTabs.addEventListener("keydown", (event) => {
    if (!["ArrowLeft", "ArrowRight"].includes(event.key)) {
        return;
    }

    const tabs = [...periodTabs.querySelectorAll("button")];
    const currentIndex = tabs.indexOf(document.activeElement);

    if (currentIndex === -1) {
        return;
    }

    event.preventDefault();
    const direction = event.key === "ArrowRight" ? 1 : -1;
    const nextIndex = (currentIndex + direction + tabs.length)
        % tabs.length;
    tabs[nextIndex].focus();
    selectPeriod(tabs[nextIndex].dataset.period);
});


loadRanking();
