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
});
