/* API Client - Centralized API handling for admin modules */

const AdminAPI = {
    // Base API request method
    async makeRequest(url, options = {}) {
        AdminLogs.log('DEBUG', `🌐 [AdminAPI] Making request to: ${url}`);
        AdminLogs.log('DEBUG', `🌐 [AdminAPI] Request options:`, options);

        try {
            const token = localStorage.getItem('access_token');
            const headers = { ...options.headers };

            if (token) {
                headers['Authorization'] = `Bearer ${token}`;
            }

            // Properly handle body and Content-Type
            let body = options.body;
            if (body && typeof body === 'object' && !(body instanceof FormData)) {
                body = JSON.stringify(body);
                if (!headers['Content-Type']) {
                    headers['Content-Type'] = 'application/json';
                }
            }

            const response = await fetch(url, {
                ...options,
                headers,
                body,
                credentials: 'include'
            });

            if (response.status === 401 && window.auth && !window.auth.isRefreshing()) {
                AdminLogs.log('INFO', `API request to ${url} returned 401, attempting token refresh...`);
                await window.auth.refreshAccessToken();
                const newToken = localStorage.getItem('access_token');
                if (newToken && newToken !== token) {
                    AdminLogs.log('INFO', `Retrying API request to ${url} with refreshed token...`);
                    headers['Authorization'] = `Bearer ${newToken}`;
                    return fetch(url, { ...options, headers, body, credentials: 'include' });
                }
            }
            
            AdminLogs.log('DEBUG', `🌐 [AdminAPI] Response received:`, {
                ok: response.ok,
                status: response.status,
                statusText: response.statusText,
                url: response.url
            });

            return response;
        } catch (error) {
            AdminLogs.log('ERROR', '🌐 [AdminAPI] API request failed:', error);
            AdminLogs.log('ERROR', '🌐 [AdminAPI] Error stack:', error.stack);
            throw error;
        }
    },

    // User management API
    users: {
        async getAll() {
            return await AdminAPI.makeRequest('/api/admin/users');
        },

        async create(userData) {
            return await AdminAPI.makeRequest('/api/admin/users', {
                method: 'POST',
                body: userData
            });
        },

        async setAdmin(userId, isAdmin) {
            return await AdminAPI.makeRequest(`/api/admin/users/${userId}/set-admin?is_admin=${isAdmin}`, {
                method: 'PUT'
            });
        },

        async setPassword(userId, password) {
            return await AdminAPI.makeRequest(`/api/admin/users/${userId}/set-password`, {
                method: 'PUT',
                body: { password }
            });
        },

        async delete(userId) {
            return await AdminAPI.makeRequest(`/api/admin/users/${userId}`, {
                method: 'DELETE'
            });
        }
    },

    // Unified OIDC & Claims API
    oidcClaims: {
        // OIDC Providers
        async getProviders() {
            return await AdminAPI.makeRequest('/api/admin/oidc-claims/providers');
        },

        async getProvider(providerId) {
            return await AdminAPI.makeRequest(`/api/admin/oidc-claims/providers/${providerId}`);
        },

        async createProvider(providerData) {
            return await AdminAPI.makeRequest('/api/admin/oidc-claims/providers', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(providerData)
            });
        },

        async updateProvider(providerId, providerData) {
            return await AdminAPI.makeRequest(`/api/admin/oidc-claims/providers/${providerId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(providerData)
            });
        },

        async deleteProvider(providerId) {
            return await AdminAPI.makeRequest(`/api/admin/oidc-claims/providers/${providerId}`, {
                method: 'DELETE'
            });
        },

        // Claims Mappings
        async getMappings() {
            return await AdminAPI.makeRequest('/api/admin/oidc-claims/claims-mappings');
        },

        async getMapping(mappingId) {
            return await AdminAPI.makeRequest(`/api/admin/oidc-claims/claims-mappings/${mappingId}`);
        },

        async createMapping(mappingData) {
            return await AdminAPI.makeRequest('/api/admin/oidc-claims/claims-mappings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(mappingData)
            });
        },

        async updateMapping(mappingId, mappingData) {
            return await AdminAPI.makeRequest(`/api/admin/oidc-claims/claims-mappings/${mappingId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(mappingData)
            });
        },

        async deleteMapping(mappingId) {
            return await AdminAPI.makeRequest(`/api/admin/oidc-claims/claims-mappings/${mappingId}`, {
                method: 'DELETE'
            });
        },

        async discoverClaims(data) {
            return await AdminAPI.makeRequest('/api/admin/oidc-claims/claims-discovery', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
        },

        async getUserProfiles() {
            return await AdminAPI.makeRequest('/api/admin/oidc-claims/user-profiles');
        },

        async getUserProfile(profileId) {
            return await AdminAPI.makeRequest(`/api/admin/oidc-claims/user-profiles/${profileId}`);
        }
    },

    // Legacy OIDC API (backwards compatibility)
    oidc: {
        async getAll() {
            return await AdminAPI.oidcClaims.getProviders();
        },

        async get(providerId) {
            return await AdminAPI.oidcClaims.getProvider(providerId);
        },

        async create(providerData) {
            return await AdminAPI.oidcClaims.createProvider(providerData);
        },

        async update(providerId, providerData) {
            return await AdminAPI.oidcClaims.updateProvider(providerId, providerData);
        },

        async delete(providerId) {
            return await AdminAPI.oidcClaims.deleteProvider(providerId);
        }
    },

    // Parking lots API
    parkingLots: {
        async getAll() {
            return await AdminAPI.makeRequest('/api/admin/parking-lots/');
        },

        async create(formData) {
            return await AdminAPI.makeRequest('/api/admin/parking-lots/', {
                method: 'POST',
                body: formData
            });
        },

        async delete(lotId) {
            return await AdminAPI.makeRequest(`/api/admin/parking-lots/${lotId}`, {
                method: 'DELETE'
            });
        },

        async get(lotId) {
            return await AdminAPI.makeRequest(`/api/parking-lots/${lotId}`);
        },

        async getSpaces(lotId) {
            return await AdminAPI.makeRequest(`/api/admin/parking-lots/${lotId}/spaces/`);
        },

        async createSpace(lotId, spaceData) {
            return await AdminAPI.makeRequest(`/api/admin/parking-lots/${lotId}/spaces/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(spaceData)
            });
        },

        async updateSpace(lotId, spaceId, spaceData) {
            return await AdminAPI.makeRequest(`/api/admin/parking-lots/${lotId}/spaces/${spaceId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(spaceData)
            });
        },

        async deleteSpace(lotId, spaceId) {
            return await AdminAPI.makeRequest(`/api/admin/parking-lots/${lotId}/spaces/${spaceId}`, {
                method: 'DELETE'
            });
        },

        async getAvailability(lotId, startTime, endTime) {
            return await AdminAPI.makeRequest(
                `/api/parking-lots/${lotId}/spaces/availability?start_time=${encodeURIComponent(startTime)}&end_time=${encodeURIComponent(endTime)}`
            );
        }
    },

    // Email settings API
    email: {
        async getSettings() {
            return await AdminAPI.makeRequest('/api/admin/email-settings');
        },

        async updateSettings(data) {
            return await AdminAPI.makeRequest('/api/admin/email-settings', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
        },

        async testConfig() {
            return await AdminAPI.makeRequest('/api/admin/email-settings/test', {
                method: 'POST'
            });
        }
    },

    // Timezone API
    timezone: {
        async getSettings() {
            return await AdminAPI.makeRequest('/api/admin/timezone-settings/current');
        },

        async updateSettings(data) {
            return await AdminAPI.makeRequest('/api/admin/timezone-settings/update', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
        },

        async getTimezones() {
            return await AdminAPI.makeRequest('/api/admin/timezone-settings/timezones');
        }
    },

    // Logs API
    logs: {
        async getLogs(params = {}) {
            const queryParams = new URLSearchParams(params);
            return await AdminAPI.makeRequest(`/api/admin/logs?${queryParams}`);
        },

        async getLoggers() {
            return await AdminAPI.makeRequest('/api/admin/logs/loggers');
        },

        async getStats(hours = 24) {
            return await AdminAPI.makeRequest(`/api/admin/logs/stats?hours=${hours}`);
        },

        async cleanup(days) {
            return await AdminAPI.makeRequest(`/api/admin/logs/cleanup?days=${days}`, {
                method: 'DELETE'
            });
        },

        async vacuum() {
            return await AdminAPI.makeRequest('/api/admin/logs/vacuum', {
                method: 'POST'
            });
        },

        async getLogConfig() {
            return await AdminAPI.makeRequest('/api/admin/logs/config');
        },

        async updateLogConfig(configData) {
            return await AdminAPI.makeRequest('/api/admin/logs/config', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(configData)
            });
        }
    },

    // Legacy Claims API (backwards compatibility)
    claims: {
        async getMappings() {
            return await AdminAPI.oidcClaims.getMappings();
        },

        async getMapping(mappingId) {
            return await AdminAPI.oidcClaims.getMapping(mappingId);
        },

        async createMapping(mappingData) {
            return await AdminAPI.oidcClaims.createMapping(mappingData);
        },

        async updateMapping(mappingId, mappingData) {
            return await AdminAPI.oidcClaims.updateMapping(mappingId, mappingData);
        },

        async deleteMapping(mappingId) {
            return await AdminAPI.oidcClaims.deleteMapping(mappingId);
        },

        async discoverClaims(data) {
            return await AdminAPI.oidcClaims.discoverClaims(data);
        },

        async getUserProfiles() {
            return await AdminAPI.oidcClaims.getUserProfiles();
        },

        async getUserProfile(profileId) {
            return await AdminAPI.oidcClaims.getUserProfile(profileId);
        }
    },


    // Dynamic reports API
    dynamicReports: {
        async getColumns() {
            return await AdminAPI.makeRequest('/api/admin/dynamic-reports/columns');
        },

        async generate(data) {
            // Ensure data includes the new optional date fields
            const requestData = {
                selected_columns: data.selected_columns,
                months: data.months || 2,
                start_date: data.start_date || null,
                end_date: data.end_date || null,
                include_excel: data.include_excel || false
            };
            
            return await AdminAPI.makeRequest('/api/admin/dynamic-reports/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(requestData)
            });
        },

        async generateExcel(data) {
            // Ensure data includes the new optional date fields
            const requestData = {
                selected_columns: data.selected_columns,
                months: data.months || 2,
                start_date: data.start_date || null,
                end_date: data.end_date || null,
                include_excel: true
            };
            
            return await AdminAPI.makeRequest('/api/admin/dynamic-reports/generate/excel', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(requestData)
            });
        },

        async getTemplates() {
            return await AdminAPI.makeRequest('/api/admin/dynamic-reports/templates');
        },

        async createTemplate(templateData) {
            return await AdminAPI.makeRequest('/api/admin/dynamic-reports/templates', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(templateData)
            });
        },

        async deleteTemplate(templateId) {
            return await AdminAPI.makeRequest(`/api/admin/dynamic-reports/templates/${templateId}`, {
                method: 'DELETE'
            });
        },

        async generateFromTemplate(templateId, options = {}) {
            // Support both legacy months parameter and new date range options
            const params = new URLSearchParams();
            if (options.months !== undefined) {
                params.append('months', options.months);
            }
            if (options.include_excel !== undefined) {
                params.append('include_excel', options.include_excel);
            }
            
            const queryString = params.toString();
            return await AdminAPI.makeRequest(`/api/admin/dynamic-reports/templates/${templateId}/generate${queryString ? '?' + queryString : ''}`, {
                method: 'POST'
            });
        },

        async getScheduleSettings() {
            return await AdminAPI.makeRequest('/api/admin/dynamic-reports/schedule-settings');
        },

        async updateScheduleSettings(settings) {
            return await AdminAPI.makeRequest('/api/admin/dynamic-reports/schedule-settings', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(settings)
            });
        },

        async sendEmail(data) {
            return await AdminAPI.makeRequest('/api/admin/dynamic-reports/send-email', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
        },

        async sendTestEmail(data) {
            return await AdminAPI.makeRequest('/api/admin/dynamic-reports/send-test-email', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
        },

        // Scheduled reports management
        async getSchedules() {
            return await AdminAPI.makeRequest('/api/admin/dynamic-reports/schedules');
        },

        async createSchedule(scheduleData) {
            return await AdminAPI.makeRequest('/api/admin/dynamic-reports/schedules', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(scheduleData)
            });
        },

        async updateSchedule(scheduleId, scheduleData) {
            return await AdminAPI.makeRequest(`/api/admin/dynamic-reports/schedules/${scheduleId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(scheduleData)
            });
        },

        async deleteSchedule(scheduleId) {
            return await AdminAPI.makeRequest(`/api/admin/dynamic-reports/schedules/${scheduleId}`, {
                method: 'DELETE'
            });
        },

        async toggleSchedule(scheduleId) {
            return await AdminAPI.makeRequest(`/api/admin/dynamic-reports/schedules/${scheduleId}/toggle`, {
                method: 'POST'
            });
        }
    },

    // Backup API
    backup: {
        async getSettings() {
            return await AdminAPI.makeRequest('/api/admin/backup-settings/');
        },

        async updateSettings(data) {
            return await AdminAPI.makeRequest('/api/admin/backup-settings/', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
        },

        async testConnection() {
            return await AdminAPI.makeRequest('/api/admin/backup-settings/test-connection', {
                method: 'POST'
            });
        },

        async backupNow() {
            return await AdminAPI.makeRequest('/api/admin/backup-settings/backup-now', {
                method: 'POST'
            });
        },

        async listBackups(limit = 10) {
            return await AdminAPI.makeRequest(`/api/admin/backup-settings/list-backups?limit=${limit}`);
        }
    },

    // Bookings API
    bookings: {
        async getAll(params = {}) {
            const queryParams = new URLSearchParams();
            Object.keys(params).forEach(key => {
                if (params[key] !== null && params[key] !== undefined && params[key] !== '') {
                    queryParams.append(key, params[key]);
                }
            });
            const queryString = queryParams.toString();
            return await AdminAPI.makeRequest(`/api/admin/bookings/bookings${queryString ? '?' + queryString : ''}`);
        },

        async getCount(params = {}) {
            const queryParams = new URLSearchParams();
            Object.keys(params).forEach(key => {
                if (params[key] !== null && params[key] !== undefined && params[key] !== '') {
                    queryParams.append(key, params[key]);
                }
            });
            const queryString = queryParams.toString();
            return await AdminAPI.makeRequest(`/api/admin/bookings/bookings/count${queryString ? '?' + queryString : ''}`);
        },

        async delete(bookingId) {
            return await AdminAPI.makeRequest(`/api/admin/bookings/bookings/${bookingId}`, {
                method: 'DELETE'
            });
        },

        async exportExcel(params = {}) {
            const queryParams = new URLSearchParams();
            Object.keys(params).forEach(key => {
                if (params[key] !== null && params[key] !== undefined && params[key] !== '') {
                    queryParams.append(key, params[key]);
                }
            });
            const queryString = queryParams.toString();
            return await AdminAPI.makeRequest(`/api/admin/bookings/bookings/export${queryString ? '?' + queryString : ''}`);
        },

        async getUsersWithBookings() {
            return await AdminAPI.makeRequest('/api/admin/bookings/bookings/users');
        },

        async getParkingLotsWithBookings() {
            return await AdminAPI.makeRequest('/api/admin/bookings/bookings/parking-lots');
        }
    }
};

// Export for global access
window.AdminAPI = AdminAPI;

AdminLogs.log('INFO', 'Admin API client module loaded!');
