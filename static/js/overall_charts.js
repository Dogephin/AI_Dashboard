document.addEventListener("DOMContentLoaded", function () {
    const ctx = document.getElementById('errorChart').getContext('2d');

    const chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: chartDataFromFlask.labels,
            datasets: chartDataFromFlask.datasets.map(dataset => ({
                ...dataset,
                fill: false,
                tension: 0.1,
                borderWidth: 2,
                pointRadius: 3
            }))
        },
        options: {
            responsive: true,
            plugins: {
                title: {
                    display: true,
                    text: 'Error Frequency Over Time'
                },
                legend: {
                    display: true
                }
            },
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
    const scatterCtx = document.getElementById('scatterChart').getContext('2d');

    new Chart(scatterCtx, {
        type: 'scatter',
        data: scatterChartDataFromFlask,
        options: {
            responsive: true,
            plugins: {
                title: {
                    display: true,
                    text: 'Performance vs Session Duration'
                },
                legend: {
                    display: true
                }
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: 'Duration (minutes)'
                    },
                    beginAtZero: true
                },
                y: {
                    title: {
                        display: true,
                        text: 'Score'
                    },
                    beginAtZero: true
                }
            }
        }
    });
    const avgScoreCtx = document.getElementById('avgScoreChart').getContext('2d');

    new Chart(avgScoreCtx, {
        type: 'bar',
        data: avgScoreChartDataFromFlask,
        options: {
            responsive: true,
            plugins: {
                title: {
                    display: true,
                    text: 'Average vs Max Score per Minigame (Practice)'
                },
                legend: {
                    display: true,
                    position: 'top'
                },
                tooltip: {
                    mode: 'index',
                    intersect: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    suggestedMax: 400,
                    title: {
                        display: true,
                        text: 'Score'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Minigames'
                    }
                }
            }
        }
    });


});
