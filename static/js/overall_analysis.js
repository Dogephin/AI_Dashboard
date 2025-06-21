document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.analyze-btn').forEach(button => {
    button.addEventListener('click', () => generateAnalysis(button));
  });
});
  
function generateAnalysis(button) {
    const type = button.getAttribute('data-type');
    const modalBody = document.getElementById('ai-analysis-content');

    // Set modal loading UI
    modalBody.innerHTML = `
      <div id="ai-loading" class="d-flex align-items-center justify-content-center flex-column py-4">
        <div class="spinner-border text-primary" role="status" style="width: 3rem; height: 3rem;">
          <span class="visually-hidden">Loading...</span>
        </div>
        <div class="mt-3">Analyzing ${type.replace(/-/g, ' ')}... please wait.</div>
      </div>
    `;

    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('aiAnalysisModal'));
    modal.show();

    // Fetch analysis from the backend
    fetch(`/api/analysis/${type}`)
      .then(res => res.json())
      .then(data => {
        // Handle API error shape
        if (data.text && typeof data.text === 'string') {
          modalBody.innerHTML = `<p>${data.text}</p>`;
          return;
        }

        // If it's the parsed insight format:
        if (Array.isArray(data)) {
          let html = '';
          data.forEach(insight => {
            html += `
              <div class="mb-3">
                <h3><strong>${insight.title}</strong></h3>
                <p>${insight.content.replace(/\n/g, '<br>')}</p>
              </div>
              <hr>
            `;
          });
          modalBody.innerHTML = html;
        } else {
          modalBody.innerHTML = `<p>Unexpected response format.</p>`;
        }
      })
      .catch(err => {
        modalBody.innerHTML = `
          <div class="alert alert-danger" role="alert">
            Error: ${err.message}
          </div>
        `;
      });
  }