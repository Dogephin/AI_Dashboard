// === Completion Chart ===
let completionChart;

function loadCompletionData() {
    return fetch('/api/minigames/completion', { cache: 'no-store' })
        .then(r => r.json())
        .then(({ rows }) => rows || []);
}

function renderCompletionChart(rows) {
    const canvas = document.getElementById('completionChart');
    if (!canvas) return; // page safeguard

    // sort by name (stable) – flip to sort by completion_rate if you prefer
    rows = [...rows].sort((a, b) => a.Name.localeCompare(b.Name));
    const labels = rows.map(r => r.Name);
    const data = rows.map(r => r.completion_rate);

    const ctx = canvas.getContext('2d');
    if (completionChart) {
        completionChart.data.labels = labels;
        completionChart.data.datasets[0].data = data;
        completionChart.update();
        return;
    }

    completionChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels,
            datasets: [{
                label: 'Completion (%)',
                data,
                // leave default colors; Chart.js will pick; or set a single neutral color if you prefer
            }]
        },
        options: {
            indexAxis: 'y', // horizontal bars
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    title: { display: true, text: 'Completion %' },
                    min: 0, max: 100,
                    ticks: { callback: v => v + '%' }
                },
                y: {
                    title: { display: false, text: 'Minigame' }
                }
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: (ctx) => ` ${ctx.parsed.x.toFixed(1)}%`
                    }
                }
            }
        }
    });
}

function refreshCompletionChart() {
    loadCompletionData().then(renderCompletionChart).catch(err => {
        console.error('Completion load error', err);
    });
}

const btnRefreshCompletion = document.getElementById('btn-refresh-completion');
if (btnRefreshCompletion) btnRefreshCompletion.addEventListener('click', refreshCompletionChart);

// initial load
refreshCompletionChart();

const btnAiPriority = document.getElementById('btn-ai-priority');
if (btnAiPriority) {
    btnAiPriority.addEventListener('click', () => {
        // Optional: you can pass ?threshold=50 or ?top_n=5
        // Use force_refresh=false for initial load
        const baseUrl = '/api/minigames/completion/ai-priority?top_n=5&force_refresh=false';

        showAiModal('<em>Asking AI where to prioritise support…</em>');
        const modalContent = document.getElementById('aiModalBody');
        const downloadBtn = document.getElementById('btn-download-analysis');
        const cancelBtn = document.getElementById('btn-cancel-analysis');
        const regenBtn = document.getElementById('btn-regenerate-analysis');

        // initial state: show cancel while waiting, hide regenerate/download
        if (downloadBtn) downloadBtn.classList.add('d-none');
        if (regenBtn) regenBtn.classList.add('d-none');
        if (cancelBtn) cancelBtn.classList.remove('d-none');

        // Cancel closes modal
        if (cancelBtn) {
            cancelBtn.onclick = () => {
                const aiModalEl = document.getElementById('aiModal');
                const inst = bootstrap.Modal.getInstance(aiModalEl) || new bootstrap.Modal(aiModalEl);
                inst.hide();
            };
        }

        // Fetch AI priority
        fetch(baseUrl, { cache: 'no-store' })
            .then(r => r.json())
            .then(res => {
                const text = res.analysis || 'No analysis available.';
                const html = (typeof marked !== 'undefined') ? marked.parse(text) : text;
                modalContent.innerHTML = `<div class="px-2 py-1">${html}</div>`;

                // Allow download
                if (downloadBtn && text.trim()) {
                    downloadBtn.classList.remove('d-none');
                    downloadBtn.onclick = () => {
                        const blob = new Blob([text], { type: 'text/plain' });
                        const url = URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = url;
                        a.download = `AI_PRIORITY_BRIEF.txt`;
                        document.body.appendChild(a);
                        a.click();
                        document.body.removeChild(a);
                        URL.revokeObjectURL(url);
                    };
                }

                // Show regenerate button
                if (regenBtn) {
                    regenBtn.classList.remove('d-none');
                    regenBtn.onclick = function () {
                        if (downloadBtn) downloadBtn.classList.add('d-none');
                        if (regenBtn) regenBtn.classList.add('d-none');
                        if (cancelBtn) cancelBtn.classList.remove('d-none');

                        modalContent.innerHTML = `
              <div class="d-flex align-items-center justify-content-center flex-column py-4">
                <div class="spinner-border text-primary" role="status" style="width: 3rem; height: 3rem;">
                  <span class="visually-hidden">Loading...</span>
                </div>
                <div class="mt-3">Regenerating AI priority analysis... please wait.</div>
              </div>
            `;

                        // Regenerate = force_refresh=true
                        const regenUrl = '/api/minigames/completion/ai-priority?top_n=5&force_refresh=true';
                        fetch(regenUrl, { cache: 'no-store' })
                            .then(r => r.json())
                            .then(res => {
                                const text2 = res.analysis || 'No analysis available.';
                                const html2 = typeof marked !== 'undefined' ? marked.parse(text2) : text2;
                                modalContent.innerHTML = `<div class="px-2 py-1">${html2}</div>`;

                                if (downloadBtn && text2.trim()) downloadBtn.classList.remove('d-none');
                                if (regenBtn) regenBtn.classList.remove('d-none');
                                if (cancelBtn) cancelBtn.classList.add('d-none');

                                // download
                                if (downloadBtn) {
                                    downloadBtn.onclick = () => {
                                        const blob2 = new Blob([text2], { type: 'text/plain' });
                                        const url2 = URL.createObjectURL(blob2);
                                        const a2 = document.createElement('a');
                                        a2.href = url2;
                                        a2.download = `AI_PRIORITY_BRIEF.txt`;
                                        document.body.appendChild(a2);
                                        a2.click();
                                        document.body.removeChild(a2);
                                        URL.revokeObjectURL(url2);
                                    };
                                }
                            })
                            .catch(err => {
                                console.error('AI priority regenerate error', err);
                                modalContent.innerHTML = '<div class="text-danger">Failed to regenerate AI priority analysis.</div>';
                            });
                    };
                }

                // Hide cancel once content loaded
                if (cancelBtn) cancelBtn.classList.add('d-none');
            })
            .catch(err => {
                console.error('AI priority fetch error', err);
                modalContent.innerHTML = '<div class="text-danger">Failed to fetch AI priority analysis.</div>';
                if (cancelBtn) cancelBtn.classList.add('d-none');
            });
    });
}
