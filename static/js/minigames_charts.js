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
    const url = '/api/minigames/completion/ai-priority?top_n=5';
    showAiModal('<em>Asking AI where to prioritise support…</em>');
    const modalContent = document.getElementById('aiModalBody');
    const downloadBtn = document.getElementById('btn-download-analysis');
    const cancelBtn = document.getElementById('btn-cancel-analysis');
    const regenBtn = document.getElementById('btn-regenerate-analysis');

    if (downloadBtn) downloadBtn.classList.add('d-none');
    if (regenBtn) regenBtn.classList.add('d-none');
    if (cancelBtn) cancelBtn.classList.add('d-none');

    fetch(url, { cache: 'no-store' })
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
      })
      .catch(() => {
        modalContent.innerHTML = '<div class="text-danger">Failed to fetch AI priority analysis.</div>';
      });
  });
}
