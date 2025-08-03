/**
 * Backup Manager Web Component - Bootstrap UI
 * Modern, clean interface for backup management
 */
class BackupManager extends HTMLElement {
    constructor() {
        super();
        AdminLogs.log('DEBUG', '🔧 BackupManager constructor');
        this.settings = {};
        this.backups = [];
    }

    connectedCallback() {
        AdminLogs.log('DEBUG', '🔧 BackupManager connected to DOM');
        this.render();
        this.loadBackupData();
        this.setupEventListeners();
    }

    render() {
        this.innerHTML = `
            <style>
                .card-header {
                    background-color: var(--bs-warning);
                    color: var(--bs-dark);
                }
                .btn-success {
                    background-color: var(--bs-success);
                }
                .btn-primary {
                    background-color: var(--bs-primary);
                }
            </style>
            <div class="card shadow-sm">
                <div class="card-header d-flex justify-content-between align-items-center">
                    <h5 class="card-title mb-0">
                        <i class="fas fa-database me-2"></i>Database Backup Management
                    </h5>
                    <div class="btn-group" role="group">
                        <button class="btn btn-success btn-sm" id="test-connection-btn" title="Test Connection">
                            Test
                        </button>
                        <button class="btn btn-primary btn-sm" id="backup-now-btn" title="Start Backup Now">
                            Backup Now
                        </button>
                        <button class="btn btn-light btn-sm" id="refresh-btn" title="Refresh">
                            Refresh
                        </button>
                    </div>
                </div>
                
                <div class="card-body">
                    <!-- Status Overview -->
                    <div class="row mb-4">
                        <div class="col-md-6">
                            <div class="card bg-light">
                                <div class="card-body">
                                    <h6 class="card-subtitle mb-2 text-muted">
                                        <i class="fas fa-info-circle me-1"></i>Backup Status
                                    </h6>
                                    <div class="row g-2">
                                        <div class="col-6">
                                            <small class="text-muted">Last Backup:</small>
                                            <div id="last-backup-time" class="fw-bold">Never</div>
                                        </div>
                                        <div class="col-6">
                                            <small class="text-muted">Status:</small>
                                            <div><span id="last-backup-status" class="badge bg-secondary">Not configured</span></div>
                                        </div>
                                        <div class="col-6">
                                            <small class="text-muted">Size:</small>
                                            <div id="last-backup-size" class="fw-bold">-</div>
                                        </div>
                                        <div class="col-6">
                                            <small class="text-muted">Enabled:</small>
                                            <div id="backup-enabled-status" class="fw-bold">No</div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="card bg-light">
                                <div class="card-body">
                                    <h6 class="card-subtitle mb-2 text-muted">
                                        <i class="fas fa-list me-1"></i>Recent Backups
                                    </h6>
                                    <div id="backup-list-preview" class="small">
                                        <p class="text-muted mb-0">Click "Load Backups" to view</p>
                                    </div>
                                    <button class="btn btn-outline-primary btn-sm mt-2" id="load-backup-list-btn">
                                        <i class="fas fa-download me-1"></i>Load Backups
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Configuration Form -->
                    <form id="backup-form">
                        <div class="row g-3">
                            <!-- Basic Settings -->
                            <div class="col-12">
                                <h6 class="border-bottom pb-2 mb-3">
                                    <i class="fas fa-cog me-1"></i>Basic Settings
                                </h6>
                            </div>
                            
                            <div class="col-md-6">
                                <div class="form-check form-switch">
                                    <input class="form-check-input" type="checkbox" id="backup-enabled">
                                    <label class="form-check-label fw-bold" for="backup-enabled">
                                        Enable Automatic Backups
                                    </label>
                                </div>
                            </div>

                            <div class="col-md-3">
                                <label for="backup-frequency" class="form-label">Frequency</label>
                                <select class="form-select" id="backup-frequency">
                                    <option value="daily">Daily</option>
                                    <option value="weekly">Weekly</option>
                                    <option value="monthly">Monthly</option>
                                </select>
                            </div>

                            <div class="col-md-3">
                                <label for="backup-hour" class="form-label">Time (24h)</label>
                                <select class="form-select" id="backup-hour">
                                    ${Array.from({length: 24}, (_, i) => 
                                        `<option value="${i}">${i.toString().padStart(2, '0')}:00</option>`
                                    ).join('')}
                                </select>
                            </div>

                            <!-- Azure Storage Settings -->
                            <div class="col-12 mt-4">
                                <h6 class="border-bottom pb-2 mb-3">
                                    <i class="fab fa-microsoft me-1"></i>Azure Blob Storage Configuration
                                </h6>
                            </div>

                            <div class="col-md-6">
                                <label for="storage-account" class="form-label">
                                    <i class="fas fa-server me-1"></i>Storage Account
                                </label>
                                <input type="text" class="form-control" id="storage-account" 
                                       placeholder="mystorageaccount" required>
                                <div class="form-text">Azure Storage Account name</div>
                            </div>

                            <div class="col-md-6">
                                <label for="container-name" class="form-label">
                                    <i class="fas fa-folder me-1"></i>Container Name
                                </label>
                                <input type="text" class="form-control" id="container-name" 
                                       placeholder="backups" required>
                                <div class="form-text">Blob container for storing backups</div>
                            </div>

                            <div class="col-12">
                                <label for="sas-token" class="form-label">
                                    <i class="fas fa-key me-1"></i>SAS Token
                                </label>
                                <div class="input-group">
                                    <input type="password" class="form-control" id="sas-token" 
                                           placeholder="?sv=2021-06-08&ss=b&srt=..." required>
                                    <button class="btn btn-outline-secondary" type="button" id="toggle-sas-visibility">
                                        <i class="fas fa-eye"></i>
                                    </button>
                                </div>
                                <div class="form-text">Shared Access Signature token with read/write permissions</div>
                            </div>

                            <div class="col-md-6">
                                <label for="keep-backups" class="form-label">
                                    <i class="fas fa-history me-1"></i>Retention Period
                                </label>
                                <div class="input-group">
                                    <input type="number" class="form-control" id="keep-backups" 
                                           value="30" min="1" max="365" required>
                                    <span class="input-group-text">days</span>
                                </div>
                                <div class="form-text">How long to keep backup files</div>
                            </div>
                        </div>

                        <div class="d-grid gap-2 d-md-flex justify-content-md-end mt-4">
                            <button type="submit" class="btn btn-success btn-sm">
                                <i class="fas fa-save me-2"></i>Save Configuration
                            </button>
                        </div>
                    </form>

                    <!-- Status Messages -->
                    <div id="message-container" class="mt-3"></div>

                    <!-- Error Details -->
                    <div id="error-details" class="mt-3" style="display: none;">
                        <div class="card border-danger">
                            <div class="card-header bg-danger text-white">
                                <h6 class="mb-0"><i class="fas fa-exclamation-triangle me-1"></i>Error Details</h6>
                            </div>
                            <div class="card-body">
                                <pre id="error-content" class="mb-0 small"></pre>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Loading Overlay -->
                <div id="loading-overlay" class="position-absolute top-0 start-0 w-100 h-100 d-none" 
                     style="background: rgba(255,255,255,0.8); z-index: 10;">
                    <div class="d-flex justify-content-center align-items-center h-100">
                        <div class="spinner-border text-warning" role="status">
                            <span class="visually-hidden">Loading...</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    setupEventListeners() {
        const form = this.querySelector('#backup-form');
        const testBtn = this.querySelector('#test-connection-btn');
        const backupBtn = this.querySelector('#backup-now-btn');
        const refreshBtn = this.querySelector('#refresh-btn');
        const loadListBtn = this.querySelector('#load-backup-list-btn');
        const toggleSasBtn = this.querySelector('#toggle-sas-visibility');
        
        if (!this._listenersAttached) {
            form.addEventListener('submit', this.handleSubmit.bind(this));
            testBtn.addEventListener('click', this.testConnection.bind(this));
            backupBtn.addEventListener('click', this.backupNow.bind(this));
            refreshBtn.addEventListener('click', this.loadBackupData.bind(this));
            loadListBtn.addEventListener('click', this.loadBackupList.bind(this));
            toggleSasBtn.addEventListener('click', this.toggleSasVisibility.bind(this));
            this._listenersAttached = true;
        }
    }

    async loadBackupData() {
        this.setLoading(true);
        this.clearMessage();
        
        try {
            const response = await this.fetchBackupSettings();

            if (response.ok) {
                const settings = await response.json();
                this.backupSettings = settings;
                this.updateUI();
                
                this.dispatchEvent(new CustomEvent('backup-loaded', { 
                    detail: { settings } 
                }));
            } else {
                throw new Error('Failed to load backup settings');
            }
        } catch (error) {
            this.showMessage(`Error loading backup settings: ${error.message}`, 'danger');
        } finally {
            this.setLoading(false);
        }
    }

    updateUI() {
        const settings = this.backupSettings;
        
        // Form fields
        this.querySelector('#backup-enabled').checked = settings.enabled || false;
        this.querySelector('#storage-account').value = settings.storage_account || '';
        this.querySelector('#container-name').value = settings.container_name || '';
        this.querySelector('#sas-token').value = settings.sas_token || '';
        this.querySelector('#backup-frequency').value = settings.backup_frequency || 'daily';
        this.querySelector('#backup-hour').value = settings.backup_hour || 2;
        this.querySelector('#keep-backups').value = settings.keep_backups || 30;
        
        // Status display
        const lastTimeElement = this.querySelector('#last-backup-time');
        if (settings.last_backup_time) {
            lastTimeElement.textContent = new Date(settings.last_backup_time).toLocaleString();
        } else {
            lastTimeElement.textContent = 'Never';
        }
        
        const statusElement = this.querySelector('#last-backup-status');
        const status = settings.last_backup_status || 'Not configured';
        statusElement.textContent = status;
        statusElement.className = 'badge ';
        switch (status) {
            case 'success':
                statusElement.className += 'bg-success';
                break;
            case 'failed':
                statusElement.className += 'bg-danger';
                break;
            case 'running':
                statusElement.className += 'bg-warning text-dark';
                break;
            default:
                statusElement.className += 'bg-secondary';
        }
        
        this.querySelector('#last-backup-size').textContent = 
            settings.last_backup_size_mb ? `${settings.last_backup_size_mb} MB` : '-';
        
        this.querySelector('#backup-enabled-status').textContent = 
            settings.enabled ? 'Yes' : 'No';

        // Show error if exists
        if (settings.last_backup_error) {
            this.showErrorDetails(settings.last_backup_error);
        }
    }

    async handleSubmit(event) {
        event.preventDefault();
        
        this.setLoading(true);
        this.clearMessage();

        try {
            const data = {
                enabled: this.querySelector('#backup-enabled').checked,
                storage_account: this.querySelector('#storage-account').value,
                container_name: this.querySelector('#container-name').value,
                sas_token: this.querySelector('#sas-token').value,
                backup_frequency: this.querySelector('#backup-frequency').value,
                backup_hour: parseInt(this.querySelector('#backup-hour').value),
                keep_backups: parseInt(this.querySelector('#keep-backups').value)
            };

            const response = await this.updateBackupSettings(data);

            if (response.ok) {
                this.showMessage('Backup settings saved successfully!', 'success');
                await this.loadBackupData();
                
                this.dispatchEvent(new CustomEvent('backup-updated', { 
                    detail: { settings: data } 
                }));
            } else {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to save backup settings');
            }
        } catch (error) {
            this.showMessage(`Error saving backup settings: ${error.message}`, 'danger');
        } finally {
            this.setLoading(false);
        }
    }

    async testConnection() {
        this.setLoading(true);
        this.clearMessage();
        
        try {
            const response = await this.testBackupConnection();

            if (response.ok) {
                const result = await response.json();
                if (result.success) {
                    this.showMessage('✅ Azure Blob Storage connection successful!', 'success');
                } else {
                    this.showMessage(`❌ Connection test failed: ${result.error}`, 'danger');
                }
            } else {
                const error = await response.json();
                this.showMessage(`❌ Connection test failed: ${error.detail}`, 'danger');
            }
        } catch (error) {
            this.showMessage(`❌ Error testing backup connection: ${error.message}`, 'danger');
        } finally {
            this.setLoading(false);
        }
    }

    async backupNow() {
        if (!confirm('Are you sure you want to start a backup now?')) {
            return;
        }
        
        this.setLoading(true);
        this.clearMessage();
        
        try {
            const response = await this.startBackupNow();

            if (response.ok) {
                const result = await response.json();
                this.showMessage(result.message, 'success');
                
                setTimeout(() => {
                    this.loadBackupData();
                }, 2000);
                
                this.dispatchEvent(new CustomEvent('backup-started'));
            } else {
                const error = await response.json();
                this.showMessage(error.detail || 'Failed to start backup', 'danger');
            }
        } catch (error) {
            this.showMessage(`Error starting backup: ${error.message}`, 'danger');
        } finally {
            this.setLoading(false);
        }
    }

    async loadBackupList() {
        const previewElement = this.querySelector('#backup-list-preview');
        
        try {
            previewElement.innerHTML = '<div class="spinner-border spinner-border-sm me-2"></div>Loading...';
            
            const response = await this.fetchBackupList(5);

            if (response.ok) {
                const result = await response.json();
                
                if (result.success) {
                    const backups = result.backups || [];
                    
                    if (backups.length > 0) {
                        const backupItems = backups.map((backup, index) => {
                            const dateMatch = backup.match(/(\d{8}_\d{6})/);
                            let displayDate = 'Unknown date';
                            
                            if (dateMatch) {
                                const dateStr = dateMatch[1];
                                const year = dateStr.substring(0, 4);
                                const month = dateStr.substring(4, 6);
                                const day = dateStr.substring(6, 8);
                                const hour = dateStr.substring(9, 11);
                                const minute = dateStr.substring(11, 13);
                                displayDate = `${year}-${month}-${day} ${hour}:${minute}`;
                            }
                            
                            return `<div class="d-flex justify-content-between align-items-center border-bottom py-1">
                                        <div class="small">${displayDate}</div>
                                        <span class="badge bg-light text-dark">#${index + 1}</span>
                                    </div>`;
                        }).join('');
                        
                        previewElement.innerHTML = `
                            <div class="mb-2"><strong>${result.count} backups found</strong></div>
                            ${backupItems}
                        `;
                    } else {
                        previewElement.innerHTML = '<div class="text-muted">No backup files found</div>';
                    }
                } else {
                    previewElement.innerHTML = `<div class="text-danger">Error: ${result.error}</div>`;
                }
            } else {
                const error = await response.json();
                previewElement.innerHTML = `<div class="text-danger">API Error: ${error.detail || 'Unknown error'}</div>`;
            }
        } catch (error) {
            previewElement.innerHTML = `<div class="text-danger">Error: ${error.message}</div>`;
        }
    }

    toggleSasVisibility() {
        const sasInput = this.querySelector('#sas-token');
        const toggleBtn = this.querySelector('#toggle-sas-visibility');
        const icon = toggleBtn.querySelector('i');
        
        if (sasInput.type === 'password') {
            sasInput.type = 'text';
            icon.className = 'fas fa-eye-slash';
        } else {
            sasInput.type = 'password';
            icon.className = 'fas fa-eye';
        }
    }

    showErrorDetails(error) {
        const errorDiv = this.querySelector('#error-details');
        const errorContent = this.querySelector('#error-content');
        
        errorContent.textContent = error;
        errorDiv.style.display = 'block';
    }

    // API methods
    async fetchBackupSettings() {
        return fetch('/admin/api/backup/settings', {
            headers: { 'Authorization': `Bearer ${this.getAuthToken()}` },
            credentials: 'include'
        });
    }

    async updateBackupSettings(data) {
        return fetch('/admin/api/backup/settings', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${this.getAuthToken()}`
            },
            credentials: 'include',
            body: JSON.stringify(data)
        });
    }

    async testBackupConnection() {
        return fetch('/admin/api/backup/test-connection', {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${this.getAuthToken()}` },

        });
    }

    async startBackupNow() {
        return fetch('/admin/api/backup/backup-now', {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${this.getAuthToken()}` },

        });
    }

    async fetchBackupList(limit = 20) {
        return fetch(`/admin/api/backup/list?limit=${limit}`, {
            headers: { 'Authorization': `Bearer ${this.getAuthToken()}` },
            
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
        
        // Hide error details
        const errorDiv = this.querySelector('#error-details');
        errorDiv.style.display = 'none';
    }

    // Public API
    getBackupSettings() {
        return this.backupSettings;
    }

    async refresh() {
        await this.loadBackupData();
    }
}

// Register the custom element
customElements.define('backup-manager', BackupManager);
