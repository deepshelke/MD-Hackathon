// DOM Elements
const noteIdInput = document.getElementById('noteIdInput');
const hadmIdInput = document.getElementById('hadmIdInput');
const simplifyBtn = document.getElementById('simplifyBtn');
const errorMessage = document.getElementById('errorMessage');
const successMessage = document.getElementById('successMessage');
const resultsSection = document.getElementById('resultsSection');
const outputContent = document.getElementById('outputContent');

// Event Listeners
simplifyBtn.addEventListener('click', handleSimplify);
noteIdInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        handleSimplify();
    }
});
hadmIdInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        handleSimplify();
    }
});

// Handle Simplify Button Click
async function handleSimplify() {
    const noteId = noteIdInput.value.trim();
    const hadmId = hadmIdInput.value.trim();
    
    // Validation
    if (!noteId || !hadmId) {
        showError('Please enter both Note ID and HADM ID');
        return;
    }
    
    // Hide previous results and messages
    hideMessages();
    hideResults();
    
    // Show loading state
    setLoading(true);
    
    try {
        // Make API request
        const requestBody = { 
            note_id: noteId,
            hadm_id: hadmId
        };
            
        const response = await fetch('/api/simplify', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestBody)
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Failed to simplify note');
        }
        
        if (data.success && data.data) {
            // Show success message
            showSuccess();
            
            // Display results
            displayResults(data.data);
        } else {
            throw new Error('Invalid response from server');
        }
        
    } catch (error) {
        // Handle network errors
        if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
            showError('Network error: Could not connect to server. Please check if the server is running.');
        } else {
            showError(error.message || 'An error occurred while processing the note');
        }
    } finally {
        setLoading(false);
    }
}

// Display Results - Parse plain text output and format nicely
function displayResults(data) {
    let output = '';
    
    // Check if we have simplified_output (plain text from model)
    if (data.simplified_output) {
        output = formatPlainTextOutput(data.simplified_output);
    } else if (data._raw_output) {
        // Fallback to raw output
        output = formatPlainTextOutput(data._raw_output);
    } else if (data.summary || data.actions || data.medications || data.glossary) {
        // If we have structured data, format it
        output = formatStructuredOutput(data);
    } else {
        output = '<p style="color: #9aa0a6;">No output available</p>';
    }
    
    outputContent.innerHTML = output;
    
    // Show results section
    resultsSection.style.display = 'block';
    
    // Scroll to results
    resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// Format plain text output from model
function formatPlainTextOutput(text) {
    // Remove any truncation markers or incomplete text
    if (text.includes('...') && text.length > 5000) {
        // Check if text appears to be cut off mid-sentence
        const lastSentence = text.substring(text.length - 100);
        if (!lastSentence.match(/[.!?]$/)) {
            // Text might be truncated - try to find last complete section
            const sections = text.split(/\n(?=[📋✅💊⚠️📖])/);
            if (sections.length > 1) {
                // Keep all complete sections
                text = sections.slice(0, -1).join('\n');
            }
        }
    }
    
    let html = '';
    const lines = text.split('\n');
    let inList = false;
    let inSubList = false;
    let skipIntro = true; // Skip intro line like "Here is the simplified version..."
    let currentSection = '';
    let sectionCount = 0;
    
    for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();
        
        if (!line) {
            if (inSubList) {
                html += '</ul>';
                inSubList = false;
            }
            if (inList) {
                html += '</ul>';
                inList = false;
            }
            continue;
        }
        
        // Skip intro lines (common patterns)
        if (skipIntro && (
            line.toLowerCase().includes('here is the simplified') ||
            line.toLowerCase().includes('simplified version') ||
            line.toLowerCase().includes('medical discharge note')
        )) {
            continue; // Skip intro line
        }
        skipIntro = false; // After first non-intro line, stop skipping
        
        // Check if this is a main section header (starts with emoji or is a section title)
        // Also check if line starts with section title followed by colon (e.g., "Summary: content")
        const isSectionHeader = line.match(/^[📋✅💊⚠️📖]/) || 
                                 (line.match(/^(Summary|Actions Needed|Medications Explained|Safety Information|Glossary):?\s*/i) && (line.length < 50 || line.match(/^(Summary|Actions Needed|Medications Explained|Safety Information|Glossary):\s*/i)));
        
        if (isSectionHeader) {
            if (inSubList) {
                html += '</ul>';
                inSubList = false;
            }
            if (inList) {
                html += '</ul>';
                inList = false;
            }
            // Close previous section if exists
            if (sectionCount > 0) {
                html += '</div></div>'; // Close section-content and section-wrapper
            }
            // Extract section title and content
            let sectionTitle = line.replace(/^[📋✅💊⚠️📖]\s*/, '').trim();
            let sectionContent = '';
            
            // If line has content after colon (e.g., "Summary: content here")
            if (sectionTitle.includes(':')) {
                const parts = sectionTitle.split(':', 2);
                sectionTitle = parts[0].trim();
                sectionContent = parts[1] ? parts[1].trim() : '';
            } else {
                sectionTitle = sectionTitle.replace(':', '').trim();
            }
            
            sectionCount++;
            const sectionId = `section-${sectionCount}`;
            html += `<div class="section-wrapper" id="${sectionId}">`;
            html += `<h2 class="section-header">${formatSectionTitle(sectionTitle)}</h2>`;
            html += `<div class="section-content">`;
            
            // If there's content on the same line, add it
            if (sectionContent) {
                html += `<p>${escapeHtml(sectionContent)}</p>`;
            }
            
            currentSection = sectionTitle.toLowerCase();
        }
        // Check if this is a subsection header (like "Wound Care:", "Activity Restrictions:")
        else if (line.endsWith(':') && !line.startsWith('-') && !line.startsWith('•') && line.length < 50 && !line.match(/^[📋✅💊⚠️📖]/)) {
            if (inSubList) {
                html += '</ul>';
                inSubList = false;
            }
            if (inList) {
                html += '</ul>';
                inList = false;
            }
            const subsectionTitle = line.slice(0, -1).trim();
            html += `<h3>${escapeHtml(subsectionTitle)}</h3>`;
        }
        // Check if this is a numbered medication item (starts with number and period)
        else if (line.match(/^\d+\.\s+/)) {
            if (inSubList) {
                html += '</ul>';
                inSubList = false;
            }
            if (inList) {
                html += '</ul>';
                inList = false;
            }
            const content = line.replace(/^\d+\.\s+/, '').trim();
            html += `<div class="medication-item"><h4>${escapeHtml(content)}</h4>`;
            // Next lines might be sub-bullets for this medication
            inSubList = true;
            html += '<ul>';
        }
        // Check if this is a bullet point (starts with - or •)
        else if (line.startsWith('- ') || line.startsWith('• ')) {
            if (!inList && !inSubList) {
                html += '<ul>';
                inList = true;
            }
            const content = line.replace(/^[-•]\s+/, '').trim();
            html += `<li>${escapeHtml(content)}</li>`;
        }
        // Regular paragraph
        else {
            if (inSubList) {
                html += '</ul></div>';
                inSubList = false;
            }
            if (inList) {
                html += '</ul>';
                inList = false;
            }
            html += `<p>${escapeHtml(line)}</p>`;
        }
    }
    
    if (inSubList) {
        html += '</ul></div>';
    }
    if (inList) {
        html += '</ul>';
    }
    
    // Close the last section if exists
    if (sectionCount > 0) {
        html += '</div></div>'; // Close section-content and section-wrapper
    }
    
    return html;
}

