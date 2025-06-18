document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('user-form');
    const userSelect = document.getElementById('user-select');
    const gameSelect = document.getElementById('game-select');

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
                        type: 'bar', // base type (will be overridden for line)
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

                    // Table for debugging (will be removed later)
                    const table = document.createElement('table');
                    table.className = 'table table-bordered table-striped';
                    const keys = Object.keys(data.results[0]);
                    const thead = document.createElement('thead');
                    thead.innerHTML = `<tr>${keys.map(k => `<th>${k}</th>`).join('')}</tr>`;
                    table.appendChild(thead);
                    const tbody = document.createElement('tbody');
                    data.results.forEach(row => {
                        const tr = document.createElement('tr');
                        tr.innerHTML = keys.map(k => `<td>${row[k]}</td>`).join('');
                        tbody.appendChild(tr);
                    });
                    table.appendChild(tbody);
                    container.appendChild(table);
                }
            })
            .catch(error => console.error('Error:', error));
    });
});
