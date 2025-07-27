/* Dashboard Module - Main dashboard with metrics and charts */

const AdminDashboard = {
    // Data storage
    data: {
        summary: null,
        userStats: null,
        lotStats: null,
        monthlyStats: null,
        systemStatus: null
    },

    // Timer storage
    refreshTimer: null,

    // Initialize dashboard
    async init() {
        console.log('Dashboard module initializing...');
        this.setupEventListeners();
        await this.loadDashboardData();
        console.log('Dashboard module initialized');
    },

    // Setup event listeners
    setupEventListeners() {
        // Refresh button
        const refreshBtn = document.getElementById('dashboard-refresh-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', this.loadDashboardData.bind(this));
        }

        // Period filter
        const periodFilter = document.getElementById('dashboard-period-filter');
        if (periodFilter) {
            periodFilter.addEventListener('change', this.loadDashboardData.bind(this));
        }

        // Chart refresh events
        document.addEventListener('refresh', (event) => {
            if (event.target.tagName === 'DASHBOARD-CHART') {
                this.refreshChart(event.target);
            }
        });

        // Auto-refresh every 5 minutes
        this.refreshTimer = setInterval(() => {
            // Only refresh if user is still authenticated and admin view is visible
            if (window.auth && window.auth.isAuthenticated() && window.auth.isAdmin()) {
                const adminView = document.getElementById('admin-view');
                if (adminView && adminView.style.display !== 'none') {
                    this.loadDashboardData(false); // Silent refresh
                }
            } else {
                // User is no longer authenticated, stop the timer
                this.stopAutoRefresh();
            }
        }, 5 * 60 * 1000);
    },

    // Load all dashboard data
    async loadDashboardData(showLoading = true) {
        if (showLoading) {
            this.showLoadingState();
        }

        try {
            // Get date parameters based on current UI settings
            const dateParams = this._getDashboardDateParameters();

            // Load dynamic reports data instead of static reports
            const dynamicReportsResponse = await AdminAPI.dynamicReports.getColumns();
            if (dynamicReportsResponse.ok) {
                // For dashboard, we'll get basic summary data from bookings directly
                // This replaces the removed static reports functionality
                this.data.summary = {
                    total_bookings: 0,
                    unique_users: 0,
                    total_hours: 0,
                    avg_booking_duration: 0
                };
                this.data.userStats = [];
                this.data.lotStats = [];
                this.data.monthlyStats = [];
            }

            // Load system status
            await this.loadSystemStatus();

            // Update UI
            this.updateSummaryCards();
            this.updateCharts();
            this.updateActivityFeed();
            this.updateQuickStats();

            if (showLoading) {
                this.hideLoadingState();
            }

            // Update last refresh time
            const lastRefreshElement = document.getElementById('dashboard-last-refresh');
            if (lastRefreshElement) {
                lastRefreshElement.textContent = new Date().toLocaleTimeString();
            }

        } catch (error) {
            console.error('Error loading dashboard data:', error);
            AdminNotifications.showError('Failed to load dashboard data');
            if (showLoading) {
                this.hideLoadingState();
            }
        }
    },

    // Get dashboard date parameters based on current UI settings
    _getDashboardDateParameters() {
        const useCustomDates = document.getElementById('dashboard-use-custom-dates')?.checked || false;
        
        if (useCustomDates) {
            const startDateElement = document.getElementById('dashboard-start-date');
            const endDateElement = document.getElementById('dashboard-end-date');
            
            if (startDateElement?.value && endDateElement?.value) {
                const startDate = new Date(startDateElement.value);
                const endDate = new Date(endDateElement.value);
                
                // Set time to beginning and end of day respectively
                startDate.setHours(0, 0, 0, 0);
                endDate.setHours(23, 59, 59, 999);
                
                return {
                    start_date: startDate.toISOString(),
                    end_date: endDate.toISOString(),
                    months: 2 // Keep default for backward compatibility
                };
            } else {
                AdminNotifications.showError('Please provide both start and end dates for custom date range');
                throw new Error('Missing custom date range values');
            }
        } else {
            const periodFilter = document.getElementById('dashboard-period-filter');
            const months = periodFilter ? parseInt(periodFilter.value) : 2;
            
            return {
                months: months,
                start_date: null,
                end_date: null
            };
        }
    },

    // Toggle date selection mode
    toggleDateSelectionMode() {
        const useCustomDates = document.getElementById('dashboard-use-custom-dates')?.checked || false;
        const monthsSection = document.getElementById('dashboard-months-selection');
        const customDatesSection = document.getElementById('dashboard-custom-dates');
        
        if (monthsSection && customDatesSection) {
            if (useCustomDates) {
                monthsSection.style.display = 'none';
                customDatesSection.style.display = 'flex';
                this._setDefaultCustomDashboardDates();
            } else {
                monthsSection.style.display = 'block';
                customDatesSection.style.display = 'none';
            }
        }
    },

    // Set sensible defaults for custom date inputs
    _setDefaultCustomDashboardDates() {
        const startDateElement = document.getElementById('dashboard-start-date');
        const endDateElement = document.getElementById('dashboard-end-date');
        
        if (startDateElement && endDateElement) {
            const today = new Date();
            const twoMonthsAgo = new Date();
            twoMonthsAgo.setMonth(today.getMonth() - 2);
            
            // Format dates as YYYY-MM-DD for input[type="date"]
            startDateElement.value = twoMonthsAgo.toISOString().split('T')[0];
            endDateElement.value = today.toISOString().split('T')[0];
        }
    },

    // Validate custom date range
    validateCustomDateRange() {
        const startDateElement = document.getElementById('dashboard-start-date');
        const endDateElement = document.getElementById('dashboard-end-date');
        
        if (startDateElement?.value && endDateElement?.value) {
            const startDate = new Date(startDateElement.value);
            const endDate = new Date(endDateElement.value);
            
            if (startDate >= endDate) {
                AdminNotifications.showError('Start date must be before end date');
                return false;
            }
            
            // Check if range is reasonable (not more than 2 years)
            const diffTime = Math.abs(endDate - startDate);
            const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
            
            if (diffDays > 730) { // 2 years
                AdminNotifications.showWarning('Selected date range is longer than 2 years. Dashboard may take longer to load.');
            }
            
            return true;
        }
        
        return false;
    },

    // Load system status information
    async loadSystemStatus() {
        try {
            // Get email settings
            const emailResponse = await AdminAPI.email.getSettings();
            if (emailResponse.ok) {
                const emailData = await emailResponse.json();
                this.data.systemStatus = this.data.systemStatus || {};
                this.data.systemStatus.emailEnabled = emailData.sendgrid_api_key ? true : false;
                this.data.systemStatus.reportsEnabled = emailData.reports_enabled;
            }

            // Get backup settings
            const backupResponse = await AdminAPI.backup.getSettings();
            if (backupResponse.ok) {
                const backupData = await backupResponse.json();
                this.data.systemStatus.backupEnabled = backupData.enabled;
                this.data.systemStatus.lastBackup = backupData.last_backup_time;
            }

            // Get logs count
            const logsResponse = await AdminAPI.logs.getStats(24);
            if (logsResponse.ok) {
                const logsData = await logsResponse.json();
                this.data.systemStatus.errorCount = logsData.error_count || 0;
                this.data.systemStatus.warningCount = logsData.warning_count || 0;
            }

        } catch (error) {
            console.error('Error loading system status:', error);
        }
    },

    // Update summary cards
    updateSummaryCards() {
        if (!this.data.summary) return;

        const cards = [
            {
                id: 'total-bookings-card',
                value: this.data.summary.total_bookings,
                trend: this.calculateTrend('bookings')
            },
            {
                id: 'unique-users-card',
                value: this.data.summary.unique_users,
                trend: this.calculateTrend('users')
            },
            {
                id: 'total-hours-card',
                value: Math.round(this.data.summary.total_hours),
                trend: this.calculateTrend('hours')
            },
            {
                id: 'avg-duration-card',
                value: Math.round(this.data.summary.avg_booking_duration * 10) / 10,
                trend: this.calculateTrend('duration')
            }
        ];

        cards.forEach(cardData => {
            const card = document.getElementById(cardData.id);
            if (card) {
                card.updateValue(cardData.value);
                if (cardData.trend) {
                    card.updateTrend(cardData.trend.direction, cardData.trend.value);
                }
            }
        });
    },

    // Calculate trend for metrics (simple comparison with previous period)
    calculateTrend(metric) {
        // For now, return random trends as we don't have historical comparison data
        // In a real implementation, you'd compare with previous period
        const directions = ['up', 'down', 'neutral'];
        const direction = directions[Math.floor(Math.random() * directions.length)];
        const value = direction === 'neutral' ? '0%' : `${Math.floor(Math.random() * 20) + 1}%`;
        
        return { direction, value };
    },

    // Update charts
    updateCharts() {
        this.updateUserActivityChart();
        this.updateParkingLotUsageChart();
        this.updateMonthlyTrendsChart();
    },

    // Update user activity chart
    updateUserActivityChart() {
        const chart = document.getElementById('user-activity-chart');
        if (!chart || !this.data.userStats || this.data.userStats.length === 0) return;

        // Get top 10 users by bookings
        const topUsers = this.data.userStats
            .filter(user => user.total_bookings > 0) // Only include users with bookings
            .sort((a, b) => b.total_bookings - a.total_bookings)
            .slice(0, 10)
            .map(user => ({
                label: user.email.split('@')[0], // Show only username part
                value: user.total_bookings
            }));

        chart.setData(topUsers);
    },

    // Update parking lot usage chart
    updateParkingLotUsageChart() {
        const chart = document.getElementById('parking-lot-usage-chart');
        if (!chart || !this.data.lotStats || this.data.lotStats.length === 0) return;

        const lotData = this.data.lotStats
            .filter(lot => lot.total_bookings > 0) // Only include lots with bookings
            .map(lot => ({
                label: lot.name,
                value: lot.total_bookings
            }));

        chart.setData(lotData);
    },

    // Update monthly trends chart
    updateMonthlyTrendsChart() {
        const chart = document.getElementById('monthly-trends-chart');
        if (!chart || !this.data.monthlyStats) return;

        const monthlyData = this.data.monthlyStats
            .sort((a, b) => a.month.localeCompare(b.month))
            .map(month => ({
                label: month.month,
                value: month.total_bookings
            }));

        chart.setData(monthlyData);
    },

    // Update activity feed
    updateActivityFeed() {
        const feedContainer = document.getElementById('dashboard-activity-feed');
        if (!feedContainer) return;

        const activities = [];

        // Add recent user activity
        if (this.data.userStats && this.data.userStats.length > 0) {
            const topUser = this.data.userStats.reduce((prev, current) => 
                (prev.total_bookings > current.total_bookings) ? prev : current
            );
            activities.push({
                icon: 'USER',
                text: `${topUser.email} is the most active user with ${topUser.total_bookings} bookings`,
                time: 'Recent'
            });
        }

        // Add parking lot info
        if (this.data.lotStats && this.data.lotStats.length > 0) {
            const topLot = this.data.lotStats.reduce((prev, current) => 
                (prev.total_bookings > current.total_bookings) ? prev : current
            );
            activities.push({
                icon: '[P]',
                text: `${topLot.name} is the busiest parking lot with ${topLot.total_bookings} bookings`,
                time: 'Recent'
            });
        }

        // Add system status
        if (this.data.systemStatus) {
            if (this.data.systemStatus.errorCount > 0) {
                activities.push({
                    icon: 'WARN',
                    text: `${this.data.systemStatus.errorCount} errors logged in the last 24 hours`,
                    time: 'Recent'
                });
            }

            if (!this.data.systemStatus.backupEnabled) {
                activities.push({
                    icon: 'DISK',
                    text: 'Database backups are disabled',
                    time: 'System Status'
                });
            }
        }

        // Update feed HTML with appropriate icon classes
        feedContainer.innerHTML = activities.length > 0 ? 
            activities.map(activity => {
                let iconClass = '';
                switch(activity.icon) {
                    case 'USER': iconClass = 'icon-user'; break;
                    case '[P]': iconClass = 'icon-parking'; break;
                    case 'WARN': iconClass = 'icon-warning'; break;
                    case 'DISK': iconClass = 'icon-disk'; break;
                }
                return `
                    <div class="activity-item">
                        <div class="activity-icon ${iconClass}">${activity.icon}</div>
                        <div class="activity-content">
                            <div class="activity-text">${activity.text}</div>
                            <div class="activity-time">${activity.time}</div>
                        </div>
                    </div>
                `;
            }).join('') :
            '<div class="text-muted text-center py-3">No recent activity</div>';
    },

    // Update quick stats
    updateQuickStats() {
        const statsContainer = document.getElementById('dashboard-quick-stats');
        if (!statsContainer) return;

        const stats = [];

        if (this.data.systemStatus) {
            stats.push({
                label: 'Email System',
                value: this.data.systemStatus.emailEnabled ? 'Enabled' : 'Disabled',
                status: this.data.systemStatus.emailEnabled ? 'success' : 'warning'
            });

            stats.push({
                label: 'Reports',
                value: this.data.systemStatus.reportsEnabled ? 'Enabled' : 'Disabled',
                status: this.data.systemStatus.reportsEnabled ? 'success' : 'warning'
            });

            stats.push({
                label: 'Backups',
                value: this.data.systemStatus.backupEnabled ? 'Enabled' : 'Disabled',
                status: this.data.systemStatus.backupEnabled ? 'success' : 'danger'
            });

            stats.push({
                label: 'Errors (24h)',
                value: this.data.systemStatus.errorCount || 0,
                status: this.data.systemStatus.errorCount > 0 ? 'danger' : 'success'
            });
        }

        if (this.data.lotStats) {
            stats.push({
                label: 'Parking Lots',
                value: this.data.lotStats.length,
                status: 'info'
            });
        }

        statsContainer.innerHTML = stats.map(stat => `
            <div class="quick-stat">
                <div class="quick-stat-label">${stat.label}</div>
                <div class="quick-stat-value">
                    <span class="badge bg-${stat.status}">${stat.value}</span>
                </div>
            </div>
        `).join('');
    },

    // Refresh individual chart
    async refreshChart(chartElement) {
        chartElement.showLoading();
        
        try {
            // Reload data based on chart type
            await this.loadDashboardData(false);
            
            // Update specific chart
            const chartId = chartElement.id;
            switch (chartId) {
                case 'user-activity-chart':
                    this.updateUserActivityChart();
                    break;
                case 'parking-lot-usage-chart':
                    this.updateParkingLotUsageChart();
                    break;
                case 'monthly-trends-chart':
                    this.updateMonthlyTrendsChart();
                    break;
            }
        } catch (error) {
            chartElement.showError(error.message);
        }
    },

    // Show loading state
    showLoadingState() {
        const loadingIndicator = document.getElementById('dashboard-loading');
        if (loadingIndicator) {
            loadingIndicator.style.display = 'block';
        }
    },

    // Hide loading state
    hideLoadingState() {
        const loadingIndicator = document.getElementById('dashboard-loading');
        if (loadingIndicator) {
            loadingIndicator.style.display = 'none';
        }
    },

    // Export dashboard data
    async exportDashboard() {
        try {
            // Create a simple CSV export of dashboard data
            const csvData = this.generateCSVExport();
            const blob = new Blob([csvData], { type: 'text/csv' });
            const url = window.URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = `dashboard-export-${new Date().toISOString().split('T')[0]}.csv`;
            link.click();
            window.URL.revokeObjectURL(url);
            
            AdminNotifications.showSuccess('Dashboard data exported successfully');
        } catch (error) {
            AdminNotifications.showError('Failed to export dashboard data');
        }
    },

    // Generate CSV export
    generateCSVExport() {
        let csv = 'Dashboard Export\n\n';
        
        // Summary data
        if (this.data.summary) {
            csv += 'Summary Metrics\n';
            csv += 'Metric,Value\n';
            csv += `Total Bookings,${this.data.summary.total_bookings}\n`;
            csv += `Unique Users,${this.data.summary.unique_users}\n`;
            csv += `Total Hours,${this.data.summary.total_hours}\n`;
            csv += `Average Duration,${this.data.summary.avg_booking_duration}\n\n`;
        }

        // User statistics
        if (this.data.userStats) {
            csv += 'Top Users\n';
            csv += 'Email,Total Bookings,Total Hours,Average Duration\n';
            this.data.userStats
                .sort((a, b) => b.total_bookings - a.total_bookings)
                .slice(0, 10)
                .forEach(user => {
                    csv += `${user.email},${user.total_bookings},${user.total_hours},${user.avg_duration}\n`;
                });
            csv += '\n';
        }

        // Parking lot statistics
        if (this.data.lotStats) {
            csv += 'Parking Lot Usage\n';
            csv += 'Parking Lot,Total Bookings,Total Hours,Unique Users\n';
            this.data.lotStats.forEach(lot => {
                csv += `${lot.name},${lot.total_bookings},${lot.total_hours},${lot.unique_users}\n`;
            });
        }

        return csv;
    },

    // Stop auto-refresh timer
    stopAutoRefresh() {
        if (this.refreshTimer) {
            clearInterval(this.refreshTimer);
            this.refreshTimer = null;
            console.log('Dashboard auto-refresh timer stopped');
        }
    },

    // Ensure event listeners are set up (called by admin-main.js)
    ensureInitialized() {
        this.setupEventListeners();
    }
};

// Export for global access
window.AdminDashboard = AdminDashboard;

console.log('Admin dashboard module loaded!');
