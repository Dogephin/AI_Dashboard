document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('user-form');
    const userSelect = document.getElementById('user-select');
    const gameSelect = document.getElementById('game-select');

    let rowDataArray = [];

    form.addEventListener('submit', (e) => {
        e.preventDefault(); // prevent page reload

        const userId = userSelect.value;
        const gameId = gameSelect.value;

        fetch('/user', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ user_id: userId, game_id: gameId })
        })
            .then(response => response.json())
            .then(data => {
                const container = document.getElementById('results-container');
                container.className = 'stats-container';
                container.innerHTML = ''; // Clear previous content
                rowDataArray = []; // clear previous rows

                if (data.status === 'error') {
                    container.innerHTML = `<div class="alert alert-warning">${data.message}</div>`;
                }
                else if (data.status === 'success') {
                    const header = document.createElement('div');
                    header.className = 'alert alert-success';
                    header.innerText = data.message;
                    container.appendChild(header);


                    // Create result card
                    const resultCard = document.createElement('div');
                    resultCard.className = 'stats-card';
                    container.appendChild(resultCard);

                    // Insert statistics
                    const stats = data.analysis;
                    resultCard.innerHTML += `
                        <h5 class="mb-3">Game Attempt Summary</h5>
                        <p><strong>Total Attempts: </strong>${stats.attempts}</p>
                        <p><strong>Completed Attempts: </strong>${stats.completed_attempts}</p>
                        <p><strong>Failed Attempts: </strong>${stats.failed_attempts}</p>
                        <p><strong>Average Score: </strong>${stats.average_score}</p>
                        <p><strong>Min Score: </strong>${stats.min_score}</p>
                        <p><strong>Max Score: </strong>${stats.max_score}</p>
                    `;

                    // Chart
                    const canvas = document.createElement('canvas');
                    canvas.id = 'score-chart';
                    resultCard.appendChild(canvas);

                    const labels = data.analysis.trend.map(item => item.Attempt);
                    const scores = data.analysis.trend.map(item => item.Score);

                    new Chart(canvas, {
                        type: 'bar',
                        data: {
                            labels: labels,
                            datasets: [
                                {
                                    type: 'line',
                                    label: 'Score Trend (Line)',
                                    data: scores,
                                    fill: false,
                                    borderColor: 'rgba(54, 162, 235, 1)',
                                    backgroundColor: 'rgba(54, 162, 235, 0.2)',
                                    tension: 0.1,
                                    order: 2
                                },
                                {
                                    type: 'bar',
                                    label: 'Score per Attempt (Bar)',
                                    data: scores,
                                    backgroundColor: 'rgba(75, 192, 192, 0.6)',
                                    borderColor: 'rgba(75, 192, 192, 1)',
                                    borderWidth: 1,
                                    order: 1
                                }
                            ]
                        },
                        options: {
                            responsive: true,
                            plugins: {
                                tooltip: {
                                    mode: 'index',
                                    intersect: false
                                }
                            },
                            scales: {
                                x: {
                                    title: { display: true, text: 'Attempt' }
                                },
                                y: {
                                    title: { display: true, text: 'Score' },
                                    beginAtZero: true
                                }
                            }
                        }
                    });

                    // Table
                    const table = document.createElement('table');
                    table.className = 'table table-bordered table-striped mt-5 results-table';
                    const keys = ["Game_Start", "Game_End", "Overall_Results", "Score", "Status"];


                    // Add "Attempt" column header
                    const thead = document.createElement('thead');
                    thead.innerHTML = `<tr><th>Attempt</th>${keys.map(k => `<th>${k}</th>`).join('')}<th>AI Analysis</th></tr>`;
                    table.appendChild(thead);

                    const tbody = document.createElement('tbody');
                    data.results.forEach((row, rowIndex) => {
                        rowDataArray.push(row);
                        const tr = document.createElement('tr');

                        // Add attempt number first
                        let rowHtml = `<td>Attempt ${rowIndex + 1}</td>`;

                        rowHtml += keys.map(k => {
                            if (k === "Overall_Results" && row[k]) {
                                const shortText = row[k].substring(0, 100);
                                const cellId = `full-result-${rowIndex}`;
                                return `
                                    <td>
                                        <div class="result-wrapper">
                                            <span class="show-full-result"
                                                data-target="${cellId}"
                                                data-fulltext="${encodeURIComponent(row[k])}"
                                                style="cursor: pointer; color: blue;"
                                                title="Click to view full result">
                                                ${shortText}...
                                            </span>
                                            <div id="${cellId}" class="full-result-text" style="display:none; white-space: pre-wrap; margin-top: 5px;"></div>
                                        </div>
                                    </td>
                                `;
                            } else {
                                return `<td>${row[k]}</td>`;
                            }
                        }).join('');

                        rowHtml += `
                        <td>
                            <button class="btn analyze-btn" data-index='${rowIndex}' title="Analyze this row">
                                <svg height="24" width="24" fill="#FFFFFF" viewBox="0 0 24 24" data-name="Layer 1" id="Layer_1" class="sparkle">
                                    <path d="M10,21.236,6.755,14.745.264,11.5,6.755,8.255,10,1.764l3.245,6.491L19.736,11.5l-6.491,3.245ZM18,21l1.5,3L21,21l3-1.5L21,18l-1.5-3L18,18l-3,1.5ZM19.333,4.667,20.5,7l1.167-2.333L24,3.5,21.667,2.333,20.5,0,19.333,2.333,17,3.5Z"></path>
                                </svg>

                                <span class="text">Generate</span>
                            </button>
                        </td>`;

                        tr.innerHTML = rowHtml;
                        tbody.appendChild(tr);
                    });
                    table.appendChild(tbody);
                    container.appendChild(table);


                    // Attach event listeners to all .show-full-result elements
                    document.querySelectorAll('.show-full-result').forEach(span => {
                        span.addEventListener('click', () => {
                            const targetId = span.getAttribute('data-target');
                            const fullText = decodeURIComponent(span.getAttribute('data-fulltext'));
                            const fullTextEl = document.getElementById(targetId);
                            const shortTextEl = span;

                            if (fullTextEl.style.display === 'none') {
                                fullTextEl.style.display = 'block';
                                fullTextEl.innerText = fullText;
                                shortTextEl.style.display = 'none';  // hide short version
                            } else {
                                fullTextEl.style.display = 'none';
                                shortTextEl.style.display = 'inline';  // show short version
                            }
                            fullTextEl.addEventListener('click', () => {
                                fullTextEl.style.display = 'none';
                                shortTextEl.style.display = 'inline';
                            });
                        });
                    });

                    // Attach analyze button click handlers
                    document.querySelectorAll('.analyze-btn').forEach(btn => {
                        btn.addEventListener('click', () => {
                            const index = parseInt(btn.getAttribute('data-index'));
                            const rowData = rowDataArray[index];

                            // Show modal with loading message
                            const modal = new bootstrap.Modal(document.getElementById('aiAnalysisModal'));
                            const modalContent = document.getElementById('ai-analysis-content');
                            modalContent.innerHTML = `
                                <div id="ai-loading" class="d-flex align-items-center justify-content-center flex-column py-4">
                                    <div class="spinner-border text-primary" role="status" style="width: 3rem; height: 3rem;">
                                        <span class="visually-hidden">Loading...</span>
                                    </div>
                                    <div class="mt-3">Analyzing performance... please wait.</div>
                                </div>
                            `;
                            modal.show();

                            fetch('/user', {
                                method: 'POST',
                                headers: {
                                    'Content-Type': 'application/json'
                                },
                                body: JSON.stringify({ row_analysis: rowData })
                            })
                                .then(response => response.json())
                                .then(data => {
                                    const result = data.analysis || data.message || 'No analysis result.';
                                    const markdownHtml = marked.parse(result);
                                    modalContent.innerHTML = `
                                        <div class="px-3 py-2" style="font-size: 1rem; line-height: 1.6;">
                                            ${markdownHtml}
                                        </div>
                                    `;
                                })
                                .catch(err => {
                                    console.error('Analysis error:', err);
                                    modalContent.innerHTML = `<p class="text-danger">An error occurred while analyzing this attempt.</p>`;
                                });
                        });
                    });
                }
            })
            .catch(error => console.error('Error:', error));
    });
});
