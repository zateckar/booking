/* Reports Module - Standard booking reports functionality */

const AdminReports = {
    // Load reports data
    async loadReportsData() {
        const monthsInput = document.getElementById('reports-months-filter');
        const months = monthsInput ? (monthsInput.value !== '' ? parseInt(monthsInput.value) : 2) : 2;
        
        try {
            const response = await AdminAPI.reports.getBookingReports(months);
            
            if (response.ok) {
                const data = await response.json();
                this.displayReportsData(data);
            } else {
                AdminNotifications.showError('Failed to load reports data');
            }
        } catch (error) {
            AdminNotifications.handleApiError(error, 'Error loading reports data');
        }
    },

    // Display reports data
    displayReportsData(data) {
        // Update summary cards
        const summaryCards = document.getElementById('reports-summary-cards');
        if (summaryCards) {
            summaryCards.innerHTML = `
                <div class="col-md-3">
                    <div class="card bg-primary text-white">
                        <div class="card-body">
                            <h5 class="card-title">Total Bookings</h5>
                            <h3>${data.summary.total_bookings}</h3>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card bg-success text-white">
                        <div class="card-body">
                            <h5 class="card-title">Unique Users</h5>
                            <h3>${data.summary.unique_users}</h3>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card bg-info text-white">
                        <div class="card-body">
                            <h5 class="card-title">Total Hours</h5>
                            <h3>${Math.round(data.summary.total_hours)}</h3>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card bg-warning text-white">
                        <div class="card-body">
                            <h5 class="card-title">Avg Duration</h5>
                            <h3>${Math.round(data.summary.avg_booking_duration)} hrs</h3>
                        </div>
                    </div>
                </div>
            `;
        }

        // Display user statistics table
        const userStatsTable = document.getElementById('user-stats-table-body');
        if (userStatsTable) {
            userStatsTable.innerHTML = '';
            const sortedUsers = data.user_statistics.sort((a, b) => b.total_bookings - a.total_bookings);
            
            sortedUsers.forEach(user => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${user.email}</td>
                    <td>${user.total_bookings}</td>
                    <td>${Math.round(user.total_hours)}</td>
                    <td>${Math.round(user.avg_duration * 10) / 10}</td>
                    <td>${user.parking_lots_used}</td>
                    <td>${user.license_plates}</td>
                `;
                userStatsTable.appendChild(row);
            });
        }

        // Display parking lot statistics table
        const lotStatsTable = document.getElementById('lot-stats-table-body');
        if (lotStatsTable) {
            lotStatsTable.innerHTML = '';
            
            data.parking_lot_statistics.forEach(lot => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${lot.name}</td>
                    <td>${lot.total_bookings}</td>
                    <td>${Math.round(lot.total_hours)}</td>
                    <td>${Math.round((lot.avg_duration || 0) * 10) / 10}</td>
                    <td>${lot.unique_users}</td>
                `;
                lotStatsTable.appendChild(row);
            });
        }

        // Display monthly statistics table
        const monthlyStatsTable = document.getElementById('monthly-stats-table-body');
        if (monthlyStatsTable) {
            monthlyStatsTable.innerHTML = '';
            
            data.monthly_statistics.sort((a, b) => b.month.localeCompare(a.month)).forEach(month => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${month.month}</td>
                    <td>${month.total_bookings}</td>
                    <td>${Math.round(month.total_hours)}</td>
                    <td>${Math.round(month.avg_duration * 10) / 10}</td>
                    <td>${month.unique_users}</td>
                `;
                monthlyStatsTable.appendChild(row);
            });
        }

        // Update period display
        const periodDisplay = document.getElementById('reports-period-display');
        if (periodDisplay) {
            const startDate = new Date(data.period.start_date).toLocaleDateString();
            const endDate = new Date(data.period.end_date).toLocaleDateString();
            periodDisplay.textContent = `Period: ${startDate} to ${endDate}`;
        }
    },

    // Download Excel report
    async downloadExcelReport() {
        const monthsInput = document.getElementById('reports-months-filter');
        const months = monthsInput ? (monthsInput.value !== '' ? parseInt(monthsInput.value) : 2) : 2;
        
        try {
            const response = await AdminAPI.reports.downloadExcel(months);
            
            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.style.display = 'none';
                a.href = url;
                a.download = `booking_report_${new Date().toISOString().split('T')[0]}.xlsx`;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
                
                AdminNotifications.showSuccess('Excel report downloaded successfully');
            } else {
                const errorData = await response.json();
                AdminNotifications.showError(errorData.detail || 'Failed to download Excel report');
            }
        } catch (error) {
            AdminNotifications.handleApiError(error, 'Error downloading Excel report');
        }
    },

    // Send email report
    async sendEmailReport() {
        const modal = new bootstrap.Modal(document.getElementById('send-email-report-modal'));
        modal.show();
    },

    // Handle send email report
    async handleSendEmailReport() {
        const recipients = document.getElementById('email-report-recipients').value
            .split(',')
            .map(email => email.trim())
            .filter(email => email.length > 0);
        
        if (recipients.length === 0) {
            AdminNotifications.showError('Please enter at least one recipient email');
            return;
        }

        const monthsInput = document.getElementById('reports-months-filter');
        const months = monthsInput ? (monthsInput.value !== '' ? parseInt(monthsInput.value) : 2) : 2;
        const includeExcel = document.getElementById('email-include-excel').checked;
        
        try {
            const response = await AdminAPI.reports.sendEmail({
                recipients: recipients,
                months: months,
                include_excel: includeExcel
            });
            
            if (response.ok) {
                const result = await response.json();
                AdminNotifications.showSuccess(result.message);
                bootstrap.Modal.getInstance(document.getElementById('send-email-report-modal')).hide();
            } else {
                const errorData = await response.json();
                AdminNotifications.showError(errorData.detail || 'Failed to send email report');
            }
        } catch (error) {
            AdminNotifications.handleApiError(error, 'Error sending email report');
        }
    },

    // Load report schedule settings
    async loadReportScheduleSettings() {
        try {
            const response = await AdminAPI.reports.getScheduleSettings();
            
            if (response.ok) {
                const settings = await response.json();
                
                // Check if global reports are enabled first
                const globalReportsEnabled = settings.reports_enabled;
                const scheduleCheckbox = document.getElementById('schedule-reports-enabled');
                const scheduleRecipientsField = document.getElementById('schedule-recipients');
                const scheduleHourField = document.getElementById('schedule-hour');
                const scheduleFrequencyField = document.getElementById('schedule-frequency');
                
                // Disable scheduling controls if global reports are disabled
                const fieldsToToggle = [scheduleCheckbox, scheduleRecipientsField, scheduleHourField, scheduleFrequencyField];
                fieldsToToggle.forEach(field => {
                    if (field) {
                        field.disabled = !globalReportsEnabled;
                    }
                });
                
                if (globalReportsEnabled) {
                    scheduleCheckbox.checked = true; // If global reports enabled, scheduling can be enabled
                    scheduleRecipientsField.value = settings.report_recipients.join(', ');
                } else {
                    scheduleCheckbox.checked = false;
                    scheduleRecipientsField.value = '';
                }
                
                scheduleHourField.value = settings.report_schedule_hour;
                scheduleFrequencyField.value = settings.report_frequency;
                
                // Update schedule status badge
                const statusBadge = document.getElementById('schedule-status');
                if (statusBadge) {
                    if (globalReportsEnabled) {
                        statusBadge.textContent = 'Enabled';
                        statusBadge.className = 'badge bg-success';
                    } else {
                        statusBadge.textContent = 'Disabled (Global reports disabled)';
                        statusBadge.className = 'badge bg-danger';
                    }
                }
                
                const lastSentElement = document.getElementById('schedule-last-sent');
                if (lastSentElement) {
                    if (settings.last_report_sent) {
                        const lastSent = new Date(settings.last_report_sent).toLocaleString();
                        lastSentElement.textContent = `Last sent: ${lastSent}`;
                    } else {
                        lastSentElement.textContent = 'Never sent';
                    }
                }
                
                // Update the info alert to show current global status
                const infoAlert = document.querySelector('#schedule-settings .alert-info');
                if (infoAlert) {
                    if (globalReportsEnabled) {
                        infoAlert.className = 'alert alert-success';
                        infoAlert.innerHTML = '<strong>✓ Global reports are enabled.</strong> You can configure scheduling below.';
                    } else {
                        infoAlert.className = 'alert alert-warning';
                        infoAlert.innerHTML = '<strong>⚠ Global reports are disabled.</strong> Please enable reports in the <strong>Email Settings</strong> tab first.';
                    }
                }
                
            } else {
                AdminNotifications.showError('Failed to load schedule settings');
            }
        } catch (error) {
            AdminNotifications.handleApiError(error, 'Error loading schedule settings');
        }
    },

    // Save report schedule settings
    async saveReportScheduleSettings() {
        const recipients = document.getElementById('schedule-recipients').value
            .split(',')
            .map(email => email.trim())
            .filter(email => email.length > 0);
        
        const settings = {
            reports_enabled: document.getElementById('schedule-reports-enabled').checked,
            report_recipients: recipients,
            report_schedule_hour: parseInt(document.getElementById('schedule-hour').value),
            report_frequency: document.getElementById('schedule-frequency').value
        };
        
        try {
            const response = await AdminAPI.reports.updateScheduleSettings(settings);
            
            if (response.ok) {
                AdminNotifications.showSuccess('Schedule settings saved successfully');
                this.loadReportScheduleSettings(); // Reload to show updated last sent time
            } else {
                AdminNotifications.showError('Failed to save schedule settings');
            }
        } catch (error) {
            AdminNotifications.handleApiError(error, 'Error saving schedule settings');
        }
    },

    // Initialize reports module
    init() {
        // Setup filter event listener
        const reportsMonthsFilter = document.getElementById('reports-months-filter');
        if (reportsMonthsFilter) {
            reportsMonthsFilter.addEventListener('change', this.loadReportsData.bind(this));
        }

        // Wire up button event listeners
        this.setupButtonEventListeners();

        console.log('Reports module initialized');
    },

    // Setup button event listeners
    setupButtonEventListeners() {
        // Download Excel Report button
        const downloadExcelBtn = document.getElementById('download-excel-report-btn');
        if (downloadExcelBtn) {
            downloadExcelBtn.addEventListener('click', this.downloadExcelReport.bind(this));
        }

        // Send Email Report button
        const sendEmailBtn = document.getElementById('send-email-report-btn');
        if (sendEmailBtn) {
            sendEmailBtn.addEventListener('click', this.sendEmailReport.bind(this));
        }

        // Refresh Reports Data button
        const refreshBtn = document.getElementById('refresh-reports-data-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', this.loadReportsData.bind(this));
        }

        // Save Report Schedule Settings button
        const saveScheduleBtn = document.getElementById('save-report-schedule-settings-btn');
        if (saveScheduleBtn) {
            saveScheduleBtn.addEventListener('click', this.saveReportScheduleSettings.bind(this));
        }
    },

    // Ensure event listeners are set up (called by admin-main.js)
    ensureInitialized() {
        this.setupButtonEventListeners();
    }
};

// Export for global access
window.AdminReports = AdminReports;

// Initialize when module loads
AdminReports.init();

console.log('Admin reports module loaded!');
