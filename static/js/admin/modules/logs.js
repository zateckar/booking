/* Logs Module - Application logs management functionality */

const AdminLogs = {
    currentConfig: {
        backend_log_level: 'INFO',
        frontend_log_level: 'INFO'
    },

    // Load current log configuration
    async loadLogConfig() {
        try {
            const response = await AdminAPI.logs.getLogConfig();
            if (response.ok) {
                const config = await response.json();
                this.currentConfig = config;
                this.updateConfigUI(config);
            }
        } catch (error) {
            console.error('Error loading log configuration:', error);
            AdminNotifications.handleApiError(error, 'Failed to load log configuration');
        }
    },

    // Update log configuration UI
    updateConfigUI(config) {
        const backendSelect = document.getElementById('backend-log-level');
        const frontendSelect = document.getElementById('frontend-log-level');
        
        if (backendSelect) {
            backendSelect.value = config.backend_log_level;
        }
        if (frontendSelect) {
            frontendSelect.value = config.frontend_log_level;
        }

        // Update status badges
        const currentBackendLevel = document.getElementById('current-backend-level');
        const currentFrontendLevel = document.getElementById('current-frontend-level');
        const configLastUpdated = document.getElementById('config-last-updated');
        
        if (currentBackendLevel) {
            currentBackendLevel.textContent = config.backend_log_level;
        }
        if (currentFrontendLevel) {
            currentFrontendLevel.textContent = config.frontend_log_level;
        }
        if (configLastUpdated) {
            configLastUpdated.textContent = new Date().toLocaleString();
        }
    },

    // Update log configuration
    async updateLogConfig(backend_level, frontend_level) {
        try {
            const updateData = {};
            if (backend_level) updateData.backend_log_level = backend_level;
            if (frontend_level) updateData.frontend_log_level = frontend_level;

            const response = await AdminAPI.logs.updateLogConfig(updateData);
            if (response.ok) {
                const config = await response.json();
                this.currentConfig = config;
                this.updateConfigUI(config);
                
                // Update frontend logging level immediately
                if (frontend_level) {
                    this.setFrontendLogLevel(frontend_level);
                }
                
                AdminNotifications.showSuccess('Log configuration updated successfully');
                
                // Log the change
                this.log('INFO', `Log levels updated - Backend: ${config.backend_log_level}, Frontend: ${config.frontend_log_level}`);
            } else {
                throw new Error('Failed to update log configuration');
            }
        } catch (error) {
            console.error('Error updating log configuration:', error);
            AdminNotifications.handleApiError(error, 'Failed to update log configuration');
        }
    },

    // Set frontend log level for console logging
    setFrontendLogLevel(level) {
        // Store the log level for frontend logging
        localStorage.setItem('frontend_log_level', level);
        
        // Store reference to original console methods if not already done
        if (!window.originalConsole) {
            window.originalConsole = {
                log: console.log.bind(console),
                info: console.info.bind(console),
                warn: console.warn.bind(console),
                error: console.error.bind(console),
                debug: console.debug ? console.debug.bind(console) : console.log.bind(console)
            };
        }
        
        // Override the global AdminLogs.log method to respect new level
        this.currentLogLevel = level;
        
        // Log level change
        this.log('INFO', `Frontend log level changed to: ${level}`);
    },

    // Frontend logging method that respects log level
    log(level, message, ...args) {
        const levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'];
        const currentLevel = this.currentLogLevel || localStorage.getItem('frontend_log_level') || this.currentConfig.frontend_log_level || 'INFO';
        const currentLevelIndex = levels.indexOf(currentLevel);
        const messageLevelIndex = levels.indexOf(level);
        
        // Only log if message level is >= current level
        if (messageLevelIndex >= currentLevelIndex) {
            const timestamp = new Date().toISOString();
            const logMessage = `[${timestamp}] [FRONTEND-${level}] ${message}`;
            
            // Use original console methods to avoid infinite loops
            switch (level) {
                case 'DEBUG':
                    if (window.originalConsole && window.originalConsole.debug) {
                        window.originalConsole.debug(logMessage, ...args);
                    } else {
                        window.originalConsole ? window.originalConsole.log(logMessage, ...args) : console.log(logMessage, ...args);
                    }
                    break;
                case 'INFO':
                    window.originalConsole ? window.originalConsole.info(logMessage, ...args) : console.info(logMessage, ...args);
                    break;
                case 'WARNING':
                    window.originalConsole ? window.originalConsole.warn(logMessage, ...args) : console.warn(logMessage, ...args);
                    break;
                case 'ERROR':
                case 'CRITICAL':
                    window.originalConsole ? window.originalConsole.error(logMessage, ...args) : console.error(logMessage, ...args);
                    break;
            }
        }
    },

    // Load logs with filtering
    async loadLogs() {
        const tbody = document.getElementById('logs-table-body');
        if (!tbody) return;
        
        tbody.innerHTML = '<tr><td colspan="5" class="text-center">Loading...</td></tr>';
        
        try {
            const params = {
                limit: '50'
            };
            
            const level = document.getElementById('log-level-filter')?.value;
            if (level) params.level = level;

            const loggerName = document.getElementById('log-logger-filter')?.value;
            if (loggerName) params.logger_name = loggerName;

            const startDate = document.getElementById('log-start-date')?.value;
            if (startDate) params.start_time = new Date(startDate).toISOString();

            const endDate = document.getElementById('log-end-date')?.value;
            if (endDate) params.end_time = new Date(endDate).toISOString();

            const response = await AdminAPI.logs.getLogs(params);

            if (response.ok) {
                const logs = await response.json();
                tbody.innerHTML = '';
                logs.forEach(log => {
                    const row = document.createElement('tr');
                    const levelClass = log.level === 'ERROR' || log.level === 'CRITICAL' ? 'text-danger' : 
                                      log.level === 'WARNING' ? 'text-warning' : '';
                    row.innerHTML = `
                        <td>${log.timestamp_formatted || new Date(log.timestamp).toLocaleString()}</td>
                        <td><span class="badge bg-secondary ${levelClass}">${log.level}</span></td>
                        <td>${log.logger_name}</td>
                        <td style="max-width: 300px; word-wrap: break-word;">${log.message}</td>
                        <td>${log.user ? log.user.email : '-'}</td>
                    `;
                    tbody.appendChild(row);
                });
            } else {
                tbody.innerHTML = '<tr><td colspan="5" class="text-center text-danger">Failed to load logs</td></tr>';
            }
        } catch (error) {
            tbody.innerHTML = '<tr><td colspan="5" class="text-center text-danger">Error loading logs</td></tr>';
            AdminNotifications.handleApiError(error, 'Failed to load logs');
        }
    },

    // Load logger names for filter dropdown
    async loadLoggerNames() {
        try {
            const response = await AdminAPI.logs.getLoggers();

            if (response.ok) {
                const loggers = await response.json();
                const select = document.getElementById('log-logger-filter');
                if (select) {
                    select.innerHTML = '<option value="">All Loggers</option>';
                    loggers.forEach(logger => {
                        const option = document.createElement('option');
                        option.value = logger;
                        option.textContent = logger;
                        select.appendChild(option);
                    });
                }
            }
        } catch (error) {
            console.error('Error loading logger names:', error);
        }
    },

    // Cleanup old logs
    async cleanupOldLogs() {
        const days = await AdminNotifications.prompt('Delete logs older than how many days?', '30');
        if (!days || isNaN(days) || days < 1) return;

        const confirmed = await AdminNotifications.confirm(`Are you sure you want to delete logs older than ${days} days? This action cannot be undone.`);
        if (!confirmed) return;

        AdminNotifications.showInfo('Cleaning up old logs...');

        try {
            const response = await AdminAPI.logs.cleanup(days);

            if (response.ok) {
                const result = await response.json();
                const message = `Cleanup completed! Deleted ${result.deleted_count} log entries older than ${new Date(result.cutoff_date).toLocaleString()}.`;
                AdminNotifications.showSuccess(message);
                this.loadLogs(); // Refresh logs view
            } else {
                const error = await response.json();
                AdminNotifications.showError(`Failed to cleanup logs: ${error.detail || 'Unknown error'}`);
            }
        } catch (error) {
            AdminNotifications.handleApiError(error, 'Error during log cleanup');
        }
    },

    // Initialize logs module
    init() {
        // Setup filter event listeners
        const logFilters = ['log-level-filter', 'log-logger-filter', 'log-start-date', 'log-end-date'];
        logFilters.forEach(filterId => {
            const element = document.getElementById(filterId);
            if (element) {
                element.addEventListener('change', this.loadLogs.bind(this));
            }
        });

        const refreshBtn = document.getElementById('refresh-logs-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', this.loadLogs.bind(this));
        }

        const cleanupBtn = document.getElementById('cleanup-old-logs-btn');
        if (cleanupBtn) {
            cleanupBtn.addEventListener('click', this.cleanupOldLogs.bind(this));
        }

        // Setup log configuration event listeners
        const backendSelect = document.getElementById('backend-log-level');
        if (backendSelect) {
            backendSelect.addEventListener('change', (e) => {
                this.updateLogConfig(e.target.value, null);
            });
        }

        const frontendSelect = document.getElementById('frontend-log-level');
        if (frontendSelect) {
            frontendSelect.addEventListener('change', (e) => {
                this.updateLogConfig(null, e.target.value);
            });
        }

        // Load initial configuration and set frontend log level
        this.loadLogConfig().then(() => {
            // Initialize frontend log level from config
            const savedLevel = localStorage.getItem('frontend_log_level') || this.currentConfig.frontend_log_level;
            if (savedLevel) {
                this.setFrontendLogLevel(savedLevel);
            }
            this.log('INFO', 'Logs module initialized with log level: ' + savedLevel);
        }).catch(error => {
            console.error('Failed to load log config during initialization:', error);
            // Set default level
            this.setFrontendLogLevel('INFO');
            this.log('INFO', 'Logs module initialized with default log level');
        });
    }
};

// Export for global access
window.AdminLogs = AdminLogs;

// Initialize when module loads
AdminLogs.init();

console.log('Admin logs module loaded!');
