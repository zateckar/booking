/*
 * Frontend Logging Service
 * Provides a global `AdminLogs.log` method that respects the log level
 * set in the application configuration.
 */
const AdminLogs = {
    currentLogLevel: 'INFO',
    originalConsole: {},

    // Set frontend log level for console logging
    setFrontendLogLevel(level) {
        localStorage.setItem('frontend_log_level', level);
        this.currentLogLevel = level;
        this.log('INFO', `Frontend log level changed to: ${level}`);
    },

    // Frontend logging method that respects log level
    log(level, message, ...args) {
        const levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'];
        const currentLevelIndex = levels.indexOf(this.currentLogLevel);
        const messageLevelIndex = levels.indexOf(level);

        if (messageLevelIndex >= currentLevelIndex) {
            const timestamp = new Date().toISOString();
            const logMessage = `[${timestamp}] [FRONTEND-${level}] ${message}`;
            
            const consoleMethod = level.toLowerCase() === 'warning' ? 'warn' : level.toLowerCase();
            const effectiveMethod = this.originalConsole[consoleMethod] || this.originalConsole.log;
            
            if (effectiveMethod) {
                effectiveMethod(logMessage, ...args);
            }
        }
    },

    // Initialize the logging service
    async init() {
        // Store references to original console methods
        this.originalConsole = {
            log: console.log.bind(console),
            info: console.info.bind(console),
            warn: console.warn.bind(console),
            error: console.error.bind(console),
            debug: console.debug ? console.debug.bind(console) : console.log.bind(console)
        };

        // Attempt to load log level from config
        try {
            const savedLevel = localStorage.getItem('frontend_log_level');
            if (savedLevel) {
                this.currentLogLevel = savedLevel;
            } else {
                const response = await AdminAPI.logs.getLogConfig();
                if (response && response.ok) {
                    const config = await response.json();
                    this.currentLogLevel = config.frontend_log_level || 'INFO';
                } else {
                    this.currentLogLevel = 'INFO';
                }
            }
        } catch (error) {
            this.originalConsole.error('Failed to load frontend log level from API, defaulting to INFO.', error);
            this.currentLogLevel = 'INFO';
        } finally {
            localStorage.setItem('frontend_log_level', this.currentLogLevel);
            this.log('INFO', `Logging service initialized with level: ${this.currentLogLevel}`);
        }
    }
};

// Initialize and export for global access
(async () => {
    const queuedLogs = window.queuedLogs || [];
    
    // Replace the stub with the real object
    window.AdminLogs = AdminLogs;
    await AdminLogs.init();

    // Process any queued logs
    if (queuedLogs.length > 0) {
        AdminLogs.log('INFO', `Processing ${queuedLogs.length} queued log entries...`);
        queuedLogs.forEach(log => {
            AdminLogs.log(log.level, log.message, ...log.args);
        });
        // Clear the queue
        window.queuedLogs = [];
    }
    
    console.log('Admin logging service loaded!');
})();
