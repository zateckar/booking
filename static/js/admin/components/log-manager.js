/**
 * Log Manager Web Component
 * Interface for viewing logs and managing log levels.
 */
class LogManager extends HTMLElement {
    constructor() {
        super();
        this.logLevels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'];
        this.loggers = [];
        this.logs = [];
        this.config = {
            backend_log_level: 'INFO',
            frontend_log_level: 'INFO'
        };
    }

    connectedCallback() {
        this.render();
        this.setupEventListeners();
        this.loadInitialData();
    }

    render() {
        this.innerHTML = `
            <style>
                .card-header {
                    background-color: var(--bs-primary);
                    color: var(--bs-light);
                }
                .btn-danger {
                    background-color: var(--bs-danger);
                }
            </style>
            <div class="card shadow-sm mb-4">
                <div class="card-header d-flex justify-content-between align-items-center">
                    <h5 class="card-title mb-0"><i class="fas fa-cogs me-2"></i>Log Configuration</h5>
                    <button class="btn btn-light btn-sm" id="refresh-config-btn" title="Refresh Config">Refresh</button>
                </div>
                <div class="card-body">
                    <form id="log-config-form">
                        <div class="row">
                            <div class="col-md-6 mb-3">
                                <label for="backend-log-level" class="form-label">Backend Log Level</label>
                                <select id="backend-log-level" class="form-select">
                                    ${this.logLevels.map(level => `<option value="${level}">${level}</option>`).join('')}
                                </select>
                            </div>
                            <div class="col-md-6 mb-3">
                                <label for="frontend-log-level" class="form-label">Frontend Log Level</label>
                                <select id="frontend-log-level" class="form-select">
                                    ${this.logLevels.map(level => `<option value="${level}">${level}</option>`).join('')}
                                </select>
                            </div>
                        </div>
                    </form>
                    <div id="config-message-container"></div>
                </div>
            </div>

            <div class="card shadow-sm">
                <div class="card-header d-flex justify-content-between align-items-center">
                    <h5 class="card-title mb-0"><i class="fas fa-clipboard-list me-2"></i>Log Viewer</h5>
                    <div>
                        <button class="btn btn-warning btn-sm me-2" id="vacuum-db-btn" title="Vacuum Database">
                            <i class="fas fa-database me-1"></i> Vacuum
                        </button>
                        <button class="btn btn-danger btn-sm me-2" id="cleanup-logs-btn" title="Cleanup Old Logs">
                            <i class="fas fa-trash-alt me-1"></i> Cleanup
                        </button>
                        <button class="btn btn-light btn-sm" id="refresh-logs-btn" title="Refresh Logs">
                            <i class="fas fa-sync-alt me-1"></i> Refresh
                        </button>
                    </div>
                </div>
                <div class="card-body">
                    <div class="row mb-3">
                        <div class="col-md-3">
                            <label for="log-level-filter" class="form-label">Level</label>
                            <select id="log-level-filter" class="form-select form-select-sm">
                                <option value="">All</option>
                                ${this.logLevels.map(level => `<option value="${level}">${level}</option>`).join('')}
                            </select>
                        </div>
                        <div class="col-md-3">
                            <label for="log-logger-filter" class="form-label">Logger</label>
                            <select id="log-logger-filter" class="form-select form-select-sm">
                                <option value="">All Loggers</option>
                            </select>
                        </div>
                        <div class="col-md-3">
                            <label for="log-start-date" class="form-label">Start Date</label>
                            <input type="datetime-local" id="log-start-date" class="form-control form-control-sm">
                        </div>
                        <div class="col-md-3">
                            <label for="log-end-date" class="form-label">End Date</label>
                            <input type="datetime-local" id="log-end-date" class="form-control form-control-sm">
                        </div>
                    </div>
                    <div class="table-responsive">
                        <table class="table table-striped table-hover">
                            <thead>
                                <tr>
                                    <th>Timestamp</th>
                                    <th>Level</th>
                                    <th>Logger</th>
                                    <th>Message</th>
                                    <th>User</th>
                                </tr>
                            </thead>
                            <tbody id="logs-table-body">
                                <tr><td colspan="5" class="text-center">Loading logs...</td></tr>
                            </tbody>
                        </table>
                    </div>
                    <div id="logs-message-container" class="mt-3"></div>
                </div>
                <div id="loading-overlay" class="position-absolute top-0 start-0 w-100 h-100 d-none" style="background: rgba(255,255,255,0.8); z-index: 10;">
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
        // Config
        this.querySelector('#refresh-config-btn').addEventListener('click', () => this.loadLogConfig());
        this.querySelector('#backend-log-level').addEventListener('change', (e) => this.handleUpdateLogConfig({ backend_log_level: e.target.value }));
        this.querySelector('#frontend-log-level').addEventListener('change', (e) => this.handleUpdateLogConfig({ frontend_log_level: e.target.value }));

        // Logs
        this.querySelector('#refresh-logs-btn').addEventListener('click', () => this.loadLogs());
        this.querySelector('#cleanup-logs-btn').addEventListener('click', () => this.cleanupOldLogs());
        this.querySelector('#vacuum-db-btn').addEventListener('click', () => this.vacuumDatabase());

        // Filters
        this.querySelector('#log-level-filter').addEventListener('change', () => this.loadLogs());
        this.querySelector('#log-logger-filter').addEventListener('change', () => this.loadLogs());
        this.querySelector('#log-start-date').addEventListener('change', () => this.loadLogs());
        this.querySelector('#log-end-date').addEventListener('change', () => this.loadLogs());
    }

    async loadInitialData() {
        this.setLoading(true);
        await Promise.all([
            this.loadLogConfig(),
            this.loadLoggerNames(),
            this.loadLogs()
        ]);
        this.setLoading(false);
    }

    // --- API Methods ---
    fetchLogConfig() {
        return window.AdminAPI.logs.getLogConfig();
    }

    updateLogConfig(data) {
        return window.AdminAPI.logs.updateLogConfig(data);
    }

    fetchLogs(params) {
        return window.AdminAPI.logs.getLogs(params);
    }

    fetchLoggerNames() {
        return window.AdminAPI.logs.getLoggers();
    }

    cleanupLogs(days) {
        return window.AdminAPI.logs.cleanup(days);
    }

    vacuumDb() {
        return window.AdminAPI.logs.vacuum();
    }

    // --- CONFIGURATION ---
    async loadLogConfig() {
        this.setLoading(true);
        try {
            const response = await this.fetchLogConfig();
            if (!response.ok) throw new Error('Failed to fetch log config');
            this.config = await response.json();
            this.updateConfigUI();
            this.showMessage('config-message-container', 'Configuration loaded.', 'success');
        } catch (error) {
            this.showMessage('config-message-container', `Error loading log configuration: ${error.message}`, 'danger');
        } finally {
            this.setLoading(false);
        }
    }

    updateConfigUI() {
        this.querySelector('#backend-log-level').value = this.config.backend_log_level;
        this.querySelector('#frontend-log-level').value = this.config.frontend_log_level;
    }

    async handleUpdateLogConfig(updateData) {
        this.setLoading(true);
        try {
            const response = await this.updateLogConfig(updateData);
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to update log config');
            }
            this.config = await response.json();
            this.updateConfigUI();
            this.showMessage('config-message-container', 'Log configuration updated successfully!', 'success');
            
            if (updateData.frontend_log_level && window.AdminLogs) {
                window.AdminLogs.setFrontendLogLevel(updateData.frontend_log_level);
            }

        } catch (error) {
            this.showMessage('config-message-container', `Error updating log configuration: ${error.message}`, 'danger');
        } finally {
            this.setLoading(false);
        }
    }

    // --- LOGS ---
    async loadLogs() {
        this.setLoading(true);
        const tbody = this.querySelector('#logs-table-body');
        tbody.innerHTML = '<tr><td colspan="5" class="text-center">Loading...</td></tr>';

        try {
            const params = { limit: '100' };
            const level = this.querySelector('#log-level-filter').value;
            const loggerName = this.querySelector('#log-logger-filter').value;
            const startTime = this.querySelector('#log-start-date').value;
            const endTime = this.querySelector('#log-end-date').value;

            if (level) params.level = level;
            if (loggerName) params.logger_name = loggerName;
            if (startTime) params.start_time = new Date(startTime).toISOString();
            if (endTime) params.end_time = new Date(endTime).toISOString();

            const response = await this.fetchLogs(params);
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: 'Failed to fetch logs' }));
                throw new Error(errorData.detail);
            }
            this.logs = await response.json();
            this.renderLogs();
        } catch (error) {
            this.showMessage('logs-message-container', `Error loading logs: ${error.message}`, 'danger');
            tbody.innerHTML = '<tr><td colspan="5" class="text-center text-danger">Failed to load logs.</td></tr>';
        } finally {
            this.setLoading(false);
        }
    }

    renderLogs() {
        const tbody = this.querySelector('#logs-table-body');
        tbody.innerHTML = '';
        if (this.logs.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="text-center">No logs found.</td></tr>';
            return;
        }
        this.logs.forEach(log => {
            const row = document.createElement('tr');
            const levelClass = log.level === 'ERROR' || log.level === 'CRITICAL' ? 'text-danger' :
                              log.level === 'WARNING' ? 'text-warning' : '';
            row.innerHTML = `
                <td>${new Date(log.timestamp).toLocaleString()}</td>
                <td><span class="badge bg-secondary ${levelClass}">${log.level}</span></td>
                <td>${log.logger_name}</td>
                <td style="max-width: 300px; word-wrap: break-word;">${log.message}</td>
                <td>${log.user ? log.user.email : '-'}</td>
            `;
            tbody.appendChild(row);
        });
    }

    async loadLoggerNames() {
        try {
            const response = await this.fetchLoggerNames();
            if (!response.ok) throw new Error('Failed to fetch logger names');
            this.loggers = await response.json();
            const select = this.querySelector('#log-logger-filter');
            select.innerHTML = '<option value="">All Loggers</option>';
            this.loggers.forEach(logger => {
                const option = document.createElement('option');
                option.value = logger;
                option.textContent = logger;
                select.appendChild(option);
            });
        } catch (error) {
            this.showMessage('logs-message-container', `Error loading logger names: ${error.message}`, 'warning');
        }
    }

    async cleanupOldLogs() {
        const days = prompt('Delete logs older than how many days?', '30');
        if (!days || isNaN(days) || days < 1) return;

        if (!confirm(`Are you sure you want to delete logs older than ${days} days? This action cannot be undone.`)) return;

        this.setLoading(true);
        try {
            const response = await this.cleanupLogs(days);
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Cleanup failed');
            }
            const result = await response.json();
            this.showMessage('logs-message-container', `Cleanup completed! Deleted ${result.deleted_count} log entries.`, 'success');
            this.loadLogs();
        } catch (error) {
            this.showMessage('logs-message-container', `Error during log cleanup: ${error.message}`, 'danger');
        } finally {
            this.setLoading(false);
        }
    }

    async vacuumDatabase() {
        if (!confirm('Are you sure you want to vacuum the database? This may take a while and will lock the database.')) return;

        this.setLoading(true);
        try {
            const response = await this.vacuumDb();
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Vacuum failed');
            }
            this.showMessage('logs-message-container', 'Database vacuumed successfully!', 'success');
        } catch (error) {
            this.showMessage('logs-message-container', `Error during database vacuum: ${error.message}`, 'danger');
        } finally {
            this.setLoading(false);
        }
    }

    // --- UTILITIES ---
    setLoading(loading) {
        const overlay = this.querySelector('#loading-overlay');
        if (overlay) {
            overlay.classList.toggle('d-none', !loading);
        }
    }

    showMessage(containerId, message, type = 'info') {
        const container = this.querySelector(`#${containerId}`);
        if (!container) return;
        const alertClass = `alert alert-${type} alert-dismissible fade show`;
        container.innerHTML = `
            <div class="${alertClass}" role="alert">
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>
        `;
        if (type === 'success') {
            setTimeout(() => container.innerHTML = '', 5000);
        }
    }
}

customElements.define('log-manager', LogManager);
