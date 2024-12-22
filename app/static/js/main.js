document.getElementById('analyzeForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const githubUrl = document.getElementById('githubUrl').value;
    const language = document.getElementById('language').value;
    
    // Show progress and hide other sections
    document.getElementById('progress').classList.remove('hidden');
    document.getElementById('results').classList.add('hidden');
    document.getElementById('error').classList.add('hidden');
    
    try {
        const response = await fetch('/api/analyze', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ url: githubUrl, language: language })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Failed to analyze repository');
        }
        
        // Update repository info
        const repoInfo = document.getElementById('repoInfo');
        repoInfo.innerHTML = `
            <div>
                <span class="font-medium">Name:</span> ${data.repo_data.name}
            </div>
            <div>
                <span class="font-medium">Stars:</span> ${data.repo_data.stars}
            </div>
            <div>
                <span class="font-medium">Description:</span> ${data.repo_data.description || 'No description'}
            </div>
            <div>
                <span class="font-medium">Forks:</span> ${data.repo_data.forks}
            </div>
            <div class="col-span-2">
                <span class="font-medium">Languages:</span> ${Object.keys(data.repo_data.languages).join(', ')}
            </div>
        `;
        
        // Update analysis
        document.getElementById('analysis').innerHTML = data.analysis_html;
        
        // Store the raw markdown and language for export
        document.getElementById('analysis').setAttribute('data-markdown', data.analysis);
        document.getElementById('analysis').setAttribute('data-language', data.language);
        
        // Show results
        document.getElementById('results').classList.remove('hidden');
    } catch (error) {
        const errorElement = document.getElementById('error');
        errorElement.textContent = error.message;
        errorElement.classList.remove('hidden');
    } finally {
        document.getElementById('progress').classList.add('hidden');
    }
});

async function exportAnalysis(format) {
    // Get the raw markdown content and language
    const analysis = document.getElementById('analysis').getAttribute('data-markdown');
    const language = document.getElementById('analysis').getAttribute('data-language');
    
    try {
        const response = await fetch('/api/export', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ analysis, format, language })
        });
        
        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.error || 'Export failed');
        }
        
        if (format === 'markdown') {
            const data = await response.json();
            downloadFile(data.content, data.filename, 'text/markdown');
        } else if (format === 'pdf') {
            // For PDF, we need to handle the blob directly
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            
            // Get the filename from Content-Disposition header
            const contentDisposition = response.headers.get('Content-Disposition');
            const filenameMatch = contentDisposition && contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
            const filename = filenameMatch && filenameMatch[1] ? decodeURIComponent(filenameMatch[1].replace(/['"]/g, '')) : 'repository_analysis.pdf';
            
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
        }
    } catch (error) {
        const errorElement = document.getElementById('error');
        errorElement.textContent = error.message;
        errorElement.classList.remove('hidden');
    }
}

function downloadFile(content, filename, contentType) {
    const blob = new Blob([content], { type: contentType });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
}