// Format structured output (JSON format)
function formatStructuredOutput(data) {
    let html = '';
    
    if (data.summary && data.summary.length > 0) {
        html += '<h2>📋 Summary</h2><ul>';
        data.summary.forEach(item => {
            html += `<li>${escapeHtml(item)}</li>`;
        });
        html += '</ul>';
    }
    
    if (data.actions && data.actions.length > 0) {
        html += '<h2>✅ Actions Needed</h2><ul>';
        data.actions.forEach(action => {
            const task = action.task || 'Not specified';
            const when = action.when || 'Not specified';
            const who = action.who || 'Not specified';
            html += `<li><strong>${escapeHtml(task)}</strong> - When: ${escapeHtml(when)} | Who: ${escapeHtml(who)}</li>`;
        });
        html += '</ul>';
    }
    
    if (data.medications && data.medications.length > 0) {
        html += '<h2>💊 Medications Explained</h2><ul>';
        data.medications.forEach(med => {
            const name = med.name || 'Not specified';
            const why = med.why || 'Not specified';
            const how = med.how_to_take || 'Not specified';
            html += `<li><strong>${escapeHtml(name)}</strong>: ${escapeHtml(why)}. ${escapeHtml(how)}</li>`;
        });
        html += '</ul>';
    }
    
    if (data.glossary && data.glossary.length > 0) {
        html += '<h2>📖 Glossary</h2><ul>';
        data.glossary.forEach(term => {
            const termName = term.term || 'Not specified';
            const plain = term.plain || 'Not specified';
            html += `<li><strong>${escapeHtml(termName)}</strong>: ${escapeHtml(plain)}</li>`;
        });
        html += '</ul>';
    }
    
    return html;
}

// Format section titles with emojis
function formatSectionTitle(title) {
    // If title already has an emoji, preserve it
    if (title.match(/^[📋✅💊⚠️📖]/)) {
        return title;
    }
    
    const titleLower = title.toLowerCase();
    if (titleLower.includes('summary')) return '📋 Summary';
    if (titleLower.includes('action')) return '✅ Actions Needed';
    if (titleLower.includes('medication')) return '💊 Medications Explained';
    if (titleLower.includes('safety')) return '⚠️ Safety Information';
    if (titleLower.includes('glossary') || titleLower.includes('term')) return '📖 Glossary';
    return title;
}

// Escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Utility Functions
function setLoading(loading) {
    simplifyBtn.disabled = loading;
    const btnText = simplifyBtn.querySelector('.btn-text');
    const btnLoader = simplifyBtn.querySelector('.btn-loader');
    
    if (loading) {
        btnText.style.display = 'none';
        btnLoader.style.display = 'flex';
    } else {
        btnText.style.display = 'block';
        btnLoader.style.display = 'none';
    }
}

function showError(message) {
    errorMessage.textContent = `❌ ${message}`;
    errorMessage.style.display = 'flex';
    errorMessage.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

function showSuccess() {
    successMessage.style.display = 'flex';
    setTimeout(() => {
        successMessage.style.display = 'none';
    }, 3000);
}

function hideMessages() {
    errorMessage.style.display = 'none';
    successMessage.style.display = 'none';
}

function hideResults() {
    resultsSection.style.display = 'none';
}
