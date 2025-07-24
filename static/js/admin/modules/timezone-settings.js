/* Timezone Settings Module - Timezone configuration functionality */

const AdminTimezone = {
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
                timezones.forEach(tz => {
                    // Handle both string and object formats
                    const timezoneValue = typeof tz === 'string' ? tz : tz.value || tz.name || tz;
                    const timezoneDisplay = typeof tz === 'string' ? tz : tz.display || tz.name || tz.value || tz;
                    
                    if (timezoneValue && typeof timezoneValue === 'string') {
                        const option = document.createElement('option');
                        option.value = timezoneValue;
                        option.textContent = typeof timezoneDisplay === 'string' ? timezoneDisplay.replace(/_/g, ' ') : timezoneValue.replace(/_/g, ' ');
                        if (timezoneValue === settings.timezone) {
                            option.selected = true;
                        }
                        select.appendChild(option);
                    }
                });
            } else {
                AdminNotifications.showError('Failed to load timezone settings');
            }
        } catch (error) {
            AdminNotifications.handleApiError(error, 'Error loading timezone settings');
        }
    },

    // Save timezone settings
    async saveTimezoneSettings(event) {
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

    // Initialize timezone settings module
    init() {
        const saveButton = document.getElementById('save-timezone-settings');
        if (saveButton) {
            saveButton.addEventListener('click', this.saveTimezoneSettings.bind(this));
        }
        console.log('Timezone settings module initialized');
    }
};

// Export for global access
window.AdminTimezone = AdminTimezone;

// Initialize when module loads
AdminTimezone.init();

console.log('Admin timezone settings module loaded!');
