/* Email Settings Module - Email configuration functionality */

const AdminEmail = {
    // Load email settings
    async loadEmailSettings() {
        try {
            const response = await AdminAPI.email.getSettings();

            if (response.ok) {
                const settings = await response.json();
                document.getElementById('sendgrid-api-key').value = settings.sendgrid_api_key || '';
                document.getElementById('from-email').value = settings.from_email || '';
                document.getElementById('from-name').value = settings.from_name || '';
                document.getElementById('booking-confirmation-enabled').checked = settings.booking_confirmation_enabled || false;
                // Static reports functionality has been removed - only dynamic reports remain
                // document.getElementById('reports-enabled').checked = settings.reports_enabled || false;
                // document.getElementById('report-recipients').value = (settings.report_recipients || []).join(', ');
            } else {
                AdminNotifications.showError('Failed to load email settings');
            }
        } catch (error) {
            AdminNotifications.handleApiError(error, 'Error loading email settings');
        }
    },

    // Handle email settings form submission
    async handleEmailSettingsSubmit(event) {
        event.preventDefault();
        
        try {
            const recipients = document.getElementById('report-recipients').value
                .split(',')
                .map(email => email.trim())
                .filter(email => email.length > 0);

            const data = {
                sendgrid_api_key: document.getElementById('sendgrid-api-key').value,
                from_email: document.getElementById('from-email').value,
                from_name: document.getElementById('from-name').value,
                booking_confirmation_enabled: document.getElementById('booking-confirmation-enabled').checked,
                reports_enabled: document.getElementById('reports-enabled').checked,
                report_recipients: recipients
            };

            const response = await AdminAPI.email.updateSettings(data);

            if (response.ok) {
                AdminNotifications.showSuccess('Email settings saved successfully');
            } else {
                AdminNotifications.showError('Failed to save email settings');
            }
        } catch (error) {
            AdminNotifications.handleApiError(error, 'Error saving email settings');
        }
    },

    // Test email configuration
    async testEmailConfig() {
        try {
            const response = await AdminAPI.email.testConfig();

            if (response.ok) {
                const result = await response.json();
                AdminNotifications.showSuccess(result.message);
            } else {
                const error = await response.json();
                AdminNotifications.showError(error.detail);
            }
        } catch (error) {
            AdminNotifications.handleApiError(error, 'Error testing email configuration');
        }
    },

    // Initialize email settings module
    init() {
        // Setup form event listeners
        const emailForm = document.getElementById('email-settings-form');
        if (emailForm) {
            emailForm.addEventListener('submit', this.handleEmailSettingsSubmit.bind(this));
        }

        console.log('Email settings module initialized');
    }
};

// Export for global access
window.AdminEmail = AdminEmail;

// Initialize when module loads
AdminEmail.init();

console.log('Admin email settings module loaded!');
