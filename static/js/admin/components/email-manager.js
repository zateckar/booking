/**
 * Email Manager Web Component - Bootstrap UI
 * Modern, clean interface for email configuration
 */
class EmailManager extends HTMLElement {
    constructor() {
        super();
        this.emailSettings = {};
    }

    connectedCallback() {
        console.log('📧 EmailManager connected to DOM');
        this.render();
        this.setupEventListeners();
        this.loadEmailData();
    }

    render() {
        this.innerHTML = `
            <div class="card shadow-sm">
                <div class="card-header bg-info text-white d-flex justify-content-between align-items-center">
                    <h5 class="card-title mb-0">
                        Email Configuration
                    </h5>
                    <div class="btn-group" role="group">
                        <button class="btn btn-success btn-sm" id="test-email-btn" title="Send Test Email">
                            Test
                        </button>
                        <button class="btn btn-light btn-sm" id="refresh-btn" title="Refresh">
                            Refresh
                        </button>
                    </div>
                </div>
                
                <div class="card-body">
                    <!-- Email Service Status -->
                    <div class="alert alert-light border d-flex align-items-center mb-4" role="alert">
                        <i class="fas fa-info-circle text-info me-2"></i>
                        <div class="flex-grow-1">
                            <strong>Email Service Provider:</strong> SendGrid
                            <div class="small text-muted">Configure your SendGrid settings below to enable email notifications.</div>
                        </div>
                        <div id="email-status" class="badge bg-secondary">Not configured</div>
                    </div>

                    <!-- Configuration Form -->
                    <form id="email-form">
                        <div class="row g-3">
                            <!-- SendGrid Configuration -->
                            <div class="col-12">
                                <h6 class="border-bottom pb-2 mb-3">
                                    <i class="fas fa-cog me-1"></i>SendGrid Configuration
                                </h6>
                            </div>

                            <div class="col-12">
                                <label for="sendgrid-api-key" class="form-label">
                                    <i class="fas fa-key me-1"></i>SendGrid API Key
                                </label>
                                <div class="input-group">
                                    <input type="password" class="form-control" id="sendgrid-api-key" 
                                           placeholder="SG.xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" required>
                                    <button class="btn btn-outline-secondary" type="button" id="toggle-api-key-visibility">
                                        <i class="fas fa-eye"></i>
                                    </button>
                                </div>
                                <div class="form-text">
                                    <i class="fas fa-link me-1"></i>
                                    Get your API key from the 
                                    <a href="https://app.sendgrid.com/settings/api_keys" target="_blank" rel="noopener">
                                        SendGrid Dashboard
                                    </a>
                                </div>
                            </div>

                            <div class="col-md-6">
                                <label for="from-email" class="form-label">
                                    <i class="fas fa-at me-1"></i>From Email Address
                                </label>
                                <input type="email" class="form-control" id="from-email" 
                                       placeholder="noreply@yourcompany.com" required>
                                <div class="form-text">This email address will appear as the sender</div>
                            </div>

                            <div class="col-md-6">
                                <label for="from-name" class="form-label">
                                    <i class="fas fa-user me-1"></i>From Name
                                </label>
                                <input type="text" class="form-control" id="from-name" 
                                       placeholder="Parking Booking System" required>
                                <div class="form-text">Friendly name displayed to email recipients</div>
                            </div>

                            <!-- Email Features -->
                            <div class="col-12 mt-4">
                                <h6 class="border-bottom pb-2 mb-3">
                                    <i class="fas fa-toggle-on me-1"></i>Email Features
                                </h6>
                            </div>

                            <div class="col-md-6">
                                <div class="card border-0 bg-light h-100">
                                    <div class="card-body">
                                        <div class="form-check form-switch mb-2">
                                            <input class="form-check-input" type="checkbox" id="booking-confirmation-enabled">
                                            <label class="form-check-label fw-bold" for="booking-confirmation-enabled">
                                                Booking Confirmations
                                            </label>
                                        </div>
                                        <div class="small text-muted">
                                            <i class="fas fa-calendar-check me-1"></i>
                                            Send confirmation emails when users make or modify bookings
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <div class="col-md-6">
                                <div class="card border-0 bg-light h-100">
                                    <div class="card-body">
                                        <div class="form-check form-switch mb-2">
                                            <input class="form-check-input" type="checkbox" id="reports-enabled">
                                            <label class="form-check-label fw-bold" for="reports-enabled">
                                                Automated Reports
                                            </label>
                                        </div>
                                        <div class="small text-muted">
                                            <i class="fas fa-chart-line me-1"></i>
                                            Send scheduled reports to administrators
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <!-- Report Recipients -->
                            <div class="col-12" id="report-recipients-section" style="display: none;">
                                <label for="report-recipients" class="form-label">
                                    <i class="fas fa-users me-1"></i>Report Recipients
                                </label>
                                <textarea class="form-control" id="report-recipients" rows="3" 
                                          placeholder="admin@company.com, manager@company.com, finance@company.com"></textarea>
                                <div class="form-text">
                                    Enter email addresses separated by commas. These users will receive automated reports.
                                </div>
                            </div>
                        </div>

                        <div class="d-grid gap-2 d-md-flex justify-content-md-end mt-4">
                            <button type="submit" class="btn btn-success btn-sm">
                                <i class="fas fa-save me-2"></i>Save Email Settings
                            </button>
                        </div>
                    </form>

                    <!-- Status Messages -->
                    <div id="message-container" class="mt-3"></div>

                    <!-- Test Email Details -->
                    <div id="test-email-section" class="mt-4" style="display: none;">
                        <div class="card border-info">
                            <div class="card-header bg-info text-white">
                                <h6 class="mb-0">
                                    <i class="fas fa-flask me-1"></i>Test Email Configuration
                                </h6>
                            </div>
                            <div class="card-body">
                                <div class="row g-3">
                                    <div class="col-md-8">
                                        <label for="test-email-address" class="form-label">Test Email Address</label>
                                        <input type="email" class="form-control" id="test-email-address" 
                                               placeholder="your-email@example.com" required>
                                    </div>
                                    <div class="col-md-4 d-flex align-items-end">
                                        <button type="button" class="btn btn-primary w-100" id="send-test-email-btn">
                                            <i class="fas fa-paper-plane me-1"></i>Send Test
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Loading Overlay -->
                <div id="loading-overlay" class="position-absolute top-0 start-0 w-100 h-100 d-none" 
                     style="background: rgba(255,255,255,0.8); z-index: 10;">
                    <div class="d-flex justify-content-center align-items-center h-100">
                        <div class="spinner-border text-info" role="status">
                            <span class="visually-hidden">Loading...</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    setupEventListeners() {
        const form = this.querySelector('#email-form');
        const testBtn = this.querySelector('#test-email-btn');
        const refreshBtn = this.querySelector('#refresh-btn');
        const toggleApiKeyBtn = this.querySelector('#toggle-api-key-visibility');
        const reportsEnabledCheckbox = this.querySelector('#reports-enabled');
        const sendTestEmailBtn = this.querySelector('#send-test-email-btn');

        if (!this._listenersAttached) {
            form.addEventListener('submit', this.handleSubmit.bind(this));
            testBtn.addEventListener('click', this.toggleTestEmailSection.bind(this));
            refreshBtn.addEventListener('click', this.loadEmailData.bind(this));
            toggleApiKeyBtn.addEventListener('click', this.toggleApiKeyVisibility.bind(this));
            sendTestEmailBtn.addEventListener('click', this.sendTestEmail.bind(this));
            
            reportsEnabledCheckbox.addEventListener('change', this.toggleReportRecipientsSection.bind(this));
            
            this._listenersAttached = true;
        }
    }

    async loadEmailData() {
        this.setLoading(true);
        this.clearMessage();

        try {
            const response = await this.fetchEmailSettings();

            if (response.ok) {
                const settings = await response.json();
                this.emailSettings = settings;
                this.updateUI();

                this.dispatchEvent(new CustomEvent('email-loaded', {
                    detail: { settings }
                }));
            } else {
                throw new Error('Failed to load email settings');
            }
        } catch (error) {
            this.showMessage(`Error loading email settings: ${error.message}`, 'danger');
        } finally {
            this.setLoading(false);
        }
    }

    updateUI() {
        const settings = this.emailSettings;

        // Form fields
        this.querySelector('#sendgrid-api-key').value = settings.sendgrid_api_key || '';
        this.querySelector('#from-email').value = settings.from_email || '';
        this.querySelector('#from-name').value = settings.from_name || '';
        this.querySelector('#booking-confirmation-enabled').checked = settings.booking_confirmation_enabled || false;
        this.querySelector('#reports-enabled').checked = settings.reports_enabled || false;
        this.querySelector('#report-recipients').value = (settings.report_recipients || []).join(', ');

        // Update status indicator
        const statusBadge = this.querySelector('#email-status');
        if (settings.sendgrid_api_key && settings.from_email) {
            statusBadge.textContent = 'Configured';
            statusBadge.className = 'badge bg-success';
        } else {
            statusBadge.textContent = 'Not configured';
            statusBadge.className = 'badge bg-secondary';
        }

        // Toggle report recipients section visibility
        this.toggleReportRecipientsSection();
    }

    async handleSubmit(event) {
        event.preventDefault();

        this.setLoading(true);
        this.clearMessage();

        try {
            const recipients = this.querySelector('#report-recipients').value
                .split(',')
                .map(email => email.trim())
                .filter(email => email.length > 0);

            const data = {
                sendgrid_api_key: this.querySelector('#sendgrid-api-key').value,
                from_email: this.querySelector('#from-email').value,
                from_name: this.querySelector('#from-name').value,
                booking_confirmation_enabled: this.querySelector('#booking-confirmation-enabled').checked,
                reports_enabled: this.querySelector('#reports-enabled').checked,
                report_recipients: recipients
            };

            const response = await this.updateEmailSettings(data);

            if (response.ok) {
                this.showMessage('Email settings saved successfully!', 'success');
                this.emailSettings = data;
                this.updateUI();

                this.dispatchEvent(new CustomEvent('email-updated', {
                    detail: { settings: data }
                }));
            } else {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to save email settings');
            }
        } catch (error) {
            this.showMessage(`Error saving email settings: ${error.message}`, 'danger');
        } finally {
            this.setLoading(false);
        }
    }

    async sendTestEmail() {
        const testEmailAddress = this.querySelector('#test-email-address').value;
        
        if (!testEmailAddress) {
            this.showMessage('Please enter a test email address.', 'warning');
            return;
        }

        this.setLoading(true);
        this.clearMessage();

        try {
            const response = await this.testEmailConfig();

            if (response.ok) {
                const result = await response.json();
                this.showMessage(`✅ Test email sent successfully to ${testEmailAddress}!`, 'success');
            } else {
                const error = await response.json();
                this.showMessage(`❌ Test email failed: ${error.detail}`, 'danger');
            }
        } catch (error) {
            this.showMessage(`❌ Error sending test email: ${error.message}`, 'danger');
        } finally {
            this.setLoading(false);
        }
    }

    toggleTestEmailSection() {
        const section = this.querySelector('#test-email-section');
        const isVisible = section.style.display !== 'none';
        
        section.style.display = isVisible ? 'none' : 'block';
        
        if (!isVisible) {
            // Set default test email if available
            const userEmail = localStorage.getItem('user_email') || '';
            if (userEmail) {
                this.querySelector('#test-email-address').value = userEmail;
            }
        }
    }

    toggleApiKeyVisibility() {
        const apiKeyInput = this.querySelector('#sendgrid-api-key');
        const toggleBtn = this.querySelector('#toggle-api-key-visibility');
        const icon = toggleBtn.querySelector('i');
        
        if (apiKeyInput.type === 'password') {
            apiKeyInput.type = 'text';
            icon.className = 'fas fa-eye-slash';
        } else {
            apiKeyInput.type = 'password';
            icon.className = 'fas fa-eye';
        }
    }

    toggleReportRecipientsSection() {
        const reportsEnabled = this.querySelector('#reports-enabled').checked;
        const section = this.querySelector('#report-recipients-section');
        
        section.style.display = reportsEnabled ? 'block' : 'none';
    }

    // API methods
    async fetchEmailSettings() {
        return fetch('/admin/api/email/settings', {
            headers: { 'Authorization': `Bearer ${this.getAuthToken()}` }
        });
    }

    async updateEmailSettings(data) {
        return fetch('/admin/api/email/settings', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${this.getAuthToken()}`
            },
            body: JSON.stringify(data)
        });
    }

    async testEmailConfig() {
        return fetch('/admin/api/email/test-config', {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${this.getAuthToken()}` }
        });
    }

    // Utility methods
    getAuthToken() {
        return localStorage.getItem('access_token') || '';
    }

    setLoading(loading) {
        const overlay = this.querySelector('#loading-overlay');
        overlay.classList.toggle('d-none', !loading);
    }

    showMessage(message, type = 'info') {
        const container = this.querySelector('#message-container');
        const alertClass = `alert alert-${type} alert-dismissible fade show`;
        
        container.innerHTML = `
            <div class="${alertClass}" role="alert">
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>
        `;

        if (type === 'success') {
            setTimeout(() => this.clearMessage(), 5000);
        }
    }

    clearMessage() {
        const container = this.querySelector('#message-container');
        container.innerHTML = '';
    }

    // Public API
    getEmailSettings() {
        return this.emailSettings;
    }

    async refresh() {
        await this.loadEmailData();
    }
}

// Register the custom element
customElements.define('email-manager', EmailManager);
