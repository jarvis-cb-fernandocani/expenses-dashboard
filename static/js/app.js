/* Expenses Dashboard - Utility Functions */

// Format currency
function formatCurrency(amount) {
    if (amount === null || amount === undefined) return '€0.00';
    const absAmount = Math.abs(amount);
    const formatted = absAmount.toLocaleString('pt-PT', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
    return amount < 0 ? `-€${formatted}` : `€${formatted}`;
}

// Format number without currency
function formatNumber(num) {
    if (num === null || num === undefined) return '0.00';
    return num.toLocaleString('pt-PT', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Show notification
function showNotification(message, type = 'info') {
    // Simple notification - can be enhanced
    console.log(`[${type.toUpperCase()}] ${message}`);
}

// Debounce function
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// API helper
async function apiGet(url, params = {}) {
    const urlParams = new URLSearchParams(params);
    const response = await fetch(`${url}?${urlParams}`);
    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
}

async function apiPost(url, data) {
    const response = await fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
    });
    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
}
