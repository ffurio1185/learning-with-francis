const topicFilter = document.querySelector("#topic-filter");
const topicRows = document.querySelectorAll(".topic-row");
const emptyMessage = document.querySelector("#filter-empty-message");
const tableContainer = document.querySelector("#topics-table-container");

function filterTopics() {
    if (!topicFilter) {
        return;
    }

    const selectedStatus = topicFilter.value;
    let visibleCount = 0;

    topicRows.forEach((row) => {
        const savedStatus = row.dataset.learningStatus;

        if (selectedStatus === "All" || savedStatus === selectedStatus) {
            row.hidden = false;
            visibleCount++;
        } else {
            row.hidden = true;
        }
    });

    emptyMessage.hidden = visibleCount !== 0;
    tableContainer.hidden = visibleCount === 0;
}

function validateTopicSubmission(event) {
    const form = event.currentTarget;

    const statusDropdown = form.querySelector('select[name="new_status"]');
    const confirmationCheckbox = form.querySelector('input[type="checkbox"]');
    const errorMessage = form.querySelector(".confirmation-error");

    if (statusDropdown.value === "Completed" && !confirmationCheckbox.checked) {
        event.preventDefault();

        errorMessage.textContent = form.dataset.confirmationMessage;
        errorMessage.hidden = false;
        return;
    }

    errorMessage.textContent = "";
    errorMessage.hidden = true;
}

if (topicFilter) {
    topicFilter.disabled = false;
    topicFilter.addEventListener("change", filterTopics);
    filterTopics();
}

document.querySelectorAll(".status-form").forEach((form) => {
    form.addEventListener("submit", validateTopicSubmission);
});
