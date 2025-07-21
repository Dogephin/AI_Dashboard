document.addEventListener('DOMContentLoaded', () => {
    const grid = document.getElementById('gamesGrid');

    fetch('/api/minigames')
        .then(r => r.json())
        .then(games => {
            // Step 1: Fetch stats for each game
            return Promise.all(games.map(game =>
                fetch(`/api/minigames/${game.Level_ID}/stats`)
                    .then(r => r.json())
                    .then(stats => {
                        game.stats = stats.summary;
                        return game;
                    })
                    .catch(err => {
                        console.error(`Stats failed for Game ID ${game.Level_ID}`, err);
                        return game; // still include even if stats fail
                    })
            ));
        })
        .then(gamesWithStats => {
            grid.innerHTML = ''; // Clear loading

            // Store globally if you want to re-filter later
            window._allGames = gamesWithStats;

            // Initial render
            gamesWithStats.forEach(game => grid.appendChild(createCard(game)));

            // Hook up filtering logic
            setupFilterForm(gamesWithStats);
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
            <p class="text-sm text-gray-600 mb-2">Game ID ${game.Game_ID} | Level ${game.Level_ID}</p>
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

    function toggleDetails(gameId) {
        fetch(`/api/minigames/${gameId}/stats`)
            .then(r => r.json())
            .then(data => {
                const s = data.summary;
                const topMinor = data.top_minor || [];
                const topSevere = data.top_severe || [];

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
                `;

                showStatsModal(html);
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

            // Initial state: show cancel, hide download and regenerate
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

                    // Enable download if result is non-empty
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

                    // Hide cancel after load
                    if (cancelBtn) cancelBtn.classList.add('d-none');

                    // Show regenerate button
                    if (regenerateBtn && result.trim() !== 'No gameplay data available for this mini-game.') {
                        regenerateBtn.classList.remove('d-none'); // Show regenerate button
                        regenerateBtn.onclick = function () {
                            // Hide regenerate button and download button, show cancel button
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

                                    // Show regenerate button and download button, hide cancel button
                                    if (downloadBtn && result.trim() !== 'No gameplay data available for this mini-game.') {
                                        downloadBtn.classList.remove('d-none');
                                    }
                                    if (regenerateBtn && result.trim() !== 'No gameplay data available for this mini-game.') {
                                        regenerateBtn.classList.remove('d-none');
                                    }
                                    if (cancelBtn) cancelBtn.classList.add('d-none');


                                    const html = marked.parse(result);
                                    modalContent.innerHTML = `<div class="px-2 py-1">${html}</div>`;

                                    // Update download button action
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

    /* ────────────────────────────────────────────────────────────
        Filter logic setup
    ──────────────────────────────────────────────────────────── */
    const sliderConfigs = {
        total_attempts: [0, 500],
        completion_rate: [0, 100],
        average_score: [0, 500],
        failed: [0, 300]
    };

    const sliders = {};

    function setupFilterForm(games) {
        const form = document.getElementById('filterForm');
        if (!form) return;

        // Prevent dropdown close on clicks inside
        document.querySelector('#filterDropdown .dropdown-menu')
            ?.addEventListener('click', e => e.stopPropagation());

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

            // Update slider when user types into inputs
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

        // Enable/disable sliders + inputs based on checkbox
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

        // Filter logic on submit
        form.addEventListener('submit', e => {
            e.preventDefault();
            const activeFilters = {};

            form.querySelectorAll('input[type="checkbox"][name="filterTypes"]:checked').forEach(cb => {
                const key = cb.value;
                const slider = sliders[key];
                activeFilters[key] = {
                    min: slider.result.from,
                    max: slider.result.to
                };
            });

            const filtered = games.filter(game => {
                const stats = game.stats || {};
                for (const key in activeFilters) {
                    const { min, max } = activeFilters[key];
                    const val = stats[key];
                    if (val === undefined || val < min || val > max) return false;
                }
                return true;
            });

            grid.innerHTML = '';
            filtered.forEach(g => grid.appendChild(createCard(g)));

            const dropdown = bootstrap.Dropdown.getOrCreateInstance(document.getElementById('filterButton'));
            dropdown.hide();
        });
    }

});