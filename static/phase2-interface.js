/* Translation text comes from escaped HTML, not a second JavaScript dictionary. */
document.querySelectorAll("[data-required-message]").forEach((input) => {
    input.addEventListener("invalid", () => {
        if (input.validity.valueMissing) input.setCustomValidity(input.dataset.requiredMessage);
    });
    input.addEventListener("input", () => input.setCustomValidity(""));
    input.addEventListener("change", () => input.setCustomValidity(""));
});
