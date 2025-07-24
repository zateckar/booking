/* Backup System Module - Database backup and system management */

const AdminBackup = {
    // Load backup settings
    async loadBackupSettings() {
        try {
            // Load both backup and timezone settings
            await Promise.all([
                this.loadBackupData(),
                this.loadTimezoneSettings()
            ]);
        } catch (error) {
            AdminNotifications.handleApiError(error, 'Error loading system settings');
        }
    },

    // Load backup data
    async loadBackupData() {
        try {
            const response = await AdminAPI.backup.getSettings();

            if (response.ok) {
                const settings = await response.json();
                
                // Populate backup settings form
                document.getElementById('backup-enabled').checked = settings.enabled || false;
                document.getElementById('backup-storage-account').value = settings.storage_account || '';
                document.getElementById('backup-container-name').value = settings.container_name || '';
                document.getElementById('backup-sas-token').value = settings.sas_token || '';
                document.getElementById('backup-frequency').value = settings.backup_frequency || 'daily';
                document.getElementById('backup-hour').value = settings.backup_hour || 2;
                document.getElementById('backup-keep-backups').value = settings.keep_backups || 30;
                
                // Update backup status display
                this.updateBackupStatusDisplay(settings);
                
            } else {
                AdminNotifications.showError('Failed to load backup settings');
            }
        } catch (error) {
            AdminNotifications.handleApiError(error, 'Error loading backup settings');
        }
    },

    // Load timezone settings
    async loadTimezoneSettings() {
        try {
            const [settingsResponse, timezonesResponse] = await Promise.all([
                AdminAPI.timezone.getSettings(),
                AdminAPI.timezone.getTimezones()
            ]);

            if (settingsResponse.ok && timezonesResponse.ok) {
                const settings = await settingsResponse.json();
                const timezones = await timezonesResponse.json();
                
                document.getElementById('current-timezone').value = settings.timezone;
                
                const select = document.getElementById('available-timezones');
                select.innerHTML = '<option value="">Select Timezone</option>';
                // timezones is an array of objects with value, label, common properties
                timezones.forEach(tz => {
                    const option = document.createElement('option');
                    option.value = tz.value;
                    option.textContent = tz.label;
                    if (tz.value === settings.timezone) {
                        option.selected = true;
                    }
                    select.appendChild(option);
                });
            } else {
                AdminNotifications.showError('Failed to load timezone settings');
            }
        } catch (error) {
            AdminNotifications.handleApiError(error, 'Error loading timezone settings');
        }
    },

    // Update backup status display
    updateBackupStatusDisplay(settings) {
        // Update last backup time
        const lastTimeElement = document.getElementById('backup-last-time');
        if (lastTimeElement) {
            if (settings.last_backup_time) {
                const lastTime = new Date(settings.last_backup_time).toLocaleString();
                lastTimeElement.textContent = lastTime;
            } else {
                lastTimeElement.textContent = 'Never';
            }
        }
        
        // Update backup status
        const statusElement = document.getElementById('backup-last-status');
        if (statusElement) {
            const status = settings.last_backup_status || 'Not configured';
            statusElement.textContent = status;
            
            // Set appropriate badge class
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
        }
        
        // Update backup size
        const sizeElement = document.getElementById('backup-last-size');
        if (sizeElement) {
            if (settings.last_backup_size_mb) {
                sizeElement.textContent = `${settings.last_backup_size_mb} MB`;
            } else {
                sizeElement.textContent = '-';
            }
        }
        
        // Update backup error
        const errorElement = document.getElementById('backup-last-error');
        if (errorElement) {
            if (settings.last_backup_error) {
                errorElement.textContent = settings.last_backup_error;
            } else {
                errorElement.textContent = '-';
            }
        }
    },

    // Handle backup settings form submission
    async handleBackupSettingsSubmit(event) {
        event.preventDefault();
        
        try {
            const data = {
                enabled: document.getElementById('backup-enabled').checked,
                storage_account: document.getElementById('backup-storage-account').value,
                container_name: document.getElementById('backup-container-name').value,
                sas_token: document.getElementById('backup-sas-token').value,
                backup_frequency: document.getElementById('backup-frequency').value,
                backup_hour: parseInt(document.getElementById('backup-hour').value),
                keep_backups: parseInt(document.getElementById('backup-keep-backups').value)
            };

            const response = await AdminAPI.backup.updateSettings(data);

            if (response.ok) {
                AdminNotifications.showSuccess('Backup settings saved successfully');
                this.loadBackupSettings(); // Reload to show updated settings
            } else {
                const error = await response.json();
                AdminNotifications.showError(error.detail || 'Failed to save backup settings');
            }
        } catch (error) {
            AdminNotifications.handleApiError(error, 'Error saving backup settings');
        }
    },

    // Test backup connection
    async testBackupConnection() {
        try {
            AdminNotifications.showInfo('Testing backup connection...');
            
            const response = await AdminAPI.backup.testConnection();

            if (response.ok) {
                const result = await response.json();
                if (result.success) {
                    AdminNotifications.showSuccess('✅ Azure Blob Storage connection successful!');
                } else {
                    AdminNotifications.showError(`❌ Connection test failed: ${result.error}`);
                }
            } else {
                const error = await response.json();
                AdminNotifications.showError(`❌ Connection test failed: ${error.detail}`);
            }
        } catch (error) {
            AdminNotifications.handleApiError(error, '❌ Error testing backup connection');
        }
    },

    // Start backup now
    async backupNow() {
        const confirmed = await AdminNotifications.confirm('Are you sure you want to start a backup now?');
        if (!confirmed) return;
        
        try {
            AdminNotifications.showInfo('Starting backup...');
            
            const response = await AdminAPI.backup.backupNow();

            if (response.ok) {
                const result = await response.json();
                AdminNotifications.showSuccess(result.message);
                
                // Reload settings to show updated status
                setTimeout(() => {
                    this.loadBackupSettings();
                }, 2000);
            } else {
                const error = await response.json();
                AdminNotifications.showError(error.detail || 'Failed to start backup');
            }
        } catch (error) {
            AdminNotifications.handleApiError(error, 'Error starting backup');
        }
    },

    // Load backup list
    async loadBackupList() {
        const backupListElement = document.getElementById('backup-list');
        
        try {
            console.log('🔍 Loading backup list...');
            
            if (!backupListElement) {
                console.error('❌ backup-list element not found in DOM');
                return;
            }
            
            // Show loading state
            backupListElement.innerHTML = '<p class="text-muted">Loading backups...</p>';
            
            // Request backups
            const response = await AdminAPI.backup.listBackups(20);
            console.log('📡 Backup API response:', response);

            if (response.ok) {
                const result = await response.json();
                console.log('📋 Backup list result:', result);
                
                if (result.success) {
                    const backups = result.backups || [];
                    console.log(`✅ Found ${backups.length} backups`);
                    
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
                            
                            return `<div class="mb-1 p-2 border rounded">
                                        <div class="small">
                                            <strong>#${index + 1}</strong> - ${displayDate}
                                        </div>
                                        <div class="text-muted small">📄 ${backup}</div>
                                    </div>`;
                        }).join('');
                        
                        backupListElement.innerHTML = `
                            <div class="mb-2">
                                <strong>Recent Backups (${result.count} found):</strong>
                            </div>
                            ${backupItems}
                        `;
                    } else {
                        backupListElement.innerHTML = '<div class="alert alert-info">No backup files found in storage</div>';
                    }
                } else {
                    console.error('❌ Backup list failed:', result.error);
                    backupListElement.innerHTML = `<div class="alert alert-danger">Error: ${result.error}</div>`;
                }
            } else {
                console.error('❌ API request failed:', response.status, response.statusText);
                try {
                    const error = await response.json();
                    backupListElement.innerHTML = `<div class="alert alert-danger">API Error: ${error.detail || 'Unknown error'}</div>`;
                } catch {
                    backupListElement.innerHTML = `<div class="alert alert-danger">Failed to load backups (HTTP ${response.status})</div>`;
                }
            }
        } catch (error) {
            console.error('❌ Exception in loadBackupList:', error);
            if (backupListElement) {
                backupListElement.innerHTML = `<div class="alert alert-danger">Error: ${error.message}</div>`;
            }
            AdminNotifications.handleApiError(error, 'Error loading backup list');
        }
    },

    // Test admin API
    async testAdminAPI() {
        const resultsElement = document.getElementById('admin-test-results');
        if (!resultsElement) return;
        
        resultsElement.textContent = 'Testing admin API access...\n';
        
        try {
            const response = await AdminAPI.users.getAll();

            if (response.ok) {
                const users = await response.json();
                resultsElement.textContent += `✅ Admin API access successful!\n`;
                resultsElement.textContent += `Found ${users.length} users in the system.\n`;
                resultsElement.textContent += `Response status: ${response.status}\n`;
            } else {
                resultsElement.textContent += `❌ Admin API access failed!\n`;
                resultsElement.textContent += `Response status: ${response.status}\n`;
                const errorText = await response.text();
                resultsElement.textContent += `Error: ${errorText}\n`;
            }
        } catch (error) {
            resultsElement.textContent += `❌ Error testing admin API: ${error.message}\n`;
            AdminNotifications.handleApiError(error, 'Error testing admin API');
        }
    },

    // Load log statistics
    async loadLogStats() {
        const resultsElement = document.getElementById('admin-test-results');
        if (!resultsElement) return;
        
        resultsElement.textContent = 'Loading log statistics...\n';
        
        try {
            const response = await AdminAPI.logs.getStats(24);

            if (response.ok) {
                const stats = await response.json();
                resultsElement.textContent = `Log Statistics (Last 24 Hours):\n\n`;
                resultsElement.textContent += `Total Logs: ${stats.total_logs}\n`;
                resultsElement.textContent += `Error Count: ${stats.error_count}\n\n`;
                resultsElement.textContent += `By Level:\n`;
                Object.entries(stats.level_counts).forEach(([level, count]) => {
                    resultsElement.textContent += `  ${level}: ${count}\n`;
                });
                resultsElement.textContent += `\nTop Loggers:\n`;
                stats.top_loggers.forEach((logger, index) => {
                    resultsElement.textContent += `  ${index + 1}. ${logger.name}: ${logger.count}\n`;
                });
            } else {
                resultsElement.textContent += `❌ Failed to load log statistics\n`;
            }
        } catch (error) {
            resultsElement.textContent += `❌ Error loading log statistics: ${error.message}\n`;
            AdminNotifications.handleApiError(error, 'Error loading log statistics');
        }
    },

    // Cleanup old logs
    async cleanupOldLogs() {
        const days = await AdminNotifications.prompt('Delete logs older than how many days?', '30');
        if (!days || isNaN(days) || days < 1) return;
        
        const confirmed = await AdminNotifications.confirm(`Are you sure you want to delete logs older than ${days} days?`);
        if (!confirmed) return;
        
        const resultsElement = document.getElementById('admin-test-results');
        if (!resultsElement) return;
        
        resultsElement.textContent = 'Cleaning up old logs...\n';
        
        try {
            const response = await AdminAPI.logs.cleanup(days);

            if (response.ok) {
                const result = await response.json();
                resultsElement.textContent += `✅ Cleanup completed!\n`;
                resultsElement.textContent += `Deleted ${result.deleted_count} log entries\n`;
                resultsElement.textContent += `Cutoff date: ${new Date(result.cutoff_date).toLocaleString()}\n`;
            } else {
                resultsElement.textContent += `❌ Failed to cleanup logs\n`;
            }
        } catch (error) {
            resultsElement.textContent += `❌ Error during cleanup: ${error.message}\n`;
            AdminNotifications.handleApiError(error, 'Error during cleanup');
        }
    },

    // Save timezone settings
    async handleTimezoneSettingsSubmit(event) {
        event.preventDefault();
        const newTimezone = document.getElementById('available-timezones').value;
        if (!newTimezone) {
            AdminNotifications.showError('Please select a timezone.');
            return;
        }

        try {
            const response = await AdminAPI.timezone.updateSettings({ timezone: newTimezone });

            if (response.ok) {
                AdminNotifications.showSuccess('Timezone settings updated successfully.');
                await this.loadTimezoneSettings();
            } else {
                AdminNotifications.showError('Failed to update timezone settings.');
            }
        } catch (error) {
            AdminNotifications.handleApiError(error, 'Error updating timezone settings.');
        }
    },

    // Initialize backup system module
    init() {
        // Setup form event listeners
        const backupForm = document.getElementById('backup-settings-form');
        if (backupForm) {
            backupForm.addEventListener('submit', this.handleBackupSettingsSubmit.bind(this));
        }

        const timezoneForm = document.getElementById('timezone-settings-form');
        if (timezoneForm) {
            timezoneForm.addEventListener('submit', this.handleTimezoneSettingsSubmit.bind(this));
        }

        // Setup button event listeners
        this.setupButtonEventListeners();

        console.log('Backup system module initialized');
    },

    // Setup button event listeners
    setupButtonEventListeners() {
        // Test backup connection button
        const testConnectionBtn = document.getElementById('test-backup-connection-btn');
        if (testConnectionBtn) {
            testConnectionBtn.addEventListener('click', this.testBackupConnection.bind(this));
        }

        // Backup now button
        const backupNowBtn = document.getElementById('backup-now-btn');
        if (backupNowBtn) {
            backupNowBtn.addEventListener('click', this.backupNow.bind(this));
        }

        // Refresh backup settings button
        const refreshBackupBtn = document.getElementById('refresh-backup-settings-btn');
        if (refreshBackupBtn) {
            refreshBackupBtn.addEventListener('click', this.loadBackupSettings.bind(this));
        }

        // Refresh backup list button
        const refreshBackupListBtn = document.getElementById('refresh-backup-list-btn');
        if (refreshBackupListBtn) {
            refreshBackupListBtn.addEventListener('click', this.loadBackupList.bind(this));
        }

        // Test admin API button
        const testAdminApiBtn = document.getElementById('test-admin-api-btn');
        if (testAdminApiBtn) {
            testAdminApiBtn.addEventListener('click', this.testAdminAPI.bind(this));
        }

        // Load log stats button
        const loadLogStatsBtn = document.getElementById('load-log-stats-btn');
        if (loadLogStatsBtn) {
            loadLogStatsBtn.addEventListener('click', this.loadLogStats.bind(this));
        }

        // Cleanup old logs button
        const cleanupLogsBtn = document.getElementById('cleanup-old-logs-btn');
        if (cleanupLogsBtn) {
            cleanupLogsBtn.addEventListener('click', this.cleanupOldLogs.bind(this));
        }

        // Refresh timezone settings button
        const refreshTimezoneBtn = document.getElementById('refresh-timezone-settings-btn');
        if (refreshTimezoneBtn) {
            refreshTimezoneBtn.addEventListener('click', this.loadTimezoneSettings.bind(this));
        }

        console.log('Button event listeners set up for backup system');
    },

    // Ensure initialization - called when tab is activated
    ensureInitialized() {
        // Re-setup button event listeners in case DOM wasn't ready during initial load
        this.setupButtonEventListeners();
        console.log('Backup system module ensured initialized');
    }
};

// Export for global access
window.AdminBackup = AdminBackup;

// Initialize when module loads
AdminBackup.init();

console.log('Admin backup system module loaded!');
