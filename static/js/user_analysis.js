document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('user-form');
    const userSelect = document.getElementById('user-select');
    const gameSelect = document.getElementById('game-select');

    let rowDataArray = [];

    form.addEventListener('submit', (e) => {
        e.preventDefault(); // prevent page reload

        const userId = userSelect.value;
        const gameId = gameSelect.value;

        const userName = userSelect.options[userSelect.selectedIndex].textContent.trim();
        const gameName = gameSelect.options[gameSelect.selectedIndex].textContent.trim();

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
                    if ('analysis' in data) {
                        const header = document.createElement('div');
                        header.className = 'alert alert-success';
                        header.innerText = data.message;
                        container.appendChild(header);

                        const summaryCard = document.createElement('div');
                        summaryCard.className = 'results-summary-container';
                        container.appendChild(summaryCard);

                        const stats = data.analysis;

                        // Insert summary statistics
                        summaryCard.innerHTML += `
                            <div class="results-summary-container__result">
                                <div class="heading-tertiary">Total Attempts</div>
                                <div class="result-box">
                                    <div class="heading-primary">${stats.attempts}</div>
                                </div>
                            </div>
                            <div class="results-summary-container__options">
                                <div class="heading-secondary heading-secondary--blue">Summary</div>
                                <div class="summary-result-options">
                                    <div class="result-option result-option-completedattempts">
                                        <div class="icon-box">
                                        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#00BD91" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>
                                        <span class="completedattempts-icon-text p-1">Completed Attempts</span>
                                        </div>
                                        <div class="result-box"><span>${stats.completed_attempts}</span> / ${stats.attempts}</div>
                                    </div>
                                    <div class="result-option result-option-failedattempts">
                                        <div class="icon-box">
                                        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#FF5757" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>
                                        <span class="failedattempts-icon-text p-1">Failed Attempts</span>
                                        </div>
                                        <div class="result-box"><span>${stats.failed_attempts}</span> / ${stats.attempts}</div>
                                    </div>
                                    <div class="result-option result-option-averagescore">
                                        <div class="icon-box">
                                        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#FF9D00" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a10 10 0 1 0 10 10H12V2zM21.18 8.02c-1-2.3-2.85-4.17-5.16-5.18"/></svg>
                                        <span class="averagescore-icon-text p-1">Average Score</span>
                                        </div>
                                        <div class="result-box"><span>${stats.average_score}</span></div>
                                    </div>
                                    <div class="result-option result-option-minscore">
                                        <div class="icon-box">
                                        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#1125D4" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20.2 17.2l-7.7-7.7-4 4-5.7-5.7"/><path d="M15 18h6v-6"/></svg>
                                        <span class="minscore-icon-text p-1">Minimum Score</span>
                                        </div>
                                        <div class="result-box"><span>${stats.min_score}</span></div>
                                    </div>
                                    <div class="result-option result-option-maxscore">
                                        <div class="icon-box">
                                        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#1125D4" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20.2 7.8l-7.7 7.7-4-4-5.7 5.7"/><path d="M15 7h6v6"/></svg>
                                        <span class="maxscore-icon-text p-1">Maximum Score</span>
                                        </div>
                                        <div class="result-box"><span>${stats.max_score}</span></div>
                                    </div>
                                </div>
                            </div>
                            </div>
                        `

                        // Create result card
                        const resultCard = document.createElement('div');
                        resultCard.className = 'stats-card mt-4';
                        container.appendChild(resultCard);

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
                                        type: 'bar',
                                        label: 'Score per Attempt',
                                        data: scores,
                                        backgroundColor: 'rgba(54, 162, 235, 0.6)',
                                        borderColor: 'rgba(54, 162, 235, 1)',
                                        borderWidth: 1,
                                        hoverBackgroundColor: 'rgba(54, 162, 235, 0.8)',
                                        hoverBorderColor: 'rgba(54, 162, 235, 1)',
                                        borderRadius: 6,
                                        barPercentage: 0.6,
                                        datalabels: {
                                            display: false
                                        }
                                    },
                                    {
                                        type: 'line',
                                        label: 'Trend Line',
                                        data: scores,
                                        fill: false,
                                        borderColor: '#ff6384',
                                        backgroundColor: '#ff6384',
                                        tension: 0.3,
                                        pointRadius: 4,
                                        pointHoverRadius: 6,
                                        datalabels: {
                                            display: true,
                                            anchor: 'end',
                                            align: 'top',
                                            formatter: Math.round,
                                            font: {
                                                weight: 'bold'
                                            }
                                        }
                                    }
                                ]
                            },
                            options: {
                                responsive: true,
                                maintainAspectRatio: false,
                                plugins: {
                                    legend: {
                                        position: 'top',
                                        labels: {
                                            boxWidth: 12,
                                            padding: 15
                                        }
                                    },
                                    tooltip: {
                                        mode: 'index',
                                        intersect: false,
                                        callbacks: {
                                            label: context => `Score: ${context.parsed.y}`
                                        }
                                    },
                                    title: {
                                        display: true,
                                        text: 'Score Trend Across Attempts',
                                        font: {
                                            size: 18
                                        },
                                        padding: {
                                            top: 10,
                                            bottom: 20
                                        }
                                    }
                                },
                                scales: {
                                    x: {
                                        title: {
                                            display: true,
                                            text: 'Attempt',
                                            font: {
                                                size: 14,
                                                weight: 'bold'
                                            }
                                        }
                                    },
                                    y: {
                                        beginAtZero: true,
                                        title: {
                                            display: true,
                                            text: 'Score',
                                            font: {
                                                size: 14,
                                                weight: 'bold'
                                            }
                                        }
                                    }
                                }
                            },
                            plugins: [ChartDataLabels]
                        });

                        const fullAnalysisBtn = document.createElement('button');
                        fullAnalysisBtn.className = 'btn overall-analysis-btn mt-4 d-block mx-auto';
                        fullAnalysisBtn.innerHTML = `
                            <svg height="24" width="24" fill="#FFFFFF" viewBox="0 0 24 24" data-name="Layer 1" id="Layer_1" class="sparkle">
                                <path d="M10,21.236,6.755,14.745.264,11.5,6.755,8.255,10,1.764l3.245,6.491L19.736,11.5l-6.491,3.245ZM18,21l1.5,3L21,21l3-1.5L21,18l-1.5-3L18,18l-3,1.5ZM19.333,4.667,20.5,7l1.167-2.333L24,3.5,21.667,2.333,20.5,0,19.333,2.333,17,3.5Z"></path>
                            </svg>
                            <span class="text">Generate Overall AI Analysis</span>
                            `;
                        container.appendChild(fullAnalysisBtn);

                        fullAnalysisBtn.addEventListener('click', () => {
                            const downloadBtn = document.getElementById('btn-download-analysis');
                            if (downloadBtn) {
                                downloadBtn.classList.add('d-none');  // Hide download button initially
                            }
                            const modal = new bootstrap.Modal(document.getElementById('aiAnalysisModal'));
                            const modalContent = document.getElementById('ai-analysis-content');
                            modalContent.innerHTML = `
                            <div id="ai-loading" class="d-flex align-items-center justify-content-center flex-column py-4">
                                <div class="spinner-border text-primary" role="status" style="width: 3rem; height: 3rem;">
                                    <span class="visually-hidden">Loading...</span>
                                </div>
                                <div class="mt-3">Analyzing all attempts... please wait.</div>
                            </div>
                        `;
                            modal.show();

                            fetch('/user', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ bulk_analysis: rowDataArray }) // send all attempt rows
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
                                    // Enable download button
                                    const downloadBtn = document.getElementById('btn-download-analysis');
                                    if (downloadBtn) {
                                        if (result && result.trim() !== '') {
                                            downloadBtn.classList.remove('d-none');  // Show button
                                            downloadBtn.onclick = () => {
                                                const blob = new Blob([result], { type: 'text/plain' });
                                                const url = URL.createObjectURL(blob);
                                                const a = document.createElement('a');
                                                const fileName = "[" + gameName + "] - AI_ANALYSIS_FOR_ALL_ATTEMPTS - USER " + userId + ".txt";
                                                a.href = url;
                                                a.download = fileName;
                                                document.body.appendChild(a);
                                                a.click();
                                                document.body.removeChild(a);
                                                URL.revokeObjectURL(url);
                                            };
                                        } else {
                                            downloadBtn.classList.add('d-none');  // Hide if empty
                                        }
                                    }
                                })
                                .catch(err => {
                                    console.error('Bulk analysis error:', err);
                                    modalContent.innerHTML = `<p class="text-danger">An error occurred during bulk analysis.</p>`;
                                });
                        });

                        // Table
                        const table = document.createElement('table');
                        table.className = 'table results-table mt-3';
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
                                const downloadBtn = document.getElementById('btn-download-analysis');
                                if (downloadBtn) {
                                    downloadBtn.classList.add('d-none');  // Hide download button initially
                                }
                                const index = parseInt(btn.getAttribute('data-index'));
                                const rowData = rowDataArray[index];
                                const fileName = "[" + gameName + "] - AI_ANALYSIS_FOR_ATTEMPT_" + (index + 1) + " - USER " + userId + ".txt";

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
                                        // Enable download button
                                        const downloadBtn = document.getElementById('btn-download-analysis');
                                        if (downloadBtn) {
                                            if (result && result.trim() !== '') {
                                                downloadBtn.classList.remove('d-none');  // Show button
                                                downloadBtn.onclick = () => {
                                                    const blob = new Blob([result], { type: 'text/plain' });
                                                    const url = URL.createObjectURL(blob);
                                                    const a = document.createElement('a');
                                                    a.href = url;
                                                    a.download = fileName;
                                                    document.body.appendChild(a);
                                                    a.click();
                                                    document.body.removeChild(a);
                                                    URL.revokeObjectURL(url);
                                                };
                                            } else {
                                                downloadBtn.classList.add('d-none');  // Hide if empty
                                            }
                                        }
                                    })
                                    .catch(err => {
                                        console.error('Analysis error:', err);
                                        modalContent.innerHTML = `<p class="text-danger">An error occurred while analyzing this attempt.</p>`;
                                    });
                            });
                        });
                    }
                    else {
                        const sections = [
                            { title: "Imprecision Mistakes", id: "imprecision", data: data.results.imprecision },
                            { title: "Warnings Mistakes ", id: "warnings", data: data.results.warning },
                            { title: "Minors Mistakes ", id: "minors", data: data.results.minor },
                            { title: "Severes Mistakes ", id: "severes", data: data.results.severe }
                        ];

                        sections.forEach(section => {
                            if (section.data && section.data.length > 0) {
                                const sectionDiv = document.createElement("div");
                                sectionDiv.className = "result-section";

                                // Header Wrapper
                                const headerWrapper = document.createElement("div");
                                headerWrapper.className = "section-header";

                                // Header Title
                                const header = document.createElement("h3");
                                header.textContent = `${section.title} (${section.data.length})`;

                                // Generate Button
                                const aiBtn = document.createElement("button");
                                aiBtn.className = "ai-btn";
                                aiBtn.textContent = "Categorize errors";
                                // Attach click event to call the API with section.data
                                aiBtn.addEventListener("click", () => {
                                    aiOutputDiv.textContent = "Loading...";
                                    aiOutputDiv.classList.remove('hidden');
                                    fetch('/generate-ai-prompt', {
                                        method: 'POST',
                                        headers: {
                                            'Content-Type': 'application/json'
                                        },
                                        body: JSON.stringify({
                                            title: section.title,
                                            items: section.data
                                        })
                                    })
                                        .then(response => response.json())
                                        .then(data => {
                                            console.log(data)
                                            aiOutputDiv.innerHTML = `
                                            <div class="ai-generated-box">
                                                <h4>Error Categories</h4>
                                                <pre>${data.Categories || 'No prompt generated.'}</pre>
                                            </div>
                                        `;
                                        })
                                        .catch(error => {
                                            console.error('Error generating content:', error);
                                            aiOutputDiv.innerHTML = `<div class="error">Failed to generate content.</div>`;
                                        });
                                });

                                headerWrapper.appendChild(header);
                                headerWrapper.appendChild(aiBtn);
                                sectionDiv.appendChild(headerWrapper);

                                // List Items
                                const ul = document.createElement("ul");
                                ul.id = section.id;

                                const visibleCount = 5;
                                section.data.forEach((item, index) => {
                                    const li = document.createElement("li");
                                    li.className = item.type ? item.type.toLowerCase().replace(/\W+/g, '-') : '';
                                    li.textContent = item.text;
                                    if (index >= visibleCount) {
                                        li.style.display = "none";
                                        li.classList.add("hidden-item");
                                    }
                                    ul.appendChild(li);
                                });

                                sectionDiv.appendChild(ul);

                                // AI Output Placeholder (initially hidden)
                                const aiOutputDiv = document.createElement("div");
                                aiOutputDiv.className = "ai-output hidden";
                                sectionDiv.appendChild(aiOutputDiv);

                                // Show More Button if needed
                                if (section.data.length > visibleCount) {
                                    const toggleBtn = document.createElement("button");
                                    toggleBtn.textContent = "Show More";
                                    toggleBtn.className = "toggle-btn";
                                    toggleBtn.addEventListener("click", () => {
                                        const hiddenItems = ul.querySelectorAll(".hidden-item");
                                        const isExpanded = toggleBtn.textContent === "Show Less";
                                        hiddenItems.forEach(item => {
                                            item.style.display = isExpanded ? "none" : "list-item";
                                        });
                                        toggleBtn.textContent = isExpanded ? "Show More" : "Show Less";
                                    });
                                    sectionDiv.appendChild(toggleBtn);
                                }
                                container.appendChild(sectionDiv);
                            }
                        });
                    }
                }
            })
            .catch(error => console.error('Error:', error));
    });
});
