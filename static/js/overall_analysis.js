let aiModalInstance = null;

document.addEventListener('DOMContentLoaded', () => { 
    console.log("[DEBUG] DOM Loaded");
    document.querySelectorAll('.analyze-btn').forEach(button => {
        button.addEventListener('click', () => generateAnalysis(button));
    });

    // Pre-fill month inputs from URL
    const params = new URLSearchParams(window.location.search);
    console.log("[DEBUG] URL params:", Object.fromEntries(params));

    const startInput = document.getElementById("startMonth");
    const endInput = document.getElementById("endMonth");

    if (params.get("start_month")) {
        startInput.value = params.get("start_month");
        console.log("[DEBUG] Pre-fill startMonth:", startInput.value);
    }
    if (params.get("end_month")) {
        endInput.value = params.get("end_month");
        console.log("[DEBUG] Pre-fill endMonth:", endInput.value);
    }

    // Apply Filter button
    const applyBtn = document.getElementById("applyFilterBtn");
    if (applyBtn) {
        applyBtn.addEventListener("click", (event) => {
            event.preventDefault(); 
            console.log("[DEBUG] Apply Filter button clicked");

            const startMonth = startInput.value;
            const endMonth = endInput.value;
            console.log("[DEBUG] Input values:", startMonth, endMonth);

            const newParams = new URLSearchParams();
            if (startMonth) newParams.set("start_month", startMonth);
            if (endMonth) newParams.set("end_month", endMonth);

            console.log("[DEBUG] Redirecting to URL:", `/overall?${newParams.toString()}`);
            window.location.href = `/overall?${newParams.toString()}`;
        });
    } else {
        console.log("[DEBUG] Apply Filter button NOT found!");
    }
});


document.getElementById("applyFilterBtn").addEventListener("click", () => {
    const startMonth = document.getElementById("startMonth").value; 
    const endMonth = document.getElementById("endMonth").value;     

    const params = new URLSearchParams(window.location.search);

    if (startMonth) params.set("start_month", startMonth);
    else params.delete("start_month");

    if (endMonth) params.set("end_month", endMonth);
    else params.delete("end_month");

    window.location.href = `/overall?${params.toString()}`;
});

document.getElementById('aiAnalysisModal').addEventListener('hidden.bs.modal', () => {
    aiModalInstance = null;

    // Force-remove any remaining modal backdrop and cleanup
    document.querySelectorAll('.modal-backdrop').forEach(el => el.remove());
    document.body.classList.remove('modal-open');
    document.body.style.paddingRight = '';
});

function generateAnalysis(button, forceRefresh = false) {
    const type = button.getAttribute('data-type');
    const modalBody = document.getElementById('ai-analysis-content');
    const cancelBtn = document.getElementById('btn-cancel-analysis');
    const downloadBtn = document.getElementById('btn-download-analysis');
    const regenerateBtn = document.getElementById("btn-regenerate-analysis");

    // Initial state: show cancel, hide download and regenerate
    if (cancelBtn) cancelBtn.classList.remove('d-none');
    if (downloadBtn) downloadBtn.classList.add('d-none');
    if (regenerateBtn) regenerateBtn.classList.add('d-none');

    // Set modal loading UI
    modalBody.innerHTML = `
        <div id="ai-loading" class="d-flex align-items-center justify-content-center flex-column py-4">
            <div class="spinner-border text-primary" role="status" style="width: 3rem; height: 3rem;">
            <span class="visually-hidden">Loading...</span>
            </div>
            <div class="mt-3">Analyzing ${type.replace(/-/g, ' ')}... please wait.</div>
        </div>
    `;

    // Show modal
    if (!aiModalInstance) {
        aiModalInstance = new bootstrap.Modal(document.getElementById('aiAnalysisModal'), {
            backdrop: true
        });
    }

    aiModalInstance.show();

    // Grab whatever is in the current URL (so we inherit start_month & end_month)
    const params = new URLSearchParams(window.location.search);

    // Add force_refresh flag if needed
    if (forceRefresh) {
        params.set("force_refresh", "true");
    }

    let url = `/api/analysis/${type}?${params.toString()}`;


    // Fetch analysis
    fetch(url)
        .then(res => res.json())
        .then(data => {
            cancelBtn.classList.add('d-none');  // hide cancel when complete
            let result = '';

            // API returns plaintext
            if (data.text && typeof data.text === 'string') {
                result = data.text;
                modalBody.innerHTML = `<div class="px-3 py-2">${result}</div>`;
            }
            // API returns structured insights
            else if (Array.isArray(data)) {
                result = data.map(insight =>
                    `### ${insight.title}\n\n${insight.content}\n`
                ).join('\n---\n');

                const html = data.map(insight =>
                    `<div class="mb-3"><h3><strong>${insight.title}</strong></h3><p>${insight.content.replace(/\n/g, '<br>')}</p></div><hr>`
                ).join('');
                modalBody.innerHTML = html;
            } else {
                modalBody.innerHTML = `<p>Unexpected response format.</p>`;
                return;
            }

            // Enable download
            if (result && result.trim() !== '') {
                downloadBtn.classList.remove('d-none');
                downloadBtn.onclick = () => {
                    const blob = new Blob([result], { type: 'text/plain' });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `[${type.toUpperCase()}] - AI_ANALYSIS.txt`;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    URL.revokeObjectURL(url);
                };
            }

            // Show regenerate button
            if (regenerateBtn) {
                regenerateBtn.classList.remove('d-none'); // Show regenerate button
                regenerateBtn.onclick = function () {
                    // Hide regenerate button and download button, show cancel button
                    if (downloadBtn) downloadBtn.classList.add('d-none');
                    if (regenerateBtn) regenerateBtn.classList.add('d-none');
                    if (cancelBtn) cancelBtn.classList.remove('d-none');

                    modalBody.innerHTML = `
                        <div class="d-flex align-items-center justify-content-center flex-column py-4">
                            <div class="spinner-border text-primary" role="status" style="width: 3rem; height: 3rem;">
                                <span class="visually-hidden">Loading...</span>
                            </div>
                            <div class="mt-3">Regenerating analysis... please wait.</div>
                        </div>
                    `;

                    generateAnalysis(button, true); // Call the same function to regenerate with forceRefresh flag
                };
            }
        })
        .catch(err => {
            cancelBtn.classList.add('d-none');
            modalBody.innerHTML = `
                <div class="alert alert-danger" role="alert">
                    Error: ${err.message}
                </div>
            `;
        });
}