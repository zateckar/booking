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
                
                AdminNotifications.show('Log configuration updated successfully', 'success');
                
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
        
        // Override console methods based on log level
        const levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'];
        const currentLevelIndex = levels.indexOf(level);
        
        // Reset console methods to original
        if (window.originalConsole) {
            console.log = window.originalConsole.log;
            console.info = window.originalConsole.info;
            console.warn = window.originalConsole.warn;
            console.error = window.originalConsole.error;
        } else {
            // Store original console methods
            window.originalConsole = {
                log: console.log.bind(console),
                info: console.info.bind(console),
                warn: console.warn.bind(console),
                error: console.error.bind(console)
            };
        }
        
        // Disable logging methods below the current level
        if (currentLevelIndex > 0) { // Disable DEBUG
            console.log = () => {};
        }
        if (currentLevelIndex > 1) { // Disable INFO
            console.info = () => {};
        }
        if (currentLevelIndex > 2) { // Disable WARNING
            console.warn = () => {};
        }
        if (currentLevelIndex > 3) { // Disable ERROR
            console.error = () => {};
        }
    },

    // Frontend logging method that respects log level
    log(level, message, ...args) {
        const levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'];
        const currentLevel = localStorage.getItem('frontend_log_level') || this.currentConfig.frontend_log_level;
        const currentLevelIndex = levels.indexOf(currentLevel);
        const messageLevelIndex = levels.indexOf(level);
        
        if (messageLevelIndex >= currentLevelIndex) {
            const timestamp = new Date().toISOString();
            const logMessage = `[${timestamp}] [${level}] ${message}`;
            
            switch (level) {
                case 'DEBUG':
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

        // Load initial configuration
        this.loadLogConfig();

        // Initialize frontend log level from localStorage or config
        const savedLevel = localStorage.getItem('frontend_log_level');
        if (savedLevel) {
            this.setFrontendLogLevel(savedLevel);
        }

        this.log('INFO', 'Logs module initialized');
    }
};

// Export for global access
window.AdminLogs = AdminLogs;

// Initialize when module loads
AdminLogs.init();

console.log('Admin logs module loaded!');
