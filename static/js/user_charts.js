// user_charts.js - Updated with user performance functionality

document.addEventListener('DOMContentLoaded', function() {
    let userPerformanceChart = null;
    
    // Load users for dropdown
    loadUsersDropdown();
    
    // Add event listener for user selection
    const userSelect = document.getElementById('user-select-overall');
    if (userSelect) {
        userSelect.addEventListener('change', function() {
            const userId = this.value;
            if (userId) {
                loadUserPerformance(userId);
            } else {
                hideUserAnalysis();
            }
        });
    }
    
    async function loadUsersDropdown() {
        try {
            const response = await fetch('/api/users/list');
            const users = await response.json();
            
            const userSelect = document.getElementById('user-select-overall');
            if (userSelect) {
                // Clear existing options except the first one
                userSelect.innerHTML = '<option value="">-- Select a User --</option>';
                
                users.forEach(user => {
                    const option = document.createElement('option');
                    option.value = user.user_id;
                    option.textContent = user.username;
                    userSelect.appendChild(option);
                });
            }
        } catch (error) {
            console.error('Error loading users:', error);
        }
    }
    
    async function loadUserPerformance(userId) {
        try {
            const response = await fetch(`/api/users/${userId}/performance`);
            const performanceData = await response.json();
            
            if (performanceData.message) {
                // No data found
                hideUserAnalysis();
                return;
            }
            
            // Show the chart container and status summary
            document.getElementById('user-chart-container').style.display = 'block';
            document.getElementById('user-status-summary').style.display = 'block';
            document.querySelector('button[data-type="overall-user"]').style.display = 'inline-flex';
            
            // Create/update the chart
            createUserPerformanceChart(performanceData);
            
            // Update status summary
            updateStatusSummary(performanceData);
            
        } catch (error) {
            console.error('Error loading user performance:', error);
            hideUserAnalysis();
        }
    }
    
function createUserPerformanceChart(performanceData) {
    const ctx = document.getElementById('userPerformanceChart').getContext('2d');
    
    // Prepare data for chart
    const gameNames = Object.keys(performanceData);
    const averageScores = gameNames.map(game => performanceData[game].average_score);
    const completionRates = gameNames.map(game => performanceData[game].completion_rate);
    
    // Create short labels - extract just MG1, MG2, etc.
    const shortLabels = gameNames.map(name => {
        const mgMatch = name.match(/(MG\d+)/);
        return mgMatch ? mgMatch[1] : name;
    });
    
    // Destroy existing chart if it exists
    if (userPerformanceChart) {
        userPerformanceChart.destroy();
    }
    
    userPerformanceChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: shortLabels,
            datasets: [
                {
                    type: 'bar',
                    label: 'Average Score',
                    data: averageScores,
                    backgroundColor: 'rgba(54, 162, 235, 0.6)',
                    borderColor: 'rgba(54, 162, 235, 1)',
                    borderWidth: 1,
                    yAxisID: 'y'
                },
                {
                    type: 'line',
                    label: 'Completion Rate (%)',
                    data: completionRates,
                    borderColor: 'rgba(255, 99, 132, 1)',
                    backgroundColor: 'rgba(255, 99, 132, 0.2)',
                    fill: false,
                    tension: 0.1,
                    yAxisID: 'y1'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: 'User Performance Across Mini-games'
                },
                legend: {
                    display: true,
                    position: 'top'
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        title: function(context) {
                            // Show full game name in tooltip title
                            const index = context[0].dataIndex;
                            return gameNames[index];
                        },
                        afterLabel: function(context) {
                            const gameName = gameNames[context.dataIndex];
                            const gameData = performanceData[gameName];
                            return [
                                `Total Attempts: ${gameData.total_attempts}`,
                                `Completed: ${gameData.complete}`,
                                `Failed: ${gameData.fail}`,
                                `User Exit: ${gameData.userexit}`
                            ];
                        }
                    }
                }
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: 'Mini-games'
                    }
                },
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    title: {
                        display: true,
                        text: 'Average Score'
                    },
                    beginAtZero: true
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    title: {
                        display: true,
                        text: 'Completion Rate (%)'
                    },
                    beginAtZero: true,
                    max: 100,
                    grid: {
                        drawOnChartArea: false,
                    }
                }
            }
        }
    });
}
    
    function updateStatusSummary(performanceData) {
        let totalCompleted = 0;
        let totalFailed = 0;
        let totalUserExit = 0;
        
        Object.values(performanceData).forEach(gameData => {
            totalCompleted += gameData.complete;
            totalFailed += gameData.fail;
            totalUserExit += gameData.userexit;
        });
        
        document.getElementById('total-completed').textContent = totalCompleted;
        document.getElementById('total-failed').textContent = totalFailed;
        document.getElementById('total-userexit').textContent = totalUserExit;
    }
    
    function hideUserAnalysis() {
        document.getElementById('user-chart-container').style.display = 'none';
        document.getElementById('user-status-summary').style.display = 'none';
        document.querySelector('button[data-type="overall-user"]').style.display = 'none';
        
        if (userPerformanceChart) {
            userPerformanceChart.destroy();
            userPerformanceChart = null;
        }
    }
});