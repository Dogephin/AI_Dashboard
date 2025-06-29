document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("settings-form");
    const statusMessage = document.getElementById("status-message");
    const modeToggle = document.getElementById("color_mode");
    const modelSelectContainer = document.getElementById("model-select")?.closest(".form-group");
    const noModelsMessage = document.getElementById("no-models-message");
    const saveButton = document.getElementById("save-button");

    const hasNoModels = !!noModelsMessage;

    function updateModelVisibility() {
        if (modeToggle.checked) {
            // API mode: hide model select and error message
            modelSelectContainer?.classList.add("d-none");
            noModelsMessage?.classList.add("d-none");
            saveButton.disabled = false;
        } else {
            // LOCAL mode: show model select or error message if they exist
            // If no models, disable the save button
            modelSelectContainer?.classList.remove("d-none");
            noModelsMessage?.classList.remove("d-none");

            if (hasNoModels) {
                saveButton.disabled = true;
                alert("⚠️ No DeepSeek models found on your computer. Please install a model to proceed.");
            } else {
                saveButton.disabled = false;
            }
        }
    }

    // Initial state
    updateModelVisibility();

    // Toggle listener
    modeToggle.addEventListener("change", updateModelVisibility);

    form.addEventListener("submit", function (e) {
        e.preventDefault(); // Prevent default form submission

        if (saveButton.disabled) {
            return; // Prevent submission when button is disabled
        }

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
