// Main JavaScript functionality

console.log('Google Dorking Tool - Loaded');

// Utility function to make API calls
async function apiCall(endpoint, method = 'GET', data = null) {
    const options = {
        method: method,
        headers: {
            'Content-Type': 'application/json',
        }
    };

    if (data) {
        options.body = JSON.stringify(data);
    }

    try {
        const response = await fetch(endpoint, options);
        return await response.json();
    } catch (error) {
        console.error('API Call Error:', error);
        throw error;
    }
}

// Format domain name
function formatDomain(domain) {
    return domain.toLowerCase().replace(/^(https?:\/\/)|(\/.*)/g, '');
}

// Show notification
function showNotification(message, type = 'info') {
    const alertClass = {
        'success': 'alert-success',
        'error': 'alert-danger',
        'warning': 'alert-warning',
        'info': 'alert-info'
    }[type] || 'alert-info';

    const alertHtml = `
        <div class="alert ${alertClass} alert-dismissible fade show" role="alert">
            <i class="fas fa-info-circle"></i> ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;

    const container = document.getElementById('notificationContainer') || createNotificationContainer();
    const alertDiv = document.createElement('div');
    alertDiv.innerHTML = alertHtml;
    container.appendChild(alertDiv.firstElementChild);

    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        document.querySelector('.alert')?.remove();
    }, 5000);
}

// Create notification container
function createNotificationContainer() {
    const container = document.createElement('div');
    container.id = 'notificationContainer';
    container.style.position = 'fixed';
    container.style.top = '80px';
    container.style.right = '20px';
    container.style.zIndex = '1000';
    container.style.maxWidth = '400px';
    document.body.appendChild(container);
    return container;
}

// Format date
function formatDate(isoString) {
    const date = new Date(isoString);
    return date.toLocaleString();
}

// Format query string for display
function formatQuery(query) {
    if (query.length > 80) {
        return query.substring(0, 77) + '...';
    }
    return query;
}

// Export functionality
function downloadFile(content, filename, type = 'text/plain') {
    const blob = new Blob([content], { type: type });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
}

// Copy to clipboard
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showNotification('Copied to clipboard!', 'success');
    }).catch(err => {
        console.error('Failed to copy:', err);
        showNotification('Failed to copy to clipboard', 'error');
    });
}

// Validate domain
function isValidDomain(domain) {
    const domainRegex = /^([a-z0-9]([a-z0-9-]*[a-z0-9])?\.)+[a-z]{2,}$/i;
    return domainRegex.test(domain) || domain.includes('*');
}
