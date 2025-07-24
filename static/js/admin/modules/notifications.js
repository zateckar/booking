/* Notifications Module - Toast notifications for admin interface */

const AdminNotifications = {
    // Initialize notification system
    init() {
        this.createNotificationContainer();
        console.log('Admin notifications module initialized');
    },

    // Create notification container if it doesn't exist
    createNotificationContainer() {
        let container = document.getElementById('admin-notifications-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'admin-notifications-container';
            container.className = 'position-fixed top-0 end-0 p-3';
            container.style.zIndex = '9999';
            document.body.appendChild(container);
        }
    },

    // Show success notification
    showSuccess(message, title = 'Success') {
        this.showNotification(message, 'success', title);
    },

    // Show error notification
    showError(message, title = 'Error') {
        this.showNotification(message, 'danger', title);
    },

    // Show warning notification
    showWarning(message, title = 'Warning') {
        this.showNotification(message, 'warning', title);
    },

    // Show info notification
    showInfo(message, title = 'Info') {
        this.showNotification(message, 'info', title);
    },

    // Show generic notification
    showNotification(message, type = 'info', title = '', duration = 5000) {
        this.createNotificationContainer();
        
        const id = 'toast-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
        const container = document.getElementById('admin-notifications-container');
        
        const toast = document.createElement('div');
        toast.id = id;
        toast.className = `toast show align-items-center text-bg-${type} border-0`;
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'assertive');
        toast.setAttribute('aria-atomic', 'true');
        
        const iconMap = {
            success: '✓',
            danger: '✗',
            warning: '!',
            info: 'i'
        };
        
        const icon = iconMap[type] || 'i';
        
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    <div class="d-flex align-items-center">
                        <span class="me-2" style="font-size: 1.1em;">${icon}</span>
                        <div class="flex-grow-1">
                            ${title ? `<strong>${title}</strong><br>` : ''}
                            ${message}
                        </div>
                    </div>
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        `;
        
        container.appendChild(toast);
        
        // Auto-remove after duration
        if (duration > 0) {
            setTimeout(() => {
                this.removeNotification(id);
            }, duration);
        }
        
        // Add click handler to close button
        const closeBtn = toast.querySelector('.btn-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                this.removeNotification(id);
            });
        }
    },

    // Remove notification by ID
    removeNotification(id) {
        const toast = document.getElementById(id);
        if (toast) {
            toast.classList.add('fade');
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 300);
        }
    },

    // Clear all notifications
    clearAll() {
        const container = document.getElementById('admin-notifications-container');
        if (container) {
            container.innerHTML = '';
        }
    },

    // Handle API errors with detailed error information
    handleApiError(error, context = 'API Error') {
        console.error(`${context}:`, error);
        
        let message = 'An unexpected error occurred';
        
        if (error instanceof Error) {
            message = error.message;
        } else if (typeof error === 'string') {
            message = error;
        } else if (error && error.detail) {
            message = error.detail;
        } else if (error && error.message) {
            message = error.message;
        }
        
        this.showError(message, context);
    },

    // Show loading notification (returns ID for manual removal)
    showLoading(message = 'Loading...', title = '') {
        this.createNotificationContainer();
        
        const id = 'loading-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
        const container = document.getElementById('admin-notifications-container');
        
        const toast = document.createElement('div');
        toast.id = id;
        toast.className = 'toast show align-items-center text-bg-primary border-0';
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'assertive');
        toast.setAttribute('aria-atomic', 'true');
        
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    <div class="d-flex align-items-center">
                        <div class="spinner-border spinner-border-sm text-light me-2" role="status">
                            <span class="visually-hidden">Loading...</span>
                        </div>
                        <div class="flex-grow-1">
                            ${title ? `<strong>${title}</strong><br>` : ''}
                            ${message}
                        </div>
                    </div>
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        `;
        
        container.appendChild(toast);
        
        // Add click handler to close button
        const closeBtn = toast.querySelector('.btn-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                this.removeNotification(id);
            });
        }
        
        return id;
    },

    // Show confirmation dialog (returns Promise)
    showConfirmation(message, title = 'Confirm Action', confirmText = 'Confirm', cancelText = 'Cancel') {
        return new Promise((resolve) => {
            const id = 'confirm-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
            this.createNotificationContainer();
            const container = document.getElementById('admin-notifications-container');
            
            const toast = document.createElement('div');
            toast.id = id;
            toast.className = 'toast show align-items-center text-bg-warning border-0';
            toast.setAttribute('role', 'alert');
            toast.setAttribute('aria-live', 'assertive');
            toast.setAttribute('aria-atomic', 'true');
            
            toast.innerHTML = `
                <div class="toast-body">
                    <div class="mb-2">
                        <strong>${title}</strong><br>
                        ${message}
                    </div>
                    <div class="d-flex gap-2">
                        <button type="button" class="btn btn-sm btn-danger" id="${id}-confirm">${confirmText}</button>
                        <button type="button" class="btn btn-sm btn-secondary" id="${id}-cancel">${cancelText}</button>
                    </div>
                </div>
            `;
            
            container.appendChild(toast);
            
            // Add event handlers
            const confirmBtn = document.getElementById(`${id}-confirm`);
            const cancelBtn = document.getElementById(`${id}-cancel`);
            
            confirmBtn.addEventListener('click', () => {
                this.removeNotification(id);
                resolve(true);
            });
            
            cancelBtn.addEventListener('click', () => {
                this.removeNotification(id);
                resolve(false);
            });
            
            // Auto-cancel after 30 seconds
            setTimeout(() => {
                this.removeNotification(id);
                resolve(false);
            }, 30000);
        });
    },

    // Ensure initialization (called by admin-main.js)
    ensureInitialized() {
        if (!document.getElementById('admin-notifications-container')) {
            this.init();
        }
    },

    // Alias for backward compatibility
    confirm(message, title = 'Confirm Action', confirmText = 'Confirm', cancelText = 'Cancel') {
        return this.showConfirmation(message, title, confirmText, cancelText);
    },

    // Show prompt dialog (returns Promise with user input or null if cancelled)
    prompt(message, defaultValue = '', title = 'Input Required') {
        return new Promise((resolve) => {
            const id = 'prompt-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
            this.createNotificationContainer();
            const container = document.getElementById('admin-notifications-container');
            
            const toast = document.createElement('div');
            toast.id = id;
            toast.className = 'toast show align-items-center text-bg-info border-0';
            toast.setAttribute('role', 'alert');
            toast.setAttribute('aria-live', 'assertive');
            toast.setAttribute('aria-atomic', 'true');
            
            toast.innerHTML = `
                <div class="toast-body">
                    <div class="mb-2">
                        <strong>${title}</strong><br>
                        ${message}
                    </div>
                    <div class="mb-2">
                        <input type="text" class="form-control form-control-sm" id="${id}-input" value="${defaultValue}" placeholder="Enter value...">
                    </div>
                    <div class="d-flex gap-2">
                        <button type="button" class="btn btn-sm btn-primary" id="${id}-confirm">OK</button>
                        <button type="button" class="btn btn-sm btn-secondary" id="${id}-cancel">Cancel</button>
                    </div>
                </div>
            `;
            
            container.appendChild(toast);
            
            const input = document.getElementById(`${id}-input`);
            const confirmBtn = document.getElementById(`${id}-confirm`);
            const cancelBtn = document.getElementById(`${id}-cancel`);
            
            // Focus on input
            setTimeout(() => input.focus(), 100);
            
            // Handle Enter key in input
            input.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    const value = input.value.trim();
                    this.removeNotification(id);
                    resolve(value || null);
                }
            });
            
            // Handle Escape key
            input.addEventListener('keydown', (e) => {
                if (e.key === 'Escape') {
                    this.removeNotification(id);
                    resolve(null);
                }
            });
            
            confirmBtn.addEventListener('click', () => {
                const value = input.value.trim();
                this.removeNotification(id);
                resolve(value || null);
            });
            
            cancelBtn.addEventListener('click', () => {
                this.removeNotification(id);
                resolve(null);
            });
            
            // Auto-cancel after 60 seconds
            setTimeout(() => {
                this.removeNotification(id);
                resolve(null);
            }, 60000);
        });
    }
};

// Export for global access
window.AdminNotifications = AdminNotifications;

// Initialize immediately
AdminNotifications.init();

console.log('Admin notifications module loaded!');
