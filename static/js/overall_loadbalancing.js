function cleanInsightContent(text) {
  return text
    .split('\n')
    .map(line => line.trim())
    .filter(line => line.length > 0)
    .map(line => `<div class="insight-line">${line}</div>`)
    .join('');
}

// Average Score Analysis
fetch('/api/analysis/avg-scores')
  .then(res => res.json())
  .then(data => {
    
    const container = document.getElementById('avg-scores-analysis');
    container.innerHTML = ''; // clear loading text

    data.forEach(item => {
        const cleanedTitle = item.title.trim();
      const cleanedContent = cleanInsightContent(item.content.trim());
      const cardHTML = `<div class="insight-card"><h3>${cleanedTitle}</h3><p>${cleanedContent}</p></div>`;
      container.innerHTML += cardHTML;
    });
  });

// Error Frequency
fetch('/api/analysis/error-frequency')
.then(res => res.json())
.then(data => {

    const container = document.getElementById('error-frequency-analysis');
    container.innerHTML = ''; // clear loading text

    data.forEach(item => {
        const cleanedTitle = item.title.trim();
      const cleanedContent = cleanInsightContent(item.content.trim());
      const cardHTML = `<div class="insight-card"><h3>${cleanedTitle}</h3><p>${cleanedContent}</p></div>`;
      container.innerHTML += cardHTML;
    });
});

// Duration vs Performance
fetch('/api/analysis/performance-duration')
.then(res => res.json())
.then(data => {
    const container = document.getElementById('duration-analysis');
    container.innerHTML = ''; 

    data.forEach(item => {
        const cleanedTitle = item.title.trim();
      const cleanedContent = cleanInsightContent(item.content.trim());
      const cardHTML = `<div class="insight-card"><h3>${cleanedTitle}</h3><p>${cleanedContent}</p></div>`;
      container.innerHTML += cardHTML;
    });
});

// Overall User
fetch('/api/analysis/overall-user')
.then(res => res.json())
.then(data => {
    const container = document.getElementById('overall-user-analysis');
    container.innerHTML = ''; 

    data.forEach(item => {
        const cleanedTitle = item.title.trim();
      const cleanedContent = cleanInsightContent(item.content.trim());
      const cardHTML = `<div class="insight-card"><h3>${cleanedTitle}</h3><p>${cleanedContent}</p></div>`;
      container.innerHTML += cardHTML;
    });
});