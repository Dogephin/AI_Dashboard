/* static/js/minigames_analysis.js
    ---------------------------------------------------------------
    Handles the interactive mini-game dashboard (minigames.html).
*/

document.addEventListener('DOMContentLoaded', () => {
    const grid = document.getElementById('gamesGrid');   // <section id="gamesGrid">

    /* ────────────────────────────────────────────────────────────
        1.  Load the list of mini-games and build cards
    ──────────────────────────────────────────────────────────── */
    fetch('/api/minigames')
        .then(r => r.json())
        .then(games => {
            grid.innerHTML = '';        // clear loading text
            games.forEach(g => grid.appendChild(createCard(g)));
        })
        .catch(err => {
            console.error('Failed to load mini-games:', err);
            grid.innerHTML = '<p class="text-danger">Could not load mini-games.</p>';
        });

    /* helper to build one card */
    function createCard(game) {
        const card = document.createElement('div');
        card.className = 'game-card';      // styled in minigames.html <style>
        card.innerHTML = `
            <h2 class="text-lg font-semibold mb-1" style="color: #000;">${game.Name}</h2>
            <p class="text-sm text-gray-600 mb-2">Game ID ${game.Game_ID} | Level ${game.Level_ID}</p>
            <button class="btn btn-primary btn-sm" data-game-id="${game.Level_ID}">
                View Stats
            </button>
            <div class="details mt-3" id="details-${game.Level_ID}" style="display:none;"></div>
            <button class="btn btn-outline-secondary btn-sm ai-summary-btn" data-game-id="${game.Level_ID}">
                View AI Summary
            </button>
        `;

        /* click handler */
        card.querySelector('button').addEventListener('click', () =>
            toggleDetails(game.Level_ID)
        );
        setTimeout(() => attachAiButton(game.Level_ID), 0);
        return card;
    }

    /* ────────────────────────────────────────────────────────────
        2.  Expand / collapse details for one game
    ──────────────────────────────────────────────────────────── */
    function toggleDetails(gameId) {
        console.log('Fetching stats for game ID:', gameId);
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

    /* ────────────────────────────────────────────────────────────
        3.  AI summary generation
    ──────────────────────────────────────────────────────────── */
    function attachAiButton(gameId) {
        const btn = document.querySelector(`button.ai-summary-btn[data-game-id="${gameId}"]`);
        if (!btn) return;

        btn.addEventListener('click', () => {
            showAiModal('<em>Generating summary…</em>');

            fetch(`/api/minigames/${gameId}/ai-summary`)
                .then(r => r.json())
                .then(res => {
                    const html = res.analysis ? marked.parse(res.analysis)
                        : 'No summary available.';
                    showAiModal(`<div class="px-2 py-1">${html}</div>`);
                })
                .catch(err => {
                    console.error(err);
                    showAiModal('<div class="text-danger">Failed to load summary.</div>');
                });
        });
    }

});
