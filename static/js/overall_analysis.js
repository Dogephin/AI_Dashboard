document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.analyze-btn').forEach(button => {
        button.addEventListener('click', () => generateAnalysis(button));
    });
});

function generateAnalysis(button) {
    const type = button.getAttribute('data-type');
    const modalBody = document.getElementById('ai-analysis-content');
    const cancelBtn = document.getElementById('btn-cancel-analysis');
    const downloadBtn = document.getElementById('btn-download-analysis');

    // Initial state: show cancel, hide download
    if (cancelBtn) cancelBtn.classList.remove('d-none');
    if (downloadBtn) downloadBtn.classList.add('d-none');

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
    const modal = new bootstrap.Modal(document.getElementById('aiAnalysisModal'));
    modal.show();

    // Fetch analysis
    fetch(`/api/analysis/${type}`)
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