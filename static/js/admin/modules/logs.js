/* Logs Module - Application logs management functionality */

const AdminLogs = {
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

        console.log('Logs module initialized');
    }
};

// Export for global access
window.AdminLogs = AdminLogs;

// Initialize when module loads
AdminLogs.init();

console.log('Admin logs module loaded!');
