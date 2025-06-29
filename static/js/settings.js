document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("settings-form");
    const statusMessage = document.getElementById("status-message");

    form.addEventListener("submit", function (e) {
        e.preventDefault(); // Prevent default form submission

        const formData = new FormData(form);
        const data = new URLSearchParams(formData);

        fetch("/settings", {
            method: "POST",
            body: data,
        })
            .then(response => response.json())
            .then(result => {
                statusMessage.textContent = result.message;
                statusMessage.style.display = "block";
            })
            .catch(error => {
                statusMessage.textContent = "Error saving settings.";
                statusMessage.style.color = "red";
                statusMessage.style.display = "block";
                console.error("Settings save error:", error);
            });
    });
});
