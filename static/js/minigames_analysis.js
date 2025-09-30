document.addEventListener('DOMContentLoaded', () => {
    const grid = document.getElementById('gamesGrid');
    const searchInput = document.getElementById('gameSearchInput');
    const sortSelect = document.getElementById('sortSelect');
    const form = document.getElementById('filterForm');

    let currentSearchQuery = '';
    let currentSort = '';
    let currentFilters = {};
    const sliderConfigs = {
        total_attempts: [0, 500],
        completion_rate: [0, 100],
        average_score: [0, 500],
        failed: [0, 300]
    };
    const sliders = {};

    fetch('/api/minigames')
        .then(r => r.json())
        .then(games => Promise.all(
            games.map(game =>
                fetch(`/api/minigames/${game.Level_ID}/stats`)
                    .then(r => r.json())
                    .then(stats => {
                        game.stats = stats; // Store full stats
                        return game;
                    })
                    .catch(err => {
                        console.error(`Stats failed for Game ID ${game.Level_ID}`, err);
                        return game;
                    })
            )
        ))
        .then(gamesWithStats => {
            grid.innerHTML = '';
            window._allGames = gamesWithStats;

            renderGames();

            setupFilterForm(gamesWithStats);
            setupSearch();
            setupSort();
        })
        .catch(err => {
            console.error('Failed to load mini-games:', err);
            grid.innerHTML = '<p class="text-danger">Could not load mini-games.</p>';
        });

    function createCard(game) {
        const card = document.createElement('div');
        card.className = 'game-card';
        card.innerHTML = `
            <h2 class="text-lg font-semibold mb-1" style="color: #000;">${game.Name}</h2>
            <p class="text-sm text-gray-600 mb-2">Game ID ${game.Game_ID}</p>
            <button class="btn btn-primary btn-sm" data-game-id="${game.Level_ID}">View Stats</button>
            <div class="details mt-3" id="details-${game.Level_ID}" style="display:none;"></div>
            <button class="btn btn-outline-secondary btn-sm ai-summary-btn" data-game-id="${game.Level_ID}">
                View AI Summary
            </button>
        `;
        card.querySelector('button').addEventListener('click', () =>
            toggleDetails(game.Level_ID)
        );
        setTimeout(() => attachAiButton(game.Level_ID), 0);
        return card;
    }

    function renderGames() {
        let filtered = [...window._allGames];

        // Apply filters
        for (const key in currentFilters) {
            const { min, max } = currentFilters[key];
            filtered = filtered.filter(g => {
                const val = g.stats?.summary?.[key];
                return val !== undefined && val >= min && val <= max;
            });
        }

        // Apply search
        if (currentSearchQuery) {
            filtered = filtered.filter(g =>
                g.Name.toLowerCase().includes(currentSearchQuery)
            );
        }

        // Apply sort
        if (currentSort === 'name_asc') {
            filtered.sort((a, b) => a.Name.localeCompare(b.Name));
        } else if (currentSort === 'name_desc') {
            filtered.sort((a, b) => b.Name.localeCompare(a.Name));
        } else if (currentSort === 'score_asc') {
            filtered.sort((a, b) => (a.stats?.summary?.average_score || 0) - (b.stats?.summary?.average_score || 0));
        } else if (currentSort === 'score_desc') {
            filtered.sort((a, b) => (b.stats?.summary?.average_score || 0) - (a.stats?.summary?.average_score || 0));
        }

        grid.innerHTML = '';
        filtered.forEach(g => grid.appendChild(createCard(g)));
    }

    function setupSearch() {
        if (searchInput) {
            searchInput.addEventListener('input', () => {
                currentSearchQuery = searchInput.value.toLowerCase().trim();
                renderGames();
            });
        }
    }

    function setupSort() {
        if (sortSelect) {
            sortSelect.addEventListener('change', () => {
                currentSort = sortSelect.value;
                renderGames();
            });
        }
    }

    function setupFilterForm(games) {
        if (!form) return;

        Object.keys(sliderConfigs).forEach(key => {
            const [min, max] = sliderConfigs[key];
            const sliderInput = $(`#range_${key}`);
            const minInput = document.getElementById(`input_min_${key}`);
            const maxInput = document.getElementById(`input_max_${key}`);

            sliders[key] = sliderInput.ionRangeSlider({
                type: 'double',
                min,
                max,
                from: min,
                to: max,
                grid: true,
                keyboard: true,
                disable: true,
                prettify_enabled: false,
                onChange: data => {
                    minInput.value = data.from;
                    maxInput.value = data.to;
                }
            }).data('ionRangeSlider');

            minInput.addEventListener('input', () => {
                if (!sliders[key].options.disable) {
                    const newMin = parseInt(minInput.value) || min;
                    sliders[key].update({ from: Math.min(newMin, sliders[key].result.to) });
                }
            });

            maxInput.addEventListener('input', () => {
                if (!sliders[key].options.disable) {
                    const newMax = parseInt(maxInput.value) || max;
                    sliders[key].update({ to: Math.max(newMax, sliders[key].result.from) });
                }
            });
        });

        form.querySelectorAll('input[type="checkbox"][name="filterTypes"]').forEach(cb => {
            cb.addEventListener('change', () => {
                const key = cb.value;
                const minInput = document.getElementById(`input_min_${key}`);
                const maxInput = document.getElementById(`input_max_${key}`);

                if (cb.checked) {
                    sliders[key].update({ disable: false });
                    minInput.disabled = false;
                    maxInput.disabled = false;
                    minInput.value = sliders[key].result.from;
                    maxInput.value = sliders[key].result.to;
                } else {
                    sliders[key].update({
                        disable: true,
                        from: sliderConfigs[key][0],
                        to: sliderConfigs[key][1]
                    });
                    minInput.disabled = true;
                    maxInput.disabled = true;
                    minInput.value = '';
                    maxInput.value = '';
                }
            });
        });

        form.addEventListener('submit', e => {
            e.preventDefault();
            currentFilters = {};

            form.querySelectorAll('input[type="checkbox"][name="filterTypes"]:checked').forEach(cb => {
                const key = cb.value;
                const slider = sliders[key];
                currentFilters[key] = {
                    min: slider.result.from,
                    max: slider.result.to
                };
            });

            renderGames();

            const dropdown = bootstrap.Dropdown.getOrCreateInstance(document.getElementById('filterButton'));
            dropdown.hide();
        });
    }

function toggleDetails(gameId) {
    fetch(`/api/minigames/${gameId}/stats`)
        .then(r => r.json())
        .then(data => {
            const s = data.summary;
            const topMinor = data.top_minor || [];
            const topSevere = data.top_severe || [];
            const ws = data.warning_stats || {};

            const html = `
                <p><strong>Total Attempts:</strong> ${s.total_attempts}</p>
                <p><strong>Unique Users:</strong> ${s.unique_users}</p>
                <p><strong>Completed:</strong> ${s.completed}</p>
                <p><strong>Failed:</strong> ${s.failed}</p>
                <p><strong>Completion Rate:</strong> ${s.completion_rate}%</p>
                <p><strong>Average Score:</strong> ${s.average_score}</p>

                <h5 class="mt-3">Top Minor Errors</h5>
                <ul>${topMinor.length ? topMinor.map(e => `<li>${e[0]} (${e[1]})</li>`).join('') : '<li>None</li>'}</ul>

                <h5 class="mt-3">Top Severe Errors</h5>
                <ul>${topSevere.length ? topSevere.map(e => `<li>${e[0]} (${e[1]})</li>`).join('') : '<li>None</li>'}</ul>

                <h5 class="mt-3">Warnings (Monthly)</h5>
                <p><strong>This Month:</strong> ${ws.this_month_warnings || 0}</p>
                <p><strong>Last Month:</strong> ${ws.last_month_warnings || 0}</p>
                <p><strong>% Change:</strong> ${ws.percent_change !== null ? ws.percent_change + '%' : 'N/A'}</p>

                <button id="btn-analyze-warnings" class="btn btn-primary mt-3">Analyze Warnings</button>
            `;

            showStatsModal(html);

            // Attach click handler AFTER modal is rendered
            document.getElementById('btn-analyze-warnings').addEventListener('click', () => {
                // Hide stats modal if open
                if (statsModalInstance) statsModalInstance.hide();

                // Show AI Warning modal above stats
                const warningContent = document.getElementById('ai-warning-content');
                warningContent.innerHTML = '<em>Generating AI warning summary…</em>';

                // Fetch and format AI warning summary
                fetch(`/api/minigames/${gameId}/warnings/ai-summary?force_refresh=true`, { cache: 'no-store' })
                    .then(r => r.json())
                    .then(res => {
                        // Use same styling as AI summary
                        warningContent.innerHTML = `
                            <div id="aiModalBody">
                                ${marked.parse(res.analysis || '<em>No summary available.</em>')}
                            </div>
                        `;
                    })
                    .catch(err => {
                        warningContent.innerHTML = '<div class="alert alert-danger">Failed to load AI warning summary.</div>';
                    });

                // Show the modal
                const aiWarningModal = new bootstrap.Modal(document.getElementById('aiWarningModal'));
                aiWarningModal.show();
            });
        })
        .catch(err => {
            console.error(err);
            showStatsModal('<div class="alert alert-danger">Failed to load stats.</div>');
        });
}


    function attachAiButton(gameId) {
        const btn = document.querySelector(`button.ai-summary-btn[data-game-id="${gameId}"]`);
        if (!btn) return;

        btn.addEventListener('click', () => {
            const modalContent = document.getElementById('aiModalBody');
            const cancelBtn = document.getElementById('btn-cancel-analysis');
            const downloadBtn = document.getElementById('btn-download-analysis');
            const regenerateBtn = document.getElementById("btn-regenerate-analysis");

            if (cancelBtn) cancelBtn.classList.remove('d-none');
            if (downloadBtn) downloadBtn.classList.add('d-none');
            if (regenerateBtn) regenerateBtn.classList.add('d-none');

            showAiModal('<em>Generating summary…</em>');

            fetch(`/api/minigames/${gameId}/ai-summary`)
                .then(r => r.json())
                .then(res => {
                    const result = res.analysis || 'No summary available.';
                    const html = marked.parse(result);
                    modalContent.innerHTML = `<div class="px-2 py-1">${html}</div>`;

                    if (downloadBtn && result.trim() !== '' && result.trim() !== 'No gameplay data available for this mini-game.') {
                        downloadBtn.classList.remove('d-none');
                        downloadBtn.onclick = () => {
                            const blob = new Blob([result], { type: 'text/plain' });
                            const url = URL.createObjectURL(blob);
                            const a = document.createElement('a');
                            a.href = url;
                            a.download = `[Minigame ${gameId}] - AI_ANALYSIS.txt`;
                            document.body.appendChild(a);
                            a.click();
                            document.body.removeChild(a);
                            URL.revokeObjectURL(url);
                        };
                    }

                    if (cancelBtn) cancelBtn.classList.add('d-none');

                    if (regenerateBtn && result.trim() !== 'No gameplay data available for this mini-game.') {
                        regenerateBtn.classList.remove('d-none');
                        regenerateBtn.onclick = function () {
                            if (downloadBtn) downloadBtn.classList.add('d-none');
                            if (regenerateBtn) regenerateBtn.classList.add('d-none');
                            if (cancelBtn) cancelBtn.classList.remove('d-none');

                            modalContent.innerHTML = `
                                <div class="d-flex align-items-center justify-content-center flex-column py-4">
                                    <div class="spinner-border text-primary" role="status" style="width: 3rem; height: 3rem;">
                                        <span class="visually-hidden">Loading...</span>
                                    </div>
                                    <div class="mt-3">Regenerating analysis... please wait.</div>
                                </div>
                            `;

                            fetch(`/api/minigames/${gameId}/ai-summary?force_refresh=true`)
                                .then(r => r.json())
                                .then(res => {
                                    const result = res.analysis || 'No summary available.';
                                    const html = marked.parse(result);
                                    modalContent.innerHTML = `<div class="px-2 py-1">${html}</div>`;

                                    if (downloadBtn && result.trim() !== 'No gameplay data available for this mini-game.') {
                                        downloadBtn.classList.remove('d-none');
                                    }
                                    if (regenerateBtn && result.trim() !== 'No gameplay data available for this mini-game.') {
                                        regenerateBtn.classList.remove('d-none');
                                    }
                                    if (cancelBtn) cancelBtn.classList.add('d-none');

                                    downloadBtn.onclick = () => {
                                        const blob = new Blob([result], { type: 'text/plain' });
                                        const url = URL.createObjectURL(blob);
                                        const a = document.createElement('a');
                                        a.href = url;
                                        a.download = `[Minigame ${gameId}] - AI_ANALYSIS.txt`;
                                        document.body.appendChild(a);
                                        a.click();
                                        document.body.removeChild(a);
                                        URL.revokeObjectURL(url);
                                    };
                                })
                                .catch(err => {
                                    console.error("Regenerate error:", err);
                                    modalContent.innerHTML = `<p class="text-danger">An error occurred while regenerating the analysis.</p>`;
                                });
                        };
                    }
                })
                .catch(err => {
                    console.error(err);
                    modalContent.innerHTML = '<div class="text-danger">Failed to load summary.</div>';
                    if (cancelBtn) cancelBtn.classList.add('d-none');
                });
        });
    }

    // === Combined Stats Table (with Practice/Training filter) ===
    const combinedTable = document.getElementById('combinedTable');
    const refreshCombinedBtn = document.getElementById('refreshCombinedBtn');
    const combinedModeSelect = document.getElementById('combinedModeSelect');

    function fmt(val, dp=2) {
  if (val === null || val === undefined) return '—';
  return Number(val).toFixed(dp);
}

function wireAiExplainButtonsWithinTable(tbody) {
  tbody.querySelectorAll('button[data-level]').forEach(btn => {
    btn.addEventListener('click', () => {
      const gameId = btn.getAttribute('data-level');

      const modalContent = document.getElementById('aiModalBody');
      const cancelBtn = document.getElementById('btn-cancel-analysis');
      const downloadBtn = document.getElementById('btn-download-analysis');
      const regenerateBtn = document.getElementById('btn-regenerate-analysis');

      // keep summary UI untouched; just reuse the modal shell
      if (cancelBtn) cancelBtn.classList.add('d-none');
      if (downloadBtn) downloadBtn.classList.add('d-none');
      if (regenerateBtn) regenerateBtn.classList.add('d-none');

      showAiModal('<em>Generating explanation…</em>');

      fetchAiExplain(gameId)
        .then(({ analysis }) => {
          const result = analysis || 'No explanation available.';
          const html = (typeof marked !== 'undefined') ? marked.parse(result) : result;
          modalContent.innerHTML = `<div class="px-2 py-1">${html}</div>`;

          // allow download of the explanation
          if (downloadBtn && result.trim()) {
            downloadBtn.classList.remove('d-none');
            downloadBtn.onclick = () => {
              const blob = new Blob([result], { type: 'text/plain' });
              const url = URL.createObjectURL(blob);
              const a = document.createElement('a');
              a.href = url;
              a.download = `[Minigame ${gameId}] - AI_EXPLAIN.txt`;
              document.body.appendChild(a);
              a.click();
              document.body.removeChild(a);
              URL.revokeObjectURL(url);
            };
          }
        })
        .catch(() => {
          modalContent.innerHTML = '<div class="text-danger">Failed to get AI explanation.</div>';
        });
    });
  });
}


    function renderCombinedTable(data) {
        if (!combinedTable) return;
        const tbody = combinedTable.querySelector('tbody');
        tbody.innerHTML = '';

        const worstKey = data.worst_ratio ? `${data.worst_ratio.Level_ID}:${data.worst_ratio.Game_ID}:${data.worst_ratio.Mode}` : null;
        const toughKey = data.toughest ? `${data.toughest.Level_ID}:${data.toughest.Game_ID}:${data.toughest.Mode}` : null;

        data.rows.forEach(row => {
            const tr = document.createElement('tr');
            const key = `${row.Level_ID}:${row.Game_ID}:${row.Mode || ''}`;

            if (key === worstKey || key === toughKey) tr.classList.add('table-danger');

            tr.innerHTML = `
            <td>${row.Name}</td>
            <td>${row.Mode || '—'}</td>
            <td class="text-end">${row.completed}</td>
            <td class="text-end">${row.failed}</td>
            <td class="text-end">${row.userexit}</td>
            <td class="text-end">${row.failure_success_str}</td>
            <td class="text-end">${fmt(row.failure_success_ratio)}</td>
            <td class="text-end">${fmt(row.avg_attempts_before_success)}</td>
            <td class="text-end">${row.users_considered}</td>
            <td class="text-end">
                <button class="btn btn-sm btn-outline-danger" data-level="${row.Level_ID}">AI Explain</button>
            </td>
            `;
            tbody.appendChild(tr);
        });

        // 🔗 attach click handlers for the newly-rendered buttons
        wireAiExplainButtonsWithinTable(tbody);
        }


        function currentMode() {
        const sel = document.getElementById('combinedModeSelect');
        return (sel && sel.value) ? sel.value : 'all';
        }

        function fetchAiExplain(gameId) {
        return fetch(`/api/minigames/${gameId}/ai-explain?mode=${encodeURIComponent(currentMode())}`)
            .then(r => r.json());
    }


    function loadCombined() {
    const mode = currentMode();
    fetch(`/api/minigames/combined-stats?mode=${encodeURIComponent(mode)}`)
        .then(r => r.json())
        .then(data => renderCombinedTable(data))
        .catch(err => {
        console.error(err);
        if (combinedTable) {
            combinedTable.querySelector('tbody').innerHTML =
            '<tr><td colspan="9"><div class="alert alert-danger mb-0">Failed to load combined stats.</div></td></tr>';
        }
        });
    }

    if (refreshCombinedBtn) refreshCombinedBtn.addEventListener('click', loadCombined);
    if (combinedModeSelect) combinedModeSelect.addEventListener('change', loadCombined);
    loadCombined();

});
