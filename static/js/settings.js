document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("settings-form");
    const statusMessage = document.getElementById("status-message");
    const modeToggle = document.getElementById("color_mode");
    const modelSelectContainer = document.getElementById("model-select")?.closest(".form-group");
    const noModelsMessage = document.getElementById("no-models-message");

    function updateModelVisibility() {
        if (modeToggle.checked) {
            // API mode: hide model select and error message
            modelSelectContainer?.classList.add("d-none");
            noModelsMessage?.classList.add("d-none");
        } else {
            // LOCAL mode: show model select or error message if they exist
            modelSelectContainer?.classList.remove("d-none");
            noModelsMessage?.classList.remove("d-none");
        }
    }

    // Initial state
    updateModelVisibility();

    // Toggle listener
    modeToggle.addEventListener("change", updateModelVisibility);

    form.addEventListener("submit", function (e) {
        e.preventDefault(); // Prevent default form submission

        const formData = new FormData(form);

        // If modeToggle is NOT checked, set ai_type = LOCAL
        if (!modeToggle.checked) {
            formData.set("ai_type", "LOCAL");
        }

        const data = new URLSearchParams(formData);

        fetch("/settings", {
            method: "POST",
            body: data,
        })
            .then(response => response.json())
            .then(result => {
                statusMessage.textContent = result.message;
                statusMessage.classList.remove("text-danger");
                statusMessage.classList.add("text-success");
                statusMessage.style.display = "block";
            })
            .catch(error => {
                statusMessage.textContent = "Error saving settings.";
                statusMessage.classList.add("text-danger");
                statusMessage.style.display = "block";
                console.error("Settings save error:", error);
            });
    });
});
