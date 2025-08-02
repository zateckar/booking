/**
 * Shared Styles for Admin Components
 * 
 * Since we're now using pure Bootstrap components without shadow DOM,
 * this file contains minimal shared utilities and constants.
 */
const AdminSharedStyles = {
    // Color constants for consistency
    colors: {
        primary: '#007bff',
        secondary: '#6c757d',
        success: '#28a745',
        danger: '#dc3545',
        warning: '#ffc107',
        info: '#17a2b8',
        light: '#f8f9fa',
        dark: '#343a40'
    },

    // Common CSS classes that might be needed
    getUtilityClasses: () => ({
        loadingOverlay: 'position-absolute top-0 start-0 w-100 h-100 d-none',
        loadingOverlayBg: 'background: rgba(255,255,255,0.8); z-index: 10;',
        centeredSpinner: 'd-flex justify-content-center align-items-center h-100'
    }),

    // Legacy method for backward compatibility (returns empty since we don't use shadow DOM anymore)
    getSharedStyles: () => '',

    // Utility method to create consistent loading overlays
    createLoadingOverlay: (spinnerColor = 'primary') => `
        <div class="position-absolute top-0 start-0 w-100 h-100 d-none" 
             style="background: rgba(255,255,255,0.8); z-index: 10;">
            <div class="d-flex justify-content-center align-items-center h-100">
                <div class="spinner-border text-${spinnerColor}" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
            </div>
        </div>
    `,

    // Utility method to create consistent alert messages
    createAlert: (message, type = 'info', dismissible = true) => {
        const dismissibleClass = dismissible ? 'alert-dismissible' : '';
        const dismissButton = dismissible ? 
            '<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>' : '';
        
        return `
            <div class="alert alert-${type} ${dismissibleClass} fade show" role="alert">
                ${message}
                ${dismissButton}
            </div>
        `;
    },

    // Utility method for consistent card headers
    createCardHeader: (title, icon, headerColor = 'primary', actions = '') => `
        <div class="card-header bg-${headerColor} text-white d-flex justify-content-between align-items-center">
            <h5 class="card-title mb-0">
                <i class="${icon} me-2"></i>${title}
            </h5>
            ${actions}
        </div>
    `,

    // Common button group patterns
    getActionButtonGroup: (buttons = []) => {
        const buttonHtml = buttons.map(btn => 
            `<button class="btn ${btn.class} btn-sm" id="${btn.id}" title="${btn.title || ''}">
                <i class="${btn.icon} me-1"></i>${btn.text}
             </button>`
        ).join('');
        
        return `<div class="btn-group" role="group">${buttonHtml}</div>`;
    }
};

// Make it globally available for backward compatibility
window.AdminSharedStyles = AdminSharedStyles;

// Export for modern usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AdminSharedStyles;
}
