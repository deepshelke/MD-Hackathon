// DOM Elements
const noteIdInput = document.getElementById('noteIdInput');
const noteTextInput = document.getElementById('noteTextInput');
const testModeToggle = document.getElementById('testModeToggle');
const testModeSection = document.getElementById('testModeSection');
const simplifyBtn = document.getElementById('simplifyBtn');
const errorMessage = document.getElementById('errorMessage');
const successMessage = document.getElementById('successMessage');
const resultsSection = document.getElementById('resultsSection');
const summaryContent = document.getElementById('summaryContent');
const actionsContent = document.getElementById('actionsContent');
const medicationsContent = document.getElementById('medicationsContent');
const glossaryContent = document.getElementById('glossaryContent');
const readingLevelBadge = document.getElementById('readingLevelBadge');

// Event Listeners
simplifyBtn.addEventListener('click', handleSimplify);
noteIdInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !testModeToggle.checked) {
        handleSimplify();
    }
});
noteTextInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && e.ctrlKey && testModeToggle.checked) {
        handleSimplify();
    }
});
testModeToggle.addEventListener('change', (e) => {
    testModeSection.style.display = e.target.checked ? 'block' : 'none';
    if (e.target.checked) {
        noteIdInput.placeholder = 'Note ID not needed in test mode';
    } else {
        noteIdInput.placeholder = 'Enter Note ID from Firestore (e.g., note_001 or MIMIC_12345_d_1)';
    }
});

// Handle Simplify Button Click
async function handleSimplify() {
    const isTestMode = testModeToggle.checked;
    const noteId = noteIdInput.value.trim();
    const noteText = noteTextInput.value.trim();
    
    // Validation
    if (isTestMode) {
        if (!noteText) {
            showError('Please enter medical note text for testing');
            return;
        }
    } else {
        if (!noteId) {
            showError('Please enter a Note ID from Firestore');
            return;
        }
    }
    
    // Hide previous results and messages
    hideMessages();
    hideResults();
    
    // Show loading state
    setLoading(true);
    
    try {
        // Make API request
        const requestBody = isTestMode 
            ? { note_text: noteText }
            : { note_id: noteId };
            
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
        showError(error.message || 'An error occurred while processing the note');
    } finally {
        setLoading(false);
    }
}

// Display Results
function displayResults(data) {
    // Check if this is a fallback response (not properly formatted JSON)
    if (data._note) {
        // Show a warning that output wasn't in JSON format
        const warning = document.createElement('div');
        warning.className = 'warning-message';
        warning.innerHTML = `⚠️ ${data._note}`;
        resultsSection.insertBefore(warning, resultsSection.firstChild);
    }
    
    // Display Summary
    if (data.summary && data.summary.length > 0) {
        const summaryList = data.summary.map(item => `<li>${item}</li>`).join('');
        summaryContent.innerHTML = `<ul>${summaryList}</ul>`;
    } else if (data._raw_output) {
        // If no summary but we have raw output, show it
        summaryContent.innerHTML = `<p style="color: #3c4043; white-space: pre-wrap;">${data._raw_output}</p>`;
    } else {
        summaryContent.innerHTML = '<p style="color: #9aa0a6;">No summary available</p>';
    }
    
    // Display Actions
    if (data.actions && data.actions.length > 0) {
        const actionsHtml = data.actions.map(action => {
            const task = action.task || 'Not specified';
            const when = action.when || 'Not specified';
            const who = action.who || 'Not specified';
            return `
                <div class="action-item">
                    <strong>${task}</strong>
                    <small>When: ${when} | Who: ${who}</small>
                </div>
            `;
        }).join('');
        actionsContent.innerHTML = actionsHtml;
    } else {
        actionsContent.innerHTML = '<p style="color: #9aa0a6;">No actions specified</p>';
    }
    
    // Display Medications
    if (data.medications && data.medications.length > 0) {
        const medicationsHtml = data.medications.map(med => {
            const name = med.name || 'Not specified';
            const why = med.why || 'Not specified';
            const how = med.how_to_take || 'Not specified';
            const schedule = med.schedule || 'Not specified';
            const cautions = med.cautions && med.cautions !== 'Not specified' 
                ? `<p class="caution"><strong>⚠️ Cautions:</strong> ${med.cautions}</p>` 
                : '';
            return `
                <div class="medication-item">
                    <h4>${name}</h4>
                    <p><strong>Why:</strong> ${why}</p>
                    <p><strong>How to take:</strong> ${how}</p>
                    <p><strong>Schedule:</strong> ${schedule}</p>
                    ${cautions}
                </div>
            `;
        }).join('');
        medicationsContent.innerHTML = medicationsHtml;
    } else {
        medicationsContent.innerHTML = '<p style="color: #9aa0a6;">No medications listed</p>';
    }
    
    // Display Glossary
    if (data.glossary && data.glossary.length > 0) {
        const glossaryHtml = data.glossary.map(term => {
            const termName = term.term || 'Not specified';
            const plain = term.plain || 'Not specified';
            return `
                <div class="glossary-item">
                    <strong>${termName}</strong>
                    <p>${plain}</p>
                </div>
            `;
        }).join('');
        glossaryContent.innerHTML = glossaryHtml;
    } else {
        glossaryContent.innerHTML = '<p style="color: #9aa0a6;">No glossary terms available</p>';
    }
    
    // Display Reading Level
    if (data.readability_grade) {
        readingLevelBadge.textContent = `📊 Reading Level: Grade ${data.readability_grade}`;
        readingLevelBadge.style.display = 'inline-block';
    } else {
        readingLevelBadge.style.display = 'none';
    }
    
    // Show results section
    resultsSection.style.display = 'block';
    
    // Scroll to results
    resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
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

