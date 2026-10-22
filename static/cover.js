/* A normal link remains usable with JavaScript disabled or reduced motion. */
(() => {
    const cover = document.querySelector("#welcome-cover");
    const enter = document.querySelector("#cover-enter");
    if (!cover || !enter) return;

    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
    let entering = false;
    let timer;

    function resetCover() {
        window.clearTimeout(timer);
        entering = false;
        cover.classList.remove("is-entering");
        cover.removeAttribute("aria-busy");
    }

    function finishEntrance() {
        if (!entering) return;
        // Clear first so animationend and the fallback cannot navigate twice.
        entering = false;
        window.clearTimeout(timer);
        window.location.assign(enter.href);
    }

    enter.addEventListener("click", (event) => {
        // Preserve normal new-tab/window behavior and immediate reduced-motion entry.
        if (event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
        if (entering) {
            event.preventDefault();
            return;
        }
        if (reducedMotion.matches) return;

        event.preventDefault();
        entering = true;
        cover.setAttribute("aria-busy", "true");
        cover.classList.add("is-entering");
        timer = window.setTimeout(finishEntrance, 1200);
    });

    cover.addEventListener("animationend", (event) => {
        if (event.target === cover && event.animationName === "open-cover") finishEntrance();
    });
    reducedMotion.addEventListener("change", () => {
        if (reducedMotion.matches) finishEntrance();
    });
    // Back/forward cache may restore the document in its faded-out state.
    window.addEventListener("pageshow", resetCover);
})();
