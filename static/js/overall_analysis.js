let aiModalInstance = null;

document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.analyze-btn').forEach(button => {
        button.addEventListener('click', () => generateAnalysis(button));
    });
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

    // Construct URL with force_refresh param if needed
    let url = `/api/analysis/${type}`;
    if (forceRefresh) {
        url += '?force_refresh=true';
    }

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