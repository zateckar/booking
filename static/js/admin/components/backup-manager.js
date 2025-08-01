/**
 * Backup Manager Web Component
 * Encapsulates all backup-related functionality
 */
class BackupManager extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
        this.backupSettings = {};
        this.backupList = [];
    }

    connectedCallback() {
        console.log('🔧 BackupManager connected to DOM');
        this.render();
        this.setupEventListeners();
        this.loadBackupData();
    }

    render() {
        console.log('🔧 BackupManager rendering...');
        this.shadowRoot.innerHTML = `
            ${window.AdminSharedStyles?.getSharedStyles() || ''}
            
            <div class="card">
                <div class="card-header">
                    <h5 class="card-title">🗄️ Database Backup - Azure Blob Storage</h5>
                    <div>
                        <button class="btn btn-success" id="test-connection-btn">Test</button>
                        <button class="btn btn-warning" id="backup-now-btn">Backup Now</button>
                        <button class="btn btn-info" id="refresh-btn">Refresh</button>
                    </div>
                </div>
                <div class="card-body">
                    <form id="backup-form">
                        <div class="form-grid">
                            <div class="form-section">
                                <div class="form-check">
                                    <input type="checkbox" class="form-check-input" id="backup-enabled">
                                    <label class="form-check-label" for="backup-enabled">Enable Backup</label>
                                </div>
                                <div>
                                    <label class="form-label" for="storage-account">Storage Account</label>
                                    <input type="text" class="form-control" id="storage-account" placeholder="mystorageaccount">
                                </div>
                                <div>
                                    <label class="form-label" for="container-name">Container Name</label>
                                    <input type="text" class="form-control" id="container-name" placeholder="backups">
                                </div>
                                <div>
                                    <label class="form-label" for="sas-token">SAS Token</label>
                                    <input type="password" class="form-control" id="sas-token" placeholder="?sv=...">
                                </div>
                            </div>
                            <div class="form-section">
                                <div>
                                    <label class="form-label" for="backup-frequency">Backup Frequency</label>
                                    <select class="form-select" id="backup-frequency">
                                        <option value="daily">Daily</option>
                                        <option value="weekly">Weekly</option>
                                        <option value="monthly">Monthly</option>
                                    </select>
                                </div>
                                <div>
                                    <label class="form-label" for="backup-hour">Backup Hour (24h format)</label>
                                    <select class="form-select" id="backup-hour">
                                        ${Array.from({length: 24}, (_, i) => `<option value="${i}">${i.toString().padStart(2, '0')}:00</option>`).join('')}
                                    </select>
                                </div>
                                <div>
                                    <label class="form-label" for="keep-backups">Keep Backups (days)</label>
                                    <input type="number" class="form-control" id="keep-backups" value="30" min="1" max="365">
                                </div>
                            </div>
                        </div>
                        <button type="submit" class="btn btn-primary mt-3">Save Settings</button>
                        <div id="message" class="mt-3"></div>
                    </form>
                    
                    <div class="form-grid mt-4">
                        <div class="status-section">
                            <h6>Backup Status</h6>
                            <div class="status-item">
                                <span class="status-label">Last Backup:</span>
                                <span class="status-value" id="last-backup-time">Never</span>
                            </div>
                            <div class="status-item">
                                <span class="status-label">Status:</span>
                                <span id="last-backup-status" class="badge bg-secondary">Not configured</span>
                            </div>
                            <div class="status-item">
                                <span class="status-label">Size:</span>
                                <span class="status-value" id="last-backup-size">-</span>
                            </div>
                            <div class="status-item">
                                <span class="status-label">Error:</span>
                                <span class="status-value" id="last-backup-error">-</span>
                            </div>
                        </div>
                        <div class="backup-list-section">
                            <div class="d-flex justify-content-between align-items-center mb-3">
                                <h6>Recent Backups</h6>
                                <button class="btn btn-primary btn-sm" id="load-backup-list-btn">Load</button>
                            </div>
                            <div id="backup-list" class="list-section">
                                <p class="text-muted text-center">Click Load to view backup list</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    setupEventListeners() {
        const form = this.shadowRoot.getElementById('backup-form');
        const testBtn = this.shadowRoot.getElementById('test-connection-btn');
        const backupBtn = this.shadowRoot.getElementById('backup-now-btn');
        const refreshBtn = this.shadowRoot.getElementById('refresh-btn');
        const loadListBtn = this.shadowRoot.getElementById('load-backup-list-btn');
        
        // Prevent double event listeners
        if (!this._listenersAttached) {
            form.addEventListener('submit', this.handleSubmit.bind(this));
            testBtn.addEventListener('click', this.testConnection.bind(this));
            backupBtn.addEventListener('click', this.backupNow.bind(this));
            refreshBtn.addEventListener('click', this.loadBackupData.bind(this));
            loadListBtn.addEventListener('click', this.loadBackupList.bind(this));
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
            this.showError(`Error loading backup settings: ${error.message}`);
        } finally {
            this.setLoading(false);
        }
    }

    updateUI() {
        const settings = this.backupSettings;
        
        this.shadowRoot.getElementById('backup-enabled').checked = settings.enabled || false;
        this.shadowRoot.getElementById('storage-account').value = settings.storage_account || '';
        this.shadowRoot.getElementById('container-name').value = settings.container_name || '';
        this.shadowRoot.getElementById('sas-token').value = settings.sas_token || '';
        this.shadowRoot.getElementById('backup-frequency').value = settings.backup_frequency || 'daily';
        this.shadowRoot.getElementById('backup-hour').value = settings.backup_hour || 2;
        this.shadowRoot.getElementById('keep-backups').value = settings.keep_backups || 30;
        
        // Update status
        const lastTimeElement = this.shadowRoot.getElementById('last-backup-time');
        if (settings.last_backup_time) {
            lastTimeElement.textContent = new Date(settings.last_backup_time).toLocaleString();
        } else {
            lastTimeElement.textContent = 'Never';
        }
        
        const statusElement = this.shadowRoot.getElementById('last-backup-status');
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
                statusElement.className += 'bg-warning';
                break;
            default:
                statusElement.className += 'bg-secondary';
        }
        
        this.shadowRoot.getElementById('last-backup-size').textContent = 
            settings.last_backup_size_mb ? `${settings.last_backup_size_mb} MB` : '-';
        this.shadowRoot.getElementById('last-backup-error').textContent = 
            settings.last_backup_error || '-';
    }

    async handleSubmit(event) {
        event.preventDefault();
        
        this.setLoading(true);
        this.clearMessage();

        try {
            const data = {
                enabled: this.shadowRoot.getElementById('backup-enabled').checked,
                storage_account: this.shadowRoot.getElementById('storage-account').value,
                container_name: this.shadowRoot.getElementById('container-name').value,
                sas_token: this.shadowRoot.getElementById('sas-token').value,
                backup_frequency: this.shadowRoot.getElementById('backup-frequency').value,
                backup_hour: parseInt(this.shadowRoot.getElementById('backup-hour').value),
                keep_backups: parseInt(this.shadowRoot.getElementById('keep-backups').value)
            };

            const response = await this.updateBackupSettings(data);

            if (response.ok) {
                this.showSuccess('Backup settings saved successfully');
                await this.loadBackupData();
                
                this.dispatchEvent(new CustomEvent('backup-updated', { 
                    detail: { settings: data } 
                }));
            } else {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to save backup settings');
            }
        } catch (error) {
            this.showError(`Error saving backup settings: ${error.message}`);
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
                    this.showSuccess('✅ Azure Blob Storage connection successful!');
                } else {
                    this.showError(`❌ Connection test failed: ${result.error}`);
                }
            } else {
                const error = await response.json();
                this.showError(`❌ Connection test failed: ${error.detail}`);
            }
        } catch (error) {
            this.showError(`❌ Error testing backup connection: ${error.message}`);
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
                this.showSuccess(result.message);
                
                // Reload settings after a delay
                setTimeout(() => {
                    this.loadBackupData();
                }, 2000);
                
                this.dispatchEvent(new CustomEvent('backup-started'));
            } else {
                const error = await response.json();
                this.showError(error.detail || 'Failed to start backup');
            }
        } catch (error) {
            this.showError(`Error starting backup: ${error.message}`);
        } finally {
            this.setLoading(false);
        }
    }

    async loadBackupList() {
        const backupListElement = this.shadowRoot.getElementById('backup-list');
        
        try {
            // Show loading state
            backupListElement.innerHTML = '<p class="text-muted">Loading backups...</p>';
            
            const response = await this.fetchBackupList(20);

            if (response.ok) {
                const result = await response.json();
                
                if (result.success) {
                    const backups = result.backups || [];
                    
                    if (backups.length > 0) {
                        const backupItems = backups.map((backup, index) => {
                            // Extract date from filename
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
                            
                            return `<div class="list-item">
                                        <div class="list-item-header">#${index + 1} - ${displayDate}</div>
                                        <div class="list-item-meta">📄 ${backup}</div>
                                    </div>`;
                        }).join('');
                        
                        backupListElement.innerHTML = `
                            <div class="mb-3">
                                <strong>Recent Backups (${result.count} found):</strong>
                            </div>
                            ${backupItems}
                        `;
                    } else {
                        backupListElement.innerHTML = '<div class="text-center text-muted">No backup files found in storage</div>';
                    }
                } else {
                    backupListElement.innerHTML = `<div class="text-center error">Error: ${result.error}</div>`;
                }
            } else {
                const error = await response.json();
                backupListElement.innerHTML = `<div class="text-center error">API Error: ${error.detail || 'Unknown error'}</div>`;
            }
        } catch (error) {
            backupListElement.innerHTML = `<div class="text-center error">Error: ${error.message}</div>`;
        }
    }

    // API methods
    async fetchBackupSettings() {
        return fetch('/admin/api/backup/settings', {
            headers: { 'Authorization': `Bearer ${this.getAuthToken()}` }
        });
    }

    async updateBackupSettings(data) {
        return fetch('/admin/api/backup/settings', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${this.getAuthToken()}`
            },
            body: JSON.stringify(data)
        });
    }

    async testBackupConnection() {
        return fetch('/admin/api/backup/test-connection', {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${this.getAuthToken()}` }
        });
    }

    async startBackupNow() {
        return fetch('/admin/api/backup/backup-now', {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${this.getAuthToken()}` }
        });
    }

    async fetchBackupList(limit = 20) {
        return fetch(`/admin/api/backup/list?limit=${limit}`, {
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
    getBackupSettings() {
        return this.backupSettings;
    }

    async refresh() {
        await this.loadBackupData();
    }
}

// Register the custom element
customElements.define('backup-manager', BackupManager);
