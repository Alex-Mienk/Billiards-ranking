"use strict";

window.RankingYears = {
    year: null,
    dataRoot: null,

    withYear(path) {
        const url = new URL(path, window.location.href);
        url.searchParams.set("year", String(this.year));
        return `${url.pathname.split("/").pop()}${url.search}${url.hash}`;
    },

    playerUrl(playerId) {
        return this.withYear(
            `player.html?id=${encodeURIComponent(playerId)}`,
        );
    },

    updatePageLinks() {
        for (const link of document.querySelectorAll(
            ".navigation-menu a, .back-link",
        )) {
            link.href = this.withYear(link.getAttribute("href"));
        }
    },

    createPicker(years) {
        const label = document.createElement("label");
        const labelText = document.createElement("span");
        const select = document.createElement("select");

        label.className = "year-picker";
        labelText.textContent = "Ranking year";
        select.setAttribute("aria-label", "Choose ranking year");

        for (const entry of years) {
            const option = document.createElement("option");
            option.value = String(entry.year);
            option.textContent = String(entry.year);
            option.selected = entry.year === this.year;
            select.append(option);
        }

        select.addEventListener("change", () => {
            const url = new URL(window.location.href);
            url.searchParams.set("year", select.value);
            window.location.assign(url);
        });

        label.append(labelText, select);
        document.querySelector(".ranking-navigation-row")?.append(label);
    },

    async initialize() {
        const response = await fetch("./years.json", {
            cache: "no-cache",
        });

        if (!response.ok) {
            throw new Error(
                `The year index returned status ${response.status}.`,
            );
        }

        const manifest = await response.json();
        const years = Array.isArray(manifest.years)
            ? manifest.years
                .filter((entry) => Number.isInteger(entry.year))
                .sort((left, right) => right.year - left.year)
            : [];

        if (years.length === 0) {
            throw new Error("No ranking years are available.");
        }

        const requestedYear = Number.parseInt(
            new URLSearchParams(window.location.search).get("year"),
            10,
        );
        const selected = years.find(
            (entry) => entry.year === requestedYear,
        ) || years.find(
            (entry) => entry.year === manifest.latest_year,
        ) || years[0];

        this.year = selected.year;
        this.dataRoot = `./${selected.path}`;
        this.createPicker(years);
        this.updatePageLinks();
        return this;
    },
};
