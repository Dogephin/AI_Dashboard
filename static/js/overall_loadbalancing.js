// Average Scores Analysis
fetch('/api/analysis/avg-scores')
.then(res => res.json())
.then(data => {
    document.getElementById('avg-scores-analysis').innerText = data.text;
});

// Error Frequency
fetch('/api/analysis/error-frequency')
.then(res => res.json())
.then(data => {
    document.getElementById('error-frequency-analysis').innerText = data.text;
});

// Duration vs Performance
fetch('/api/analysis/performance-duration')
.then(res => res.json())
.then(data => {
    document.getElementById('duration-analysis').innerText = data.text;
});

// Overall User
fetch('/api/analysis/overall-user')
.then(res => res.json())
.then(data => {
    document.getElementById('overall-user-analysis').innerText = data.text;
});