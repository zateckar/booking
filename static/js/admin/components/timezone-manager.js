/**
 * Timezone Manager Web Component
 * Encapsulates all timezone-related functionality
 */
class TimezoneManager extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
        this.currentTimezone = null;
        this.availableTimezones = [];
    }

    connectedCallback() {
        console.log('🕐 TimezoneManager connected to DOM');
        this.render();
        this.setupEventListeners();
        this.loadTimezoneData();
    }

    render() {
        this.shadowRoot.innerHTML = `
            ${window.AdminSharedStyles?.getSharedStyles() || ''}
            
            <div class="card">
                <div class="card-header">
                    <h5 class="card-title">🕐 Timezone Configuration</h5>
                    <button class="btn btn-primary btn-sm" id="refresh-btn">Refresh</button>
                </div>
                <div class="card-body">
                    <form id="timezone-form">
                        <div class="row">
                            <div class="col-lg-5">
                                <label class="form-label">Current System Timezone</label>
                                <input type="text" class="form-control" id="current-timezone" readonly>
                            </div>
                            <div class="col-lg-5">
                                <label class="form-label">Available Timezones</label>
                                <select class="form-select" id="available-timezones">
                                    <option value="">Loading...</option>
                                </select>
                            </div>
                            <div class="col-lg-2 d-flex align-items-end">
                                <button type="submit" class="btn btn-primary w-100">Save</button>
                            </div>
                        </div>
                        <div id="message"></div>
                    </form>
                </div>
            </div>
        `;
    }

    setupEventListeners() {
        const form = this.shadowRoot.getElementById('timezone-form');
        const refreshBtn = this.shadowRoot.getElementById('refresh-btn');

        form.addEventListener('submit', this.handleSubmit.bind(this));
        refreshBtn.addEventListener('click', this.loadTimezoneData.bind(this));
    }

    async loadTimezoneData() {
        this.setLoading(true);
        this.clearMessage();

        try {
            const [settingsResponse, timezonesResponse] = await Promise.all([
                this.fetchTimezoneSettings(),
                this.fetchAvailableTimezones()
            ]);

            if (settingsResponse.ok && timezonesResponse.ok) {
                const settings = await settingsResponse.json();
                const timezones = await timezonesResponse.json();

                this.currentTimezone = settings.timezone;
                this.availableTimezones = timezones;

                this.updateUI();
                this.dispatchEvent(new CustomEvent('timezone-loaded', {
                    detail: { timezone: this.currentTimezone }
                }));
            } else {
                throw new Error('Failed to load timezone data');
            }
        } catch (error) {
            this.showError(`Error loading timezone settings: ${error.message}`);
        } finally {
            this.setLoading(false);
        }
    }

    updateUI() {
        const currentInput = this.shadowRoot.getElementById('current-timezone');
        const select = this.shadowRoot.getElementById('available-timezones');

        currentInput.value = this.currentTimezone || 'Not set';

        select.innerHTML = '<option value="">Select Timezone</option>';
        this.availableTimezones.forEach(tz => {
            const option = document.createElement('option');
            option.value = tz.value;
            option.textContent = tz.label;
            if (tz.value === this.currentTimezone) {
                option.selected = true;
            }
            select.appendChild(option);
        });
    }

    async handleSubmit(event) {
        event.preventDefault();

        const select = this.shadowRoot.getElementById('available-timezones');
        const newTimezone = select.value;

        if (!newTimezone) {
            this.showError('Please select a timezone.');
            return;
        }

        this.setLoading(true);
        this.clearMessage();

        try {
            const response = await this.updateTimezoneSettings({ timezone: newTimezone });

            if (response.ok) {
                this.currentTimezone = newTimezone;
                this.updateUI();
                this.showSuccess('Timezone settings updated successfully.');

                this.dispatchEvent(new CustomEvent('timezone-changed', {
                    detail: { timezone: newTimezone }
                }));
            } else {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to update timezone settings');
            }
        } catch (error) {
            this.showError(`Error updating timezone: ${error.message}`);
        } finally {
            this.setLoading(false);
        }
    }

    // API methods
    async fetchTimezoneSettings() {
        const token = this.getAuthToken();
        console.log('🕐 TimezoneManager: Using token for settings:', token ? 'Token present' : 'No token');
        
        // Use the global auth function if available, otherwise fallback to direct fetch
        if (window.auth && window.auth.makeAuthenticatedRequest) {
            return window.auth.makeAuthenticatedRequest('/admin/api/timezone/settings');
        }
        
        return fetch('/admin/api/timezone/settings', {
            headers: { 'Authorization': `Bearer ${token}` },
            credentials: 'include'
        });
    }

    async fetchAvailableTimezones() {
        const token = this.getAuthToken();
        console.log('🕐 TimezoneManager: Using token for timezones:', token ? 'Token present' : 'No token');
        
        // Use the global auth function if available, otherwise fallback to direct fetch
        if (window.auth && window.auth.makeAuthenticatedRequest) {
            return window.auth.makeAuthenticatedRequest('/admin/api/timezone/timezones');
        }
        
        return fetch('/admin/api/timezone/timezones', {
            headers: { 'Authorization': `Bearer ${token}` },
            credentials: 'include'
        });
    }

    async updateTimezoneSettings(data) {
        // Use the global auth function if available, otherwise fallback to direct fetch
        if (window.auth && window.auth.makeAuthenticatedRequest) {
            return window.auth.makeAuthenticatedRequest('/admin/api/timezone/settings', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });
        }
        
        return fetch('/admin/api/timezone/settings', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${this.getAuthToken()}`
            },
            credentials: 'include',
            body: JSON.stringify(data)
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
    getCurrentTimezone() {
        return this.currentTimezone;
    }

    async refresh() {
        await this.loadTimezoneData();
    }
}

// Register the custom element
customElements.define('timezone-manager', TimezoneManager);