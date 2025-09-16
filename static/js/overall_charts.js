document.addEventListener("DOMContentLoaded", function () {
    Chart.register(ChartZoom);
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
                },
                zoom: {
                    zoom: {
                        wheel: {
                            enabled: true, // Enables zooming with the mouse wheel
                        },
                        pinch: {
                            enabled: true
                        },
                        mode: 'x', 
                    },
                    pan: {
                        enabled: true, 
                        mode: 'x', 
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true
                },
                x: {
                    min: 0,
                    max: 40
                }
            }
        }
    });
    const scatterCtx = document.getElementById('scatterChart').getContext('2d');

    if (scatterChartDataFromFlask && scatterChartDataFromFlask.datasets && scatterChartDataFromFlask.datasets.length > 0) {
        const dataPoints = scatterChartDataFromFlask.datasets[0].data;

        // Use a loop to find the min and max for x and y
        let xMin = Infinity, xMax = -Infinity;
        let yMin = Infinity, yMax = -Infinity;

        dataPoints.forEach(point => {
            if (point.x < xMin) xMin = point.x;
            if (point.x > xMax) xMax = point.x;
            if (point.y < yMin) yMin = point.y;
            if (point.y > yMax) yMax = point.y;
        });

        // Move the chart creation inside the if block
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
            },
            zoom: {
                zoom: {
                    wheel: {
                        enabled: true,
                    },
                    pinch: {
                        enabled: true
                    },
                    mode: 'xy',
                },
                pan: {
                    enabled: true,
                    mode: 'xy',
                },
                limits: {
                    x: {
                        min: xMin,
                        max: xMax
                    },
                    y: {
                        min: yMin,
                        max: yMax
                    }
                }
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
    }
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
    function resetAnimation(element) {
        element.style.animation = 'none';
        element.offsetHeight; // Trigger a reflow
        element.style.animation = null;
    }

    const tooltips = document.querySelectorAll('.zoom-tooltip');
    tooltips.forEach(tooltip => {
        const parent = tooltip.parentElement;
        parent.addEventListener('mouseenter', () => resetAnimation(tooltip));
        parent.addEventListener('touchstart', () => resetAnimation(tooltip));
    });

    window.addEventListener('focus', () => {
        tooltips.forEach(tooltip => resetAnimation(tooltip));
    });

});
