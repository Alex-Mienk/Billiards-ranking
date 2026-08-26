"use strict";

const menuButton = document.querySelector(".menu-button");
const navigationMenu = document.querySelector(".navigation-menu");


function closeNavigation() {
    navigationMenu.hidden = true;
    menuButton.setAttribute("aria-expanded", "false");
}


menuButton.addEventListener("click", (event) => {
    event.stopPropagation();
    const willOpen = navigationMenu.hidden;

    navigationMenu.hidden = !willOpen;
    menuButton.setAttribute("aria-expanded", String(willOpen));
});


document.addEventListener("click", (event) => {
    if (
        !navigationMenu.hidden
        && !navigationMenu.contains(event.target)
    ) {
        closeNavigation();
    }
});


document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !navigationMenu.hidden) {
        closeNavigation();
        menuButton.focus();
    }
});
