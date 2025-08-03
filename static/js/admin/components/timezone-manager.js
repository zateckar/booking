/**
 * Timezone Manager Web Component - Bootstrap UI
 * Modern, clean interface for timezone configuration
 */
class TimezoneManager extends HTMLElement {
    constructor() {
        super();
        this.currentTimezone = null;
        this.availableTimezones = [];
    }

    connectedCallback() {
        AdminLogs.log('DEBUG', '🕐 TimezoneManager connected to DOM');
        this.render();
        this.setupEventListeners();
        this.loadTimezoneData();
    }

    render() {
        this.innerHTML = `
            <style>
                .card-header {
                    background-color: var(--bs-primary);
                    color: var(--bs-light);
                }
                .btn-success {
                    background-color: var(--bs-success);
                }
            </style>
            <div class="card shadow-sm">
                <div class="card-header d-flex justify-content-between align-items-center">
                    <h5 class="card-title mb-0">
                        <i class="fas fa-clock me-2"></i>Timezone Settings
                    </h5>
                    <button class="btn btn-light btn-sm" id="refresh-btn" title="Refresh">
                        Refresh
                    </button>
                </div>
                
                <div class="card-body">
                    <!-- Current Timezone Display -->
                    <div class="alert alert-info d-flex align-items-center mb-4" role="alert">
                        <i class="fas fa-info-circle me-2"></i>
                        <div>
                            <strong>Current Timezone:</strong> 
                            <span id="current-timezone-display">Loading...</span>
                        </div>
                    </div>

                    <!-- Timezone Selection Form -->
                    <form id="timezone-form">
                        <div class="row">
                            <div class="col-12">
                                <div class="mb-3">
                                    <label for="timezone-select" class="form-label">
                                        <i class="fas fa-globe me-1"></i>Select New Timezone
                                    </label>
                                    <select class="form-select form-select-sm" id="timezone-select" required>
                                        <option value="">Choose a timezone...</option>
                                    </select>
                                    <div class="form-text">
                                        This will affect all time displays and scheduling in the system.
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div class="d-grid gap-2 d-md-flex justify-content-md-end">
                            <button type="submit" class="btn btn-success btn-sm" disabled>
                                <i class="fas fa-save me-2"></i>Save Timezone
                            </button>
                        </div>
                    </form>

                    <!-- Status Messages -->
                    <div id="message-container" class="mt-3"></div>
                </div>

                <!-- Loading Overlay -->
                <div id="loading-overlay" class="position-absolute top-0 start-0 w-100 h-100 d-none" 
                     style="background: rgba(255,255,255,0.8); z-index: 10;">
                    <div class="d-flex justify-content-center align-items-center h-100">
                        <div class="spinner-border text-primary" role="status">
                            <span class="visually-hidden">Loading...</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    setupEventListeners() {
        const form = this.querySelector('#timezone-form');
        const refreshBtn = this.querySelector('#refresh-btn');
        const timezoneSelect = this.querySelector('#timezone-select');
        const submitBtn = this.querySelector('button[type="submit"]');

        form.addEventListener('submit', this.handleSubmit.bind(this));
        refreshBtn.addEventListener('click', this.loadTimezoneData.bind(this));
        
        timezoneSelect.addEventListener('change', () => {
            submitBtn.disabled = !timezoneSelect.value || timezoneSelect.value === this.currentTimezone;
        });
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
            this.showMessage(`Error loading timezone settings: ${error.message}`, 'danger');
        } finally {
            this.setLoading(false);
        }
    }

    updateUI() {
        const currentDisplay = this.querySelector('#current-timezone-display');
        const timezoneSelect = this.querySelector('#timezone-select');
        const submitBtn = this.querySelector('button[type="submit"]');

        // Update current timezone display
        currentDisplay.textContent = this.currentTimezone || 'Not configured';

        // Populate timezone select
        timezoneSelect.innerHTML = '<option value="">Choose a timezone...</option>';
        this.availableTimezones.forEach(tz => {
            const option = document.createElement('option');
            option.value = tz.value;
            option.textContent = tz.label;
            timezoneSelect.appendChild(option);
        });

        // Reset button state
        submitBtn.disabled = true;
    }

    async handleSubmit(event) {
        event.preventDefault();

        const timezoneSelect = this.querySelector('#timezone-select');
        const newTimezone = timezoneSelect.value;

        if (!newTimezone || newTimezone === this.currentTimezone) {
            this.showMessage('Please select a different timezone.', 'warning');
            return;
        }

        this.setLoading(true);
        this.clearMessage();

        try {
            const response = await this.updateTimezoneSettings({ timezone: newTimezone });

            if (response.ok) {
                this.currentTimezone = newTimezone;
                this.updateUI();
                this.showMessage('Timezone updated successfully!', 'success');

                this.dispatchEvent(new CustomEvent('timezone-changed', {
                    detail: { timezone: newTimezone }
                }));
            } else {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to update timezone');
            }
        } catch (error) {
            this.showMessage(`Error updating timezone: ${error.message}`, 'danger');
        } finally {
            this.setLoading(false);
        }
    }

    // API methods
    async fetchTimezoneSettings() {
        return await window.AdminAPI.timezone.getSettings();
    }

    async fetchAvailableTimezones() {
        return await window.AdminAPI.timezone.getTimezones();
    }

    async updateTimezoneSettings(data) {
        return await window.AdminAPI.timezone.updateSettings(data);
    }

    // Utility methods

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

        // Auto-hide success messages after 5 seconds
        if (type === 'success') {
            setTimeout(() => this.clearMessage(), 5000);
        }
    }

    clearMessage() {
        const container = this.querySelector('#message-container');
        container.innerHTML = '';
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
