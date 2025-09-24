let aiModalInstance = null;

document.addEventListener('DOMContentLoaded', async() => { 
    console.log("[DEBUG] DOM Loaded");
    document.querySelectorAll('.analyze-btn').forEach(button => {
        button.addEventListener('click', () => generateAnalysis(button));
    });
    
    document.getElementById("student-stats-table").addEventListener("click", (event) => {
        const button = event.target.closest(".analyze-btn");
        if (button) {
            generateAnalysis(button);
        }
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
    if (window.topBottomDataFromFlask) {
        renderStudentStatsTable(window.topBottomDataFromFlask);
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

    let url;
    if (type === "personalised-feedback") {
        const username = button.getAttribute("data-username");
        url = `/api/analysis/personalised-feedback/${username}?${params.toString()}`;
    } else {
        url = `/api/analysis/${type}?${params.toString()}`;
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

function renderStudentStatsTable(topBottomDataFromFlask) {
    const tableBody = document.getElementById("student-stats-table");
    if (!tableBody || !topBottomDataFromFlask) return;

    tableBody.innerHTML = "";

    const avgScoreMap = {};
    topBottomDataFromFlask.top.forEach(([username, avg]) => avgScoreMap[username] = avg);
    topBottomDataFromFlask.bottom.forEach(([username, avg]) => avgScoreMap[username] = avg);

    const topUsernames = topBottomDataFromFlask.top.map(t => t[0]);
    const bottomUsernames = topBottomDataFromFlask.bottom.map(t => t[0]);

    const topRows = topBottomDataFromFlask.top_rows || [];
    const bottomRows = topBottomDataFromFlask.bottom_rows || [];

    const rowsMap = {};
    [...topRows, ...bottomRows].forEach(r => {
        if (!rowsMap[r.username]) {
            rowsMap[r.username] = {
                username: r.username,
                completionRate: r.completion_rate,
                gamesPlayed: r.games_played,
                isTop: topUsernames.includes(r.username),
                isBottom: bottomUsernames.includes(r.username)
            };
        }
    });

    const sortedRows = Object.values(rowsMap).sort((a, b) => {
        if (a.isTop && !b.isTop) return -1;
        if (!a.isTop && b.isTop) return 1;
        if (a.isBottom && !b.isBottom) return 1;
        if (!a.isBottom && b.isBottom) return -1;
        return 0;
    });

    sortedRows.forEach((row, index) => {
        const tr = document.createElement("tr");
        tr.style.backgroundColor = row.isTop ? "#56a76aff" : row.isBottom ? "#a85158ff" : "#ffffff";

        // Add button only for bottom students, dash for top students
        let feedbackCell;
        if (row.isBottom) {
            feedbackCell = `
                <button class="btn analyze-btn" data-type="personalised-feedback" data-username="${row.username}" title="Analyze this row">
                    <svg height="24" width="24" fill="#FFFFFF" viewBox="0 0 24 24" class="sparkle">
                        <path d="M10,21.236,6.755,14.745.264,11.5,6.755,8.255,10,1.764l3.245,6.491L19.736,11.5l-6.491,3.245ZM18,21l1.5,3L21,21l3-1.5L21,18l-1.5-3L18,18l-3,1.5ZM19.333,4.667,20.5,7l1.167-2.333L24,3.5,21.667,2.333,20.5,0,19.333,2.333,17,3.5Z"></path>
                    </svg>
                    <span class="text">Generate</span>
                </button>
            `;
        } else if (row.isTop) {
            feedbackCell = "-";
        } else {
            feedbackCell = "";
        }

        tr.innerHTML = `
            <td style="padding:8px; border:1px solid #ccc; color: black;">${index + 1}</td>
            <td style="padding:8px; border:1px solid #ccc; color: black;">${row.username}</td>
            <td style="padding:8px; border:1px solid #ccc; color: black;">${avgScoreMap[row.username]?.toFixed(2) || 0}</td>
            <td style="padding:8px; border:1px solid #ccc; color: black;">${row.completionRate?.toFixed(2) || 0}</td>
            <td style="padding:8px; border:1px solid #ccc; color: black;">${row.gamesPlayed || 0}</td>
            <td style="padding:8px; border:1px solid #ccc; color: black; text-align:center;">${feedbackCell}</td>
        `;
        tableBody.appendChild(tr);
    });

}
