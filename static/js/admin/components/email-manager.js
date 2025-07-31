/**
 * Email Manager Web Component
 * Encapsulates all email-related functionality
 */
class EmailManager extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
        this.emailSettings = {};
    }

    connectedCallback() {
        console.log('📧 EmailManager connected to DOM');
        this.render();
        this.setupEventListeners();
        this.loadEmailData();
    }

    render() {
        this.shadowRoot.innerHTML = `
            ${window.AdminSharedStyles?.getSharedStyles() || ''}
            
            <div class="card">
                <div class="card-header">
                    <h5 class="card-title">📧 Email Configuration</h5>
                    <div>
                        <button class="btn btn-success btn-sm" id="test-email-btn">Test Email</button>
                        <button class="btn btn-info btn-sm" id="refresh-btn">Refresh</button>
                    </div>
                </div>
                <div class="card-body">
                    <form id="email-form">
                        <div class="row">
                            <div class="col-lg-4">
                                <label class="form-label">SendGrid API Key</label>
                                <input type="password" class="form-control" id="sendgrid-api-key" placeholder="SG.xxx">
                                
                                <label class="form-label">From Email</label>
                                <input type="email" class="form-control" id="from-email" placeholder="noreply@example.com">
                                
                                <label class="form-label">From Name</label>
                                <input type="text" class="form-control" id="from-name" placeholder="Parking Booking System">
                            </div>
                            <div class="col-lg-4">
                                <label class="form-label">
                                    <input type="checkbox" class="form-check-input" id="booking-confirmation-enabled">
                                    Enable Booking Confirmations
                                </label>
                                
                                <label class="form-label">
                                    <input type="checkbox" class="form-check-input" id="reports-enabled">
                                    Enable Reports
                                </label>
                                
                                <label class="form-label">Report Recipients</label>
                                <textarea class="form-control" id="report-recipients" rows="3" placeholder="admin@example.com, manager@example.com"></textarea>
                            </div>
                            <div class="col-lg-4 d-flex align-items-end">
                                <button type="submit" class="btn btn-primary w-100">Save Email Settings</button>
                            </div>
                        </div>
                        <div id="message"></div>
                    </form>
                </div>
            </div>
        `;
    }

    setupEventListeners() {
        const form = this.shadowRoot.getElementById('email-form');
        const testBtn = this.shadowRoot.getElementById('test-email-btn');
        const refreshBtn = this.shadowRoot.getElementById('refresh-btn');

        // Prevent double event listeners
        if (!this._listenersAttached) {
            form.addEventListener('submit', this.handleSubmit.bind(this));
            testBtn.addEventListener('click', this.testEmail.bind(this));
            refreshBtn.addEventListener('click', this.loadEmailData.bind(this));
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
            this.showError(`Error loading email settings: ${error.message}`);
        } finally {
            this.setLoading(false);
        }
    }

    updateUI() {
        const settings = this.emailSettings;

        this.shadowRoot.getElementById('sendgrid-api-key').value = settings.sendgrid_api_key || '';
        this.shadowRoot.getElementById('from-email').value = settings.from_email || '';
        this.shadowRoot.getElementById('from-name').value = settings.from_name || '';
        this.shadowRoot.getElementById('booking-confirmation-enabled').checked = settings.booking_confirmation_enabled || false;
        this.shadowRoot.getElementById('reports-enabled').checked = settings.reports_enabled || false;
        this.shadowRoot.getElementById('report-recipients').value = (settings.report_recipients || []).join(', ');
    }

    async handleSubmit(event) {
        event.preventDefault();

        this.setLoading(true);
        this.clearMessage();

        try {
            const recipients = this.shadowRoot.getElementById('report-recipients').value
                .split(',')
                .map(email => email.trim())
                .filter(email => email.length > 0);

            const data = {
                sendgrid_api_key: this.shadowRoot.getElementById('sendgrid-api-key').value,
                from_email: this.shadowRoot.getElementById('from-email').value,
                from_name: this.shadowRoot.getElementById('from-name').value,
                booking_confirmation_enabled: this.shadowRoot.getElementById('booking-confirmation-enabled').checked,
                reports_enabled: this.shadowRoot.getElementById('reports-enabled').checked,
                report_recipients: recipients
            };

            const response = await this.updateEmailSettings(data);

            if (response.ok) {
                this.showSuccess('Email settings saved successfully');
                this.emailSettings = data;

                this.dispatchEvent(new CustomEvent('email-updated', {
                    detail: { settings: data }
                }));
            } else {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to save email settings');
            }
        } catch (error) {
            this.showError(`Error saving email settings: ${error.message}`);
        } finally {
            this.setLoading(false);
        }
    }

    async testEmail() {
        this.setLoading(true);
        this.clearMessage();

        try {
            const response = await this.testEmailConfig();

            if (response.ok) {
                const result = await response.json();
                this.showSuccess(result.message);
            } else {
                const error = await response.json();
                this.showError(error.detail || 'Email test failed');
            }
        } catch (error) {
            this.showError(`Error testing email: ${error.message}`);
        } finally {
            this.setLoading(false);
        }
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
        const card = this.shadowRoot.querySelector('.card');
        if (loading) {
            card.classList.add('loading');
        } else {
            card.classList.remove('loading');
        }
    }

    showError(message) {
        const messageDiv = this.shadowRoot.getElementById('message');
        messageDiv.innerHTML = `<div class="error">${message}</div>`;
    }

    showSuccess(message) {
        const messageDiv = this.shadowRoot.getElementById('message');
        messageDiv.innerHTML = `<div class="success">${message}</div>`;
    }

    clearMessage() {
        const messageDiv = this.shadowRoot.getElementById('message');
        messageDiv.innerHTML = '';
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