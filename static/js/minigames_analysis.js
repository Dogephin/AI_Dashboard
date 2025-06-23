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
    `;

    /* click handler */
    card.querySelector('button').addEventListener('click', () =>
      toggleDetails(game.Level_ID)
    );
    return card;
  }

  /* ────────────────────────────────────────────────────────────
     2.  Expand / collapse details for one game
  ──────────────────────────────────────────────────────────── */
  function toggleDetails(gameId) {
    const details = document.getElementById(`details-${gameId}`);

    if (details.style.display === 'none' || details.style.display === '') {
      // first open ➜ fetch stats if not cached
      if (!details.dataset.loaded) {
        details.innerHTML = '<em>Loading…</em>';
        fetch(`/api/minigames/${gameId}/stats`)
          .then(r => r.json())
          .then(data => {
            details.dataset.loaded = '1';
            details.innerHTML = renderStats(data, gameId);
            attachAiButton(gameId);          // wire AI button
          })
          .catch(err => {
            console.error(err);
            details.innerHTML =
              '<span class="text-danger">Could not load stats.</span>';
          });
      }
      details.style.display = 'block';
    } else {
      details.style.display = 'none';
    }
  }

  /* render the stats block */
  function renderStats(data, gameId) {
    const s = data.summary;
    const topMinor  = data.top_minor  || [];
    const topSevere = data.top_severe || [];

    return `
      <div class="stat-grid">
        <p><strong>Total Attempts:</strong> ${s.total_attempts}</p>
        <p><strong>Unique Users:</strong> ${s.unique_users}</p>
        <p><strong>Completed:</strong> ${s.completed}</p>
        <p><strong>Failed:</strong> ${s.failed}</p>
        <p><strong>Completion Rate:</strong> ${s.completion_rate}%</p>
        <p><strong>Average Score:</strong> ${s.average_score}</p>

        <h4 class="mt-3">Top Minor Errors</h4>
        <ul>${topMinor.length ? topMinor.map(e => `<li>${e[0]} (${e[1]})</li>`).join('') : '<li>None</li>'}</ul>

        <h4 class="mt-2">Top Severe Errors</h4>
        <ul>${topSevere.length ? topSevere.map(e => `<li>${e[0]} (${e[1]})</li>`).join('') : '<li>None</li>'}</ul>

        <button class="btn btn-outline-secondary btn-sm mt-3 ai-summary-btn"
                data-game-id="${gameId}">
          Generate AI Summary
        </button>
        <div id="ai-summary-${gameId}" class="ai-summary mt-3"></div>
      </div>`;
  }

  /* ────────────────────────────────────────────────────────────
     3.  AI summary generation
  ──────────────────────────────────────────────────────────── */
  function attachAiButton(gameId) {
    const btn = document.querySelector(
      `button.ai-summary-btn[data-game-id="${gameId}"]`
    );
    if (!btn) return;

    btn.addEventListener('click', () => {
      const out = document.getElementById(`ai-summary-${gameId}`);
      out.innerHTML = '<em>Generating summary…</em>';

      fetch(`/api/minigames/${gameId}/ai-summary`)
        .then(r => r.json())
        .then(res => {
          const html = res.analysis ? marked.parse(res.analysis)
                                    : 'No summary available.';
          out.innerHTML = `<div class="px-2 py-1">${html}</div>`;
        })
        .catch(err => {
          console.error(err);
          out.innerHTML =
            '<span class="text-danger">Failed to generate summary.</span>';
        });
    });
  }
});
