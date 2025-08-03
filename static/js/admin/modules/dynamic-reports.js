/* Dynamic Reports Module - Dynamic report builder functionality */

const AdminDynamicReports = {
    // Module state
    availableColumns: [],
    selectedColumns: [],

    // Load dynamic reports data
    async loadDynamicReportsData() {
        await this.loadAvailableColumns();
        await this.loadReportTemplates();
    },

    // Load available columns
    async loadAvailableColumns() {
        try {
            const response = await AdminAPI.dynamicReports.getColumns();

            if (response.ok) {
                const data = await response.json();
                this.availableColumns = data.columns;
                this.renderAvailableColumns();
            } else {
                AdminNotifications.showError('Failed to load available columns');
            }
        } catch (error) {
            AdminNotifications.handleApiError(error, 'Error loading available columns');
        }
    },

    // Render available columns
    renderAvailableColumns() {
        const container = document.getElementById('available-columns-list');
        if (!container) return;
        
        container.innerHTML = '';
        this.availableColumns.forEach(column => {
            const div = document.createElement('div');
            div.className = 'border rounded p-2 mb-2 cursor-pointer';
            div.style.cursor = 'pointer';
            div.innerHTML = `
                <strong>${column.display_label}</strong>
                <br><small class="text-muted">${column.column_name} (${column.column_type})</small>
            `;
            div.onclick = () => this.addColumnToSelection(column);
            container.appendChild(div);
        });
    },

    // Add column to selection
    addColumnToSelection(column) {
        if (!this.selectedColumns.find(col => col.column_name === column.column_name)) {
            this.selectedColumns.push(column);
            this.renderSelectedColumns();
        }
    },

    // Render selected columns
    renderSelectedColumns() {
        const container = document.getElementById('selected-columns-list');
        if (!container) return;
        
        if (this.selectedColumns.length === 0) {
            container.innerHTML = '<p class="text-muted">No columns selected</p>';
            return;
        }
        
        container.innerHTML = '';
        this.selectedColumns.forEach((column, index) => {
            const div = document.createElement('div');
            div.className = 'border rounded p-2 mb-2 d-flex justify-content-between align-items-center';
            div.innerHTML = `
                <div>
                    <strong>${column.display_label}</strong>
                    <br><small class="text-muted">${column.column_name}</small>
                </div>
                <button class="btn btn-sm btn-outline-danger" onclick="AdminDynamicReports.removeColumnFromSelection(${index})">×</button>
            `;
            container.appendChild(div);
        });
    },

    // Remove column from selection
    removeColumnFromSelection(index) {
        this.selectedColumns.splice(index, 1);
        this.renderSelectedColumns();
    },

    // Clear selected columns
    clearSelectedColumns() {
        this.selectedColumns = [];
        this.renderSelectedColumns();
    },

    // Generate dynamic report
    async generateDynamicReport() {
        if (this.selectedColumns.length === 0) {
            AdminNotifications.showError('Please select at least one column');
            return;
        }
        
        try {
            const columnNames = this.selectedColumns.map(col => col.column_name);
            const reportParams = this._getReportDateParameters();
            
            const response = await AdminAPI.dynamicReports.generate({
                selected_columns: columnNames,
                ...reportParams
            });

            if (response.ok) {
                const reportData = await response.json();
                this.displayDynamicReport(reportData);
            } else {
                AdminNotifications.showError('Failed to generate dynamic report');
            }
        } catch (error) {
            AdminNotifications.handleApiError(error, 'Error generating dynamic report');
        }
    },

    // Get report date parameters based on current UI settings
    _getReportDateParameters() {
        const useCustomDates = document.getElementById('use-custom-dates')?.checked || false;
        
        if (useCustomDates) {
            const startDateElement = document.getElementById('custom-start-date');
            const endDateElement = document.getElementById('custom-end-date');
            
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
            const monthsElement = document.getElementById('dynamic-report-months');
            const months = monthsElement ? (monthsElement.value !== '' ? parseInt(monthsElement.value) : 2) : 2;
            
            return {
                months: months,
                start_date: null,
                end_date: null
            };
        }
    },

    // Toggle date selection mode
    toggleDateSelectionMode() {
        const useCustomDates = document.getElementById('use-custom-dates')?.checked || false;
        const monthsSection = document.getElementById('months-selection-section');
        const customDatesSection = document.getElementById('custom-dates-selection-section');
        
        if (monthsSection && customDatesSection) {
            if (useCustomDates) {
                monthsSection.style.display = 'none';
                customDatesSection.style.display = 'block';
                this._setDefaultCustomDates();
            } else {
                monthsSection.style.display = 'block';
                customDatesSection.style.display = 'none';
            }
        }
    },

    // Set sensible defaults for custom date inputs
    _setDefaultCustomDates() {
        const startDateElement = document.getElementById('custom-start-date');
        const endDateElement = document.getElementById('custom-end-date');
        
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
        const startDateElement = document.getElementById('custom-start-date');
        const endDateElement = document.getElementById('custom-end-date');
        
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
                AdminNotifications.showWarning('Selected date range is longer than 2 years. Report generation may take longer.');
            }
            
            return true;
        }
        
        return false;
    },

    // Display dynamic report
    displayDynamicReport(reportData) {
        const resultsDiv = document.getElementById('dynamic-report-results');
        const summarySpan = document.getElementById('dynamic-report-summary');
        const headersDiv = document.getElementById('dynamic-report-headers');
        const dataDiv = document.getElementById('dynamic-report-data');
        
        if (!resultsDiv || !summarySpan || !headersDiv || !dataDiv) return;
        
        // Show results
        resultsDiv.style.display = 'block';
        
        // Update summary
        summarySpan.textContent = `${reportData.total_records} records`;
        
        // Create headers
        headersDiv.innerHTML = '<tr>' + 
            reportData.columns.map(col => `<th>${col.display_label}</th>`).join('') + 
            '</tr>';
        
        // Create data rows
        dataDiv.innerHTML = '';
        reportData.data.forEach(record => {
            const row = document.createElement('tr');
            row.innerHTML = reportData.columns.map(col => {
                let value = record[col.column_name];
                if (Array.isArray(value)) {
                    value = value.join(', ');
                } else if (value === null || value === undefined) {
                    value = '-';
                }
                return `<td>${value}</td>`;
            }).join('');
            dataDiv.appendChild(row);
        });
        
        AdminNotifications.showSuccess('Dynamic report generated successfully');
    },

    // Download dynamic report Excel
    async downloadDynamicReportExcel() {
        if (this.selectedColumns.length === 0) {
            AdminNotifications.showError('Please select at least one column');
            return;
        }
        
        try {
            const monthsElement = document.getElementById('dynamic-report-months');
            const months = monthsElement ? (monthsElement.value !== '' ? parseInt(monthsElement.value) : 2) : 2;
            const columnNames = this.selectedColumns.map(col => col.column_name);
            
            const response = await AdminAPI.dynamicReports.generateExcel({
                selected_columns: columnNames,
                months: months
            });

            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.style.display = 'none';
                a.href = url;
                a.download = `dynamic_report_${new Date().toISOString().split('T')[0]}.xlsx`;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
                
                AdminNotifications.showSuccess('Dynamic Excel report downloaded successfully');
            } else {
                AdminNotifications.showError('Failed to download Excel report');
            }
        } catch (error) {
            AdminNotifications.handleApiError(error, 'Error downloading Excel report');
        }
    },

    // Load report templates
    async loadReportTemplates() {
        try {
            const response = await AdminAPI.dynamicReports.getTemplates();

            if (response.ok) {
                const templates = await response.json();
                this.renderReportTemplates(templates);
            } else {
                AdminNotifications.showError('Failed to load report templates');
            }
        } catch (error) {
            AdminNotifications.handleApiError(error, 'Error loading report templates');
        }
    },

    // Render report templates
    renderReportTemplates(templates) {
        const container = document.getElementById('report-templates-list');
        if (!container) return;
        
        if (templates.length === 0) {
            container.innerHTML = '<p class="text-muted">No templates saved</p>';
            return;
        }
        
        container.innerHTML = '';
        templates.forEach(template => {
            const div = document.createElement('div');
            div.className = 'border rounded p-2 mb-2';
            div.innerHTML = `
                <div class="d-flex justify-content-between align-items-start">
                    <div>
                        <strong>${template.name}</strong>
                        ${template.is_default ? '<span class="badge bg-primary ms-2">Default</span>' : ''}
                        <br><small class="text-muted">${template.description || 'No description'}</small>
                        <br><small class="text-info">${template.selected_columns.length} columns</small>
                    </div>
                    <div>
                        <button class="btn btn-sm btn-outline-primary me-1" onclick="AdminDynamicReports.loadTemplate(${template.id})">Load</button>
                        <button class="btn btn-sm btn-outline-success me-1" onclick="AdminDynamicReports.generateFromTemplate(${template.id})">Generate</button>
                        ${!template.is_default ? `<button class="btn btn-sm btn-outline-danger" onclick="AdminDynamicReports.deleteTemplate(${template.id})">Delete</button>` : ''}
                    </div>
                </div>
            `;
            container.appendChild(div);
        });
    },

    // Load template
    async loadTemplate(templateId) {
        try {
            const response = await AdminAPI.dynamicReports.getTemplates();
            if (response.ok) {
                const templates = await response.json();
                const template = templates.find(t => t.id === templateId);
                if (template) {
                    // Load the template's columns into selection
                    this.selectedColumns = template.selected_columns.map(colName => 
                        this.availableColumns.find(col => col.column_name === colName)
                    ).filter(col => col !== undefined);
                    this.renderSelectedColumns();
                    AdminNotifications.showSuccess(`Loaded template: ${template.name}`);
                }
            }
        } catch (error) {
            AdminNotifications.handleApiError(error, 'Error loading template');
        }
    },

    // Generate from template
    async generateFromTemplate(templateId) {
        try {
            const monthsElement = document.getElementById('dynamic-report-months');
            const months = monthsElement ? (monthsElement.value !== '' ? parseInt(monthsElement.value) : 2) : 2;
            
            const response = await AdminAPI.dynamicReports.generateFromTemplate(templateId, months);

            if (response.ok) {
                const reportData = await response.json();
                this.displayDynamicReport(reportData);
                AdminNotifications.showSuccess('Generated report from template');
            } else {
                AdminNotifications.showError('Failed to generate report from template');
            }
        } catch (error) {
            AdminNotifications.handleApiError(error, 'Error generating report from template');
        }
    },

    // Delete template
    async deleteTemplate(templateId) {
        const confirmed = await AdminNotifications.confirm('Are you sure you want to delete this template?');
        if (!confirmed) return;
        
        try {
            const response = await AdminAPI.dynamicReports.deleteTemplate(templateId);

            if (response.ok) {
                AdminNotifications.showSuccess('Template deleted successfully');
                this.loadReportTemplates();
            } else {
                AdminNotifications.showError('Failed to delete template');
            }
        } catch (error) {
            AdminNotifications.handleApiError(error, 'Error deleting template');
        }
    },

    // Show report template modal
    async showReportTemplateModal() {
        if (this.selectedColumns.length === 0) {
            AdminNotifications.showError('Please select columns before saving a template');
            return;
        }
        
        const name = await AdminNotifications.prompt('Enter template name:');
        if (!name) return;
        
        const description = await AdminNotifications.prompt('Enter template description (optional):') || '';
        
        this.saveReportTemplate(name, description);
    },

    // Save report template
    async saveReportTemplate(name, description) {
        try {
            const columnNames = this.selectedColumns.map(col => col.column_name);
            
            const response = await AdminAPI.dynamicReports.createTemplate({
                name: name,
                description: description,
                selected_columns: columnNames,
                is_default: false
            });

            if (response.ok) {
                AdminNotifications.showSuccess('Report template saved successfully');
                this.loadReportTemplates();
            } else {
                AdminNotifications.showError('Failed to save template');
            }
        } catch (error) {
            AdminNotifications.handleApiError(error, 'Error saving template');
        }
    },

    // Initialize dynamic reports module
    init() {
        AdminLogs.log('INFO', 'Initializing dynamic reports module...');
        
        // Setup event listeners with retry mechanism
        this.setupEventListeners();
        
        AdminLogs.log('INFO', 'Dynamic reports module initialized');
    },

    // Setup event listeners with proper error handling
    setupEventListeners() {
        // Save Template button
        const saveTemplateBtn = document.getElementById('save-report-template-btn');
        if (saveTemplateBtn && !saveTemplateBtn.hasAttribute('data-dynamic-reports-listener')) {
            saveTemplateBtn.addEventListener('click', this.showReportTemplateModal.bind(this));
            saveTemplateBtn.setAttribute('data-dynamic-reports-listener', 'true');
            AdminLogs.log('DEBUG', 'Save template button listener attached');
        }

        // Refresh button
        const refreshBtn = document.getElementById('refresh-dynamic-reports-btn');
        if (refreshBtn && !refreshBtn.hasAttribute('data-dynamic-reports-listener')) {
            refreshBtn.addEventListener('click', this.loadDynamicReportsData.bind(this));
            refreshBtn.setAttribute('data-dynamic-reports-listener', 'true');
            AdminLogs.log('DEBUG', 'Refresh dynamic reports button listener attached');
        }

        // Generate Report button
        const generateBtn = document.getElementById('generate-dynamic-report-btn');
        if (generateBtn && !generateBtn.hasAttribute('data-dynamic-reports-listener')) {
            generateBtn.addEventListener('click', this.generateDynamicReport.bind(this));
            generateBtn.setAttribute('data-dynamic-reports-listener', 'true');
            AdminLogs.log('DEBUG', 'Generate report button listener attached');
        }

        // Download Excel button
        const downloadExcelBtn = document.getElementById('download-dynamic-report-excel-btn');
        if (downloadExcelBtn && !downloadExcelBtn.hasAttribute('data-dynamic-reports-listener')) {
            downloadExcelBtn.addEventListener('click', this.downloadDynamicReportExcel.bind(this));
            downloadExcelBtn.setAttribute('data-dynamic-reports-listener', 'true');
            AdminLogs.log('DEBUG', 'Download Excel button listener attached');
        }

        // Clear Selection button
        const clearSelectionBtn = document.getElementById('clear-selected-columns-btn');
        if (clearSelectionBtn && !clearSelectionBtn.hasAttribute('data-dynamic-reports-listener')) {
            clearSelectionBtn.addEventListener('click', this.clearSelectedColumns.bind(this));
            clearSelectionBtn.setAttribute('data-dynamic-reports-listener', 'true');
            AdminLogs.log('DEBUG', 'Clear selection button listener attached');
        }

        // Email & Scheduling tab activation
        const emailTabBtn = document.getElementById('email-dynamic-tab');
        if (emailTabBtn && !emailTabBtn.hasAttribute('data-dynamic-reports-listener')) {
            emailTabBtn.addEventListener('click', this.initEmailScheduling.bind(this));
            emailTabBtn.setAttribute('data-dynamic-reports-listener', 'true');
            AdminLogs.log('DEBUG', 'Email tab button listener attached');
        }

        // Unified email form listeners
        this.setupUnifiedEmailListeners();

        // If elements aren't found, they might not be rendered yet
        if (!saveTemplateBtn || !refreshBtn || !generateBtn || !downloadExcelBtn || !clearSelectionBtn) {
            AdminLogs.log('DEBUG', 'Some dynamic reports elements not found yet, will retry when tab is activated');
        }
    },

    // Load dynamic report scheduling settings
    async loadDynamicReportScheduleSettings() {
        try {
            const response = await AdminAPI.dynamicReports.getScheduleSettings();

            if (response.ok) {
                const settings = await response.json();
                this.populateScheduleSettingsForm(settings);
            } else {
                AdminNotifications.showError('Failed to load dynamic report schedule settings');
            }
        } catch (error) {
            AdminNotifications.handleApiError(error, 'Error loading dynamic report schedule settings');
        }
    },

    // Populate schedule settings form
    populateScheduleSettingsForm(settings) {
        const form = document.getElementById('dynamic-report-schedule-form');
        if (!form) return;

        // Set form values
        const enabledCheckbox = form.querySelector('#dynamic-reports-enabled');
        if (enabledCheckbox) enabledCheckbox.checked = settings.dynamic_reports_enabled;

        const recipientsInput = form.querySelector('#dynamic-report-recipients');
        if (recipientsInput) recipientsInput.value = settings.dynamic_report_recipients.join(', ');

        const hourSelect = form.querySelector('#dynamic-report-schedule-hour');
        if (hourSelect) hourSelect.value = settings.dynamic_report_schedule_hour;

        const frequencySelect = form.querySelector('#dynamic-report-frequency');
        if (frequencySelect) frequencySelect.value = settings.dynamic_report_frequency;

        const templateSelect = form.querySelector('#dynamic-report-template-id');
        if (templateSelect) templateSelect.value = settings.dynamic_report_template_id || '';

        const timezoneSelect = form.querySelector('#dynamic-report-timezone');
        if (timezoneSelect) timezoneSelect.value = settings.timezone;

        // Show last sent time
        const lastSentElement = document.getElementById('dynamic-last-report-sent');
        if (lastSentElement) {
            if (settings.last_dynamic_report_sent) {
                const date = new Date(settings.last_dynamic_report_sent);
                lastSentElement.textContent = date.toLocaleString();
            } else {
                lastSentElement.textContent = 'Never';
            }
        }
    },

    // Save dynamic report schedule settings
    async saveDynamicReportScheduleSettings() {
        const form = document.getElementById('dynamic-report-schedule-form');
        if (!form) return;

        try {
            const formData = new FormData(form);
            
            // Parse recipients
            const recipientsText = formData.get('dynamic_report_recipients') || '';
            const recipients = recipientsText.split(',').map(email => email.trim()).filter(email => email);

            const settings = {
                dynamic_reports_enabled: formData.has('dynamic_reports_enabled'),
                dynamic_report_recipients: recipients,
                dynamic_report_schedule_hour: parseInt(formData.get('dynamic_report_schedule_hour')),
                dynamic_report_frequency: formData.get('dynamic_report_frequency'),
                dynamic_report_template_id: formData.get('dynamic_report_template_id') ? parseInt(formData.get('dynamic_report_template_id')) : null,
                timezone: formData.get('timezone')
            };

            const response = await AdminAPI.dynamicReports.updateScheduleSettings(settings);

            if (response.ok) {
                AdminNotifications.showSuccess('Dynamic report schedule settings saved successfully');
                this.loadDynamicReportScheduleSettings(); // Refresh to show updated values
            } else {
                AdminNotifications.showError('Failed to save dynamic report schedule settings');
            }
        } catch (error) {
            AdminNotifications.handleApiError(error, 'Error saving dynamic report schedule settings');
        }
    },

    // Send dynamic report email
    async sendDynamicReportEmail() {
        const templateId = document.getElementById('email-template-id')?.value;
        const recipientsText = document.getElementById('email-recipients')?.value;
        const monthsElement = document.getElementById('email-report-months');
        const months = monthsElement ? (monthsElement.value !== '' ? parseInt(monthsElement.value) : 2) : 2;
        const includeExcel = document.getElementById('email-include-excel')?.checked !== false;

        if (!templateId) {
            AdminNotifications.showError('Please select a template');
            return;
        }

        if (!recipientsText) {
            AdminNotifications.showError('Please enter recipient email addresses');
            return;
        }

        const recipients = recipientsText.split(',').map(email => email.trim()).filter(email => email);
        if (recipients.length === 0) {
            AdminNotifications.showError('Please enter valid recipient email addresses');
            return;
        }

        try {
            const response = await AdminAPI.dynamicReports.sendEmail({
                template_id: parseInt(templateId),
                recipients: recipients,
                months: months,
                include_excel: includeExcel
            });

            if (response.ok) {
                AdminNotifications.showSuccess(`Dynamic report sent successfully to ${recipients.length} recipients`);
            } else {
                AdminNotifications.showError('Failed to send dynamic report email');
            }
        } catch (error) {
            AdminNotifications.handleApiError(error, 'Error sending dynamic report email');
        }
    },

    // Send test dynamic report email
    async sendTestDynamicReportEmail() {
        const templateId = document.getElementById('test-email-template-id')?.value;
        const testEmail = document.getElementById('test-email-address')?.value;

        if (!templateId) {
            AdminNotifications.showError('Please select a template');
            return;
        }

        if (!testEmail) {
            AdminNotifications.showError('Please enter a test email address');
            return;
        }

        // Basic email validation
        const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailPattern.test(testEmail)) {
            AdminNotifications.showError('Please enter a valid email address');
            return;
        }

        try {
            const response = await AdminAPI.dynamicReports.sendTestEmail({
                template_id: parseInt(templateId),
                test_email: testEmail
            });

            if (response.ok) {
                AdminNotifications.showSuccess(`Test dynamic report sent successfully to ${testEmail}`);
            } else {
                AdminNotifications.showError('Failed to send test dynamic report email');
            }
        } catch (error) {
            AdminNotifications.handleApiError(error, 'Error sending test dynamic report email');
        }
    },

    // Load templates for email dropdowns
    async loadTemplatesForEmailDropdowns() {
        try {
            const response = await AdminAPI.dynamicReports.getTemplates();

            if (response.ok) {
                const templates = await response.json();
                this.populateTemplateDropdowns(templates);
            }
        } catch (error) {
            AdminLogs.log('WARNING', 'Error loading templates for dropdowns:', error);
        }
    },

    // Populate template dropdowns
    populateTemplateDropdowns(templates) {
        const dropdowns = [
            'dynamic-report-template-id',
            'email-template-id', 
            'test-email-template-id'
        ];

        dropdowns.forEach(dropdownId => {
            const dropdown = document.getElementById(dropdownId);
            if (dropdown) {
                // Clear existing options except the first one
                while (dropdown.children.length > 1) {
                    dropdown.removeChild(dropdown.lastChild);
                }

                // Add template options
                templates.forEach(template => {
                    const option = document.createElement('option');
                    option.value = template.id;
                    option.textContent = template.name;
                    dropdown.appendChild(option);
                });
            }
        });
    },

    // Initialize email scheduling functionality
    initEmailScheduling() {
        // Load schedule settings
        this.loadDynamicReportScheduleSettings();
        
        // Load templates for dropdowns
        this.loadTemplatesForEmailDropdowns();
    },

    // Setup unified email form listeners
    setupUnifiedEmailListeners() {
        // Sending method radio buttons
        const methodRadios = document.querySelectorAll('input[name="sending-method"]');
        methodRadios.forEach(radio => {
            if (!radio.hasAttribute('data-unified-listener')) {
                radio.addEventListener('change', this.handleSendingMethodChange.bind(this));
                radio.setAttribute('data-unified-listener', 'true');
            }
        });

        // Template selection for unified form
        const unifiedTemplateSelect = document.getElementById('unified-template-id');
        if (unifiedTemplateSelect && !unifiedTemplateSelect.hasAttribute('data-unified-listener')) {
            unifiedTemplateSelect.addEventListener('change', this.updateUnifiedStatus.bind(this));
            unifiedTemplateSelect.setAttribute('data-unified-listener', 'true');
        }
    },

    // Handle sending method change
    handleSendingMethodChange(event) {
        const method = event.target.value;
        
        // Hide all recipient sections first
        document.getElementById('send-now-recipients').style.display = 'none';
        document.getElementById('test-email-recipient').style.display = 'none';
        document.getElementById('schedule-recipients').style.display = 'none';
        document.getElementById('report-settings-section').style.display = 'none';
        document.getElementById('schedule-settings-section').style.display = 'none';

        // Update action button text
        const actionBtn = document.getElementById('unified-action-btn');
        
        if (method === 'send_now') {
            document.getElementById('send-now-recipients').style.display = 'block';
            document.getElementById('report-settings-section').style.display = 'block';
            actionBtn.innerHTML = '📧 Send Now';
        } else if (method === 'test') {
            document.getElementById('test-email-recipient').style.display = 'block';
            document.getElementById('report-settings-section').style.display = 'block';
            actionBtn.innerHTML = '🧪 Send Test';
        } else if (method === 'schedule') {
            document.getElementById('schedule-recipients').style.display = 'block';
            document.getElementById('schedule-settings-section').style.display = 'block';
            actionBtn.innerHTML = '⏰ Save Schedule';
        }
    },

    // Handle unified email action
    async handleUnifiedEmailAction() {
        const method = document.querySelector('input[name="sending-method"]:checked')?.value;
        
        if (method === 'send_now') {
            await this.handleSendNow();
        } else if (method === 'test') {
            await this.handleSendTest();
        } else if (method === 'schedule') {
            await this.handleSaveSchedule();
        }
    },

    // Handle send now action
    async handleSendNow() {
        const templateId = document.getElementById('unified-template-id').value;
        const recipientsText = document.getElementById('unified-recipients').value;
        const monthsElement = document.getElementById('unified-report-months');
        const months = monthsElement ? (monthsElement.value !== '' ? parseInt(monthsElement.value) : 2) : 2;
        const includeExcel = document.getElementById('unified-include-excel').checked;

        if (!templateId) {
            AdminNotifications.showError('Please select a template');
            return;
        }

        if (!recipientsText) {
            AdminNotifications.showError('Please enter recipient email addresses');
            return;
        }

        const recipients = recipientsText.split(',').map(email => email.trim()).filter(email => email);
        if (recipients.length === 0) {
            AdminNotifications.showError('Please enter valid recipient email addresses');
            return;
        }

        try {
            const response = await AdminAPI.dynamicReports.sendEmail({
                template_id: parseInt(templateId),
                recipients: recipients,
                months: months,
                include_excel: includeExcel
            });

            if (response.ok) {
                AdminNotifications.showSuccess(`Dynamic report sent successfully to ${recipients.length} recipients`);
            } else {
                AdminNotifications.showError('Failed to send dynamic report email');
            }
        } catch (error) {
            AdminNotifications.handleApiError(error, 'Error sending dynamic report email');
        }
    },

    // Handle send test action
    async handleSendTest() {
        const templateId = document.getElementById('unified-template-id').value;
        const testEmail = document.getElementById('unified-test-email').value;

        if (!templateId) {
            AdminNotifications.showError('Please select a template');
            return;
        }

        if (!testEmail) {
            AdminNotifications.showError('Please enter a test email address');
            return;
        }

        // Basic email validation
        const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailPattern.test(testEmail)) {
            AdminNotifications.showError('Please enter a valid email address');
            return;
        }

        try {
            const response = await AdminAPI.dynamicReports.sendTestEmail({
                template_id: parseInt(templateId),
                test_email: testEmail
            });

            if (response.ok) {
                AdminNotifications.showSuccess(`Test dynamic report sent successfully to ${testEmail}`);
            } else {
                AdminNotifications.showError('Failed to send test dynamic report email');
            }
        } catch (error) {
            AdminNotifications.handleApiError(error, 'Error sending test dynamic report email');
        }
    },

    // Handle save schedule action
    async handleSaveSchedule() {
        const templateId = document.getElementById('unified-template-id').value;
        const recipientsText = document.getElementById('unified-schedule-recipients').value;
        const enabled = document.getElementById('unified-schedule-enabled').checked;
        const frequency = document.getElementById('unified-schedule-frequency').value;
        const hour = parseInt(document.getElementById('unified-schedule-hour').value);
        const timezone = document.getElementById('unified-schedule-timezone').value;

        if (!templateId) {
            AdminNotifications.showError('Please select a template');
            return;
        }

        if (!recipientsText) {
            AdminNotifications.showError('Please enter recipient email addresses');
            return;
        }

        const recipients = recipientsText.split(',').map(email => email.trim()).filter(email => email);
        if (recipients.length === 0) {
            AdminNotifications.showError('Please enter valid recipient email addresses');
            return;
        }

        try {
            const settings = {
                dynamic_reports_enabled: enabled,
                dynamic_report_recipients: recipients,
                dynamic_report_schedule_hour: hour,
                dynamic_report_frequency: frequency,
                dynamic_report_template_id: parseInt(templateId),
                timezone: timezone
            };

            const response = await AdminAPI.dynamicReports.updateScheduleSettings(settings);

            if (response.ok) {
                AdminNotifications.showSuccess('Schedule settings saved successfully');
                this.updateUnifiedStatus();
            } else {
                AdminNotifications.showError('Failed to save schedule settings');
            }
        } catch (error) {
            AdminNotifications.handleApiError(error, 'Error saving schedule settings');
        }
    },

    // Reset unified form
    resetUnifiedForm() {
        // Reset to send now method
        document.getElementById('method-send-now').checked = true;
        this.handleSendingMethodChange({ target: { value: 'send_now' } });

        // Clear all form fields
        document.getElementById('unified-template-id').value = '';
        document.getElementById('unified-recipients').value = '';
        document.getElementById('unified-test-email').value = '';
        document.getElementById('unified-schedule-recipients').value = '';
        document.getElementById('unified-report-months').value = '2';
        document.getElementById('unified-include-excel').checked = true;
        document.getElementById('unified-schedule-enabled').checked = false;
        document.getElementById('unified-schedule-frequency').value = 'weekly';
        document.getElementById('unified-schedule-hour').value = '9';
        document.getElementById('unified-schedule-timezone').value = 'UTC';
    },

    // Update unified status display
    async updateUnifiedStatus() {
        try {
            const response = await AdminAPI.dynamicReports.getScheduleSettings();
            if (response.ok) {
                const settings = await response.json();
                
                // Update status indicators
                const statusElement = document.getElementById('unified-schedule-status');
                const templateElement = document.getElementById('unified-schedule-template');
                const recipientCountElement = document.getElementById('unified-schedule-recipient-count');
                const frequencyElement = document.getElementById('unified-schedule-freq');
                const lastSentElement = document.getElementById('unified-last-sent');

                if (statusElement) {
                    statusElement.className = settings.dynamic_reports_enabled ? 'badge bg-success' : 'badge bg-secondary';
                    statusElement.textContent = settings.dynamic_reports_enabled ? 'Enabled' : 'Disabled';
                }

                if (templateElement) {
                    // Get template name
                    const templateId = settings.dynamic_report_template_id;
                    if (templateId) {
                        const templatesResponse = await AdminAPI.dynamicReports.getTemplates();
                        if (templatesResponse.ok) {
                            const templates = await templatesResponse.json();
                            const template = templates.find(t => t.id === templateId);
                            templateElement.textContent = template ? template.name : 'Unknown';
                        }
                    } else {
                        templateElement.textContent = 'None';
                    }
                }

                if (recipientCountElement) {
                    recipientCountElement.textContent = settings.dynamic_report_recipients.length;
                }

                if (frequencyElement) {
                    frequencyElement.textContent = settings.dynamic_report_frequency || '-';
                }

                if (lastSentElement) {
                    if (settings.last_dynamic_report_sent) {
                        const date = new Date(settings.last_dynamic_report_sent);
                        lastSentElement.textContent = date.toLocaleString();
                    } else {
                        lastSentElement.textContent = 'Never';
                    }
                }
            }
        } catch (error) {
            console.warn('Error updating unified status:', error);
        }
    },

    // Initialize email scheduling functionality
    initEmailScheduling() {
        // Load schedule settings for unified interface
        this.updateUnifiedStatus();
        
        // Load templates for unified dropdown
        this.loadTemplatesForUnifiedDropdown();
        
        // Set up initial form state
        this.handleSendingMethodChange({ target: { value: 'send_now' } });
    },

    // Load templates for unified dropdown
    async loadTemplatesForUnifiedDropdown() {
        try {
            const response = await AdminAPI.dynamicReports.getTemplates();

            if (response.ok) {
                const templates = await response.json();
                const dropdown = document.getElementById('unified-template-id');
                
                if (dropdown) {
                    // Clear existing options except the first one
                    while (dropdown.children.length > 1) {
                        dropdown.removeChild(dropdown.lastChild);
                    }

                    // Add template options
                    templates.forEach(template => {
                        const option = document.createElement('option');
                        option.value = template.id;
                        option.textContent = template.name;
                        dropdown.appendChild(option);
                    });
                }
            }
        } catch (error) {
            console.warn('Error loading templates for unified dropdown:', error);
        }
    },

    // Handle modal unified email action
    async handleModalUnifiedEmailAction() {
        const method = document.querySelector('input[name="modal-sending-method"]:checked')?.value;
        
        if (method === 'send_now') {
            await this.handleModalSendNow();
        } else if (method === 'test') {
            await this.handleModalSendTest();
        } else if (method === 'schedule') {
            await this.handleModalSaveSchedule();
        }
    },

    // Handle modal send now action
    async handleModalSendNow() {
        const templateId = document.getElementById('modal-unified-template-id').value;
        const recipientsText = document.getElementById('modal-unified-recipients').value;
        const monthsElement = document.getElementById('modal-unified-report-months');
        const months = monthsElement ? (monthsElement.value !== '' ? parseInt(monthsElement.value) : 2) : 2;
        const includeExcel = document.getElementById('modal-unified-include-excel').checked;

        if (!templateId) {
            AdminNotifications.showError('Please select a template');
            return;
        }

        if (!recipientsText) {
            AdminNotifications.showError('Please enter recipient email addresses');
            return;
        }

        const recipients = recipientsText.split(',').map(email => email.trim()).filter(email => email);
        if (recipients.length === 0) {
            AdminNotifications.showError('Please enter valid recipient email addresses');
            return;
        }

        try {
            const response = await AdminAPI.dynamicReports.sendEmail({
                template_id: parseInt(templateId),
                recipients: recipients,
                months: months,
                include_excel: includeExcel
            });

            if (response.ok) {
                AdminNotifications.showSuccess(`Dynamic report sent successfully to ${recipients.length} recipients`);
                // Close modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('send-dynamic-report-modal'));
                if (modal) modal.hide();
            } else {
                AdminNotifications.showError('Failed to send dynamic report email');
            }
        } catch (error) {
            AdminNotifications.handleApiError(error, 'Error sending dynamic report email');
        }
    },

    // Handle modal send test action
    async handleModalSendTest() {
        const templateId = document.getElementById('modal-unified-template-id').value;
        const testEmail = document.getElementById('modal-unified-test-email').value;

        if (!templateId) {
            AdminNotifications.showError('Please select a template');
            return;
        }

        if (!testEmail) {
            AdminNotifications.showError('Please enter a test email address');
            return;
        }

        // Basic email validation
        const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailPattern.test(testEmail)) {
            AdminNotifications.showError('Please enter a valid email address');
            return;
        }

        try {
            const response = await AdminAPI.dynamicReports.sendTestEmail({
                template_id: parseInt(templateId),
                test_email: testEmail
            });

            if (response.ok) {
                AdminNotifications.showSuccess(`Test dynamic report sent successfully to ${testEmail}`);
                // Close modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('send-dynamic-report-modal'));
                if (modal) modal.hide();
            } else {
                AdminNotifications.showError('Failed to send test dynamic report email');
            }
        } catch (error) {
            AdminNotifications.handleApiError(error, 'Error sending test dynamic report email');
        }
    },

    // Handle modal save schedule action
    async handleModalSaveSchedule() {
        const templateId = document.getElementById('modal-unified-template-id').value;
        const recipientsText = document.getElementById('modal-unified-schedule-recipients').value;
        const enabled = document.getElementById('modal-unified-schedule-enabled').checked;
        const frequency = document.getElementById('modal-unified-schedule-frequency').value;
        const hour = parseInt(document.getElementById('modal-unified-schedule-hour').value);
        const timezone = document.getElementById('modal-unified-schedule-timezone').value;

        if (!templateId) {
            AdminNotifications.showError('Please select a template');
            return;
        }

        if (!recipientsText) {
            AdminNotifications.showError('Please enter recipient email addresses');
            return;
        }

        const recipients = recipientsText.split(',').map(email => email.trim()).filter(email => email);
        if (recipients.length === 0) {
            AdminNotifications.showError('Please enter valid recipient email addresses');
            return;
        }

        try {
            const settings = {
                dynamic_reports_enabled: enabled,
                dynamic_report_recipients: recipients,
                dynamic_report_schedule_hour: hour,
                dynamic_report_frequency: frequency,
                dynamic_report_template_id: parseInt(templateId),
                timezone: timezone
            };

            const response = await AdminAPI.dynamicReports.updateScheduleSettings(settings);

            if (response.ok) {
                AdminNotifications.showSuccess('Schedule settings saved successfully');
                this.updateUnifiedStatus();
                // Close modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('send-dynamic-report-modal'));
                if (modal) modal.hide();
            } else {
                AdminNotifications.showError('Failed to save schedule settings');
            }
        } catch (error) {
            AdminNotifications.handleApiError(error, 'Error saving schedule settings');
        }
    },

    // Setup modal listeners
    setupModalListeners() {
        // Modal sending method radio buttons
        const modalMethodRadios = document.querySelectorAll('input[name="modal-sending-method"]');
        modalMethodRadios.forEach(radio => {
            if (!radio.hasAttribute('data-modal-listener')) {
                radio.addEventListener('change', this.handleModalSendingMethodChange.bind(this));
                radio.setAttribute('data-modal-listener', 'true');
            }
        });

        // Modal show event to load templates
        const modal = document.getElementById('send-dynamic-report-modal');
        if (modal && !modal.hasAttribute('data-modal-listener')) {
            modal.addEventListener('show.bs.modal', this.onModalShow.bind(this));
            modal.setAttribute('data-modal-listener', 'true');
        }
    },

    // Handle modal sending method change
    handleModalSendingMethodChange(event) {
        const method = event.target.value;
        
        // Hide all recipient sections first
        document.getElementById('modal-send-now-recipients').style.display = 'none';
        document.getElementById('modal-test-email-recipient').style.display = 'none';
        document.getElementById('modal-schedule-recipients').style.display = 'none';
        document.getElementById('modal-report-settings-section').style.display = 'none';
        document.getElementById('modal-schedule-settings-section').style.display = 'none';

        // Update action button text
        const actionBtn = document.getElementById('modal-unified-action-btn');
        
        if (method === 'send_now') {
            document.getElementById('modal-send-now-recipients').style.display = 'block';
            document.getElementById('modal-report-settings-section').style.display = 'block';
            actionBtn.innerHTML = '📧 Send Now';
        } else if (method === 'test') {
            document.getElementById('modal-test-email-recipient').style.display = 'block';
            document.getElementById('modal-report-settings-section').style.display = 'block';
            actionBtn.innerHTML = '🧪 Send Test';
        } else if (method === 'schedule') {
            document.getElementById('modal-schedule-recipients').style.display = 'block';
            document.getElementById('modal-schedule-settings-section').style.display = 'block';
            actionBtn.innerHTML = '⏰ Save Schedule';
        }
    },

    // Handle modal show event
    async onModalShow() {
        // Load templates for modal dropdown
        await this.loadTemplatesForModalDropdown();
        
        // Set initial form state
        this.handleModalSendingMethodChange({ target: { value: 'send_now' } });
    },

    // Load templates for modal dropdown
    async loadTemplatesForModalDropdown() {
        try {
            const response = await AdminAPI.dynamicReports.getTemplates();

            if (response.ok) {
                const templates = await response.json();
                const dropdown = document.getElementById('modal-unified-template-id');
                
                if (dropdown) {
                    // Clear existing options except the first one
                    while (dropdown.children.length > 1) {
                        dropdown.removeChild(dropdown.lastChild);
                    }

                    // Add template options
                    templates.forEach(template => {
                        const option = document.createElement('option');
                        option.value = template.id;
                        option.textContent = template.name;
                        dropdown.appendChild(option);
                    });
                }
            }
        } catch (error) {
            console.warn('Error loading templates for modal dropdown:', error);
        }
    },

    // Show send email modal
    showSendEmailModal() {
        const modal = new bootstrap.Modal(document.getElementById('send-dynamic-report-modal'));
        modal.show();
    },

    // Load scheduled reports
    async loadScheduledReports() {
        AdminLogs.log('INFO', '🔄 Loading scheduled reports...');
        try {
            const response = await AdminAPI.dynamicReports.getSchedules();
            AdminLogs.log('DEBUG', '📡 API Response:', { ok: response.ok, status: response.status });
            
            if (response.ok) {
                const schedules = await response.json();
                AdminLogs.log('DEBUG', '📊 Received schedules:', schedules);
                AdminLogs.log('DEBUG', `📈 Total schedules: ${schedules.length}`);
                
                this.renderScheduledReports(schedules);
                AdminLogs.log('INFO', '✅ Schedules rendered successfully');
            } else {
                AdminLogs.log('ERROR', '❌ Failed to load scheduled reports:', response.status, response.statusText);
                AdminNotifications.showError('Failed to load scheduled reports');
            }
        } catch (error) {
            AdminLogs.log('ERROR', '❌ Error loading scheduled reports:', error);
            AdminNotifications.handleApiError(error, 'Error loading scheduled reports');
        }
    },

    // Manual trigger to force load scheduled reports (for debugging)
    async forceLoadScheduledReports() {
        AdminLogs.log('DEBUG', '🔧 Force loading scheduled reports...');
        await this.loadScheduledReports();
    },

    // Render scheduled reports list
    renderScheduledReports(schedules) {
        AdminLogs.log('DEBUG', '🎨 Rendering scheduled reports...', schedules);
        
        // Try multiple possible container IDs
        const possibleContainerIds = [
            'scheduled-reports-list',
            'scheduled-reports-container',
            'dynamic-reports-scheduled-list',
            'dynamic-scheduled-reports-list'
        ];
        
        let container = null;
        for (const containerId of possibleContainerIds) {
            container = document.getElementById(containerId);
            if (container) {
                AdminLogs.log('DEBUG', `✅ Found container: ${containerId}`);
                break;
            }
        }
        
        if (!container) {
            AdminLogs.log('ERROR', '❌ No suitable container found for scheduled reports');
            AdminLogs.log('DEBUG', '🔍 Available elements with "scheduled" in ID:');
            const allElements = document.querySelectorAll('*');
            allElements.forEach(el => {
                if (el.id && el.id.toLowerCase().includes('scheduled')) {
                    AdminLogs.log('DEBUG', `  - ${el.id}`);
                }
            });
            return;
        }

        if (schedules.length === 0) {
            AdminLogs.log('DEBUG', '📭 No schedules to display, showing empty state');
            container.innerHTML = `
                <div class="text-center text-muted py-4">
                    <h6>📅 No Scheduled Reports</h6>
                    <p>Create your first scheduled report to automate report delivery.</p>
                    <button class="btn btn-success" onclick="AdminDynamicReports.showCreateScheduleModal()">
                        ➕ Create Schedule
                    </button>
                </div>
            `;
            return;
        }

        AdminLogs.log('DEBUG', `📝 Rendering ${schedules.length} scheduled reports`);
        const htmlContent = schedules.map(schedule => `
            <div class="card mb-3">
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-start">
                        <div class="flex-grow-1">
                            <div class="d-flex align-items-center mb-2">
                                <h6 class="mb-0 me-2">${schedule.name}</h6>
                                <span class="badge ${schedule.is_enabled ? 'bg-success' : 'bg-secondary'}">
                                    ${schedule.is_enabled ? '▶️ Active' : '⏸️ Paused'}
                                </span>
                            </div>
                            <p class="text-muted mb-2">${schedule.description || 'No description'}</p>
                            <div class="row text-sm">
                                <div class="col-md-3">
                                    <strong>Template:</strong> ${schedule.template ? schedule.template.name : 'Unknown'}
                                </div>
                                <div class="col-md-3">
                                    <strong>Frequency:</strong> ${schedule.frequency}
                                </div>
                                <div class="col-md-3">
                                    <strong>Time:</strong> ${String(schedule.schedule_hour).padStart(2, '0')}:00 ${schedule.timezone}
                                </div>
                                <div class="col-md-3">
                                    <strong>Recipients:</strong> ${Array.isArray(schedule.recipients) ? schedule.recipients.length : 0}
                                </div>
                            </div>
                            ${schedule.last_sent ? `
                                <div class="text-sm text-success mt-1">
                                    <strong>Last sent:</strong> ${new Date(schedule.last_sent).toLocaleString()}
                                </div>
                            ` : ''}
                            ${schedule.last_error ? `
                                <div class="text-sm text-danger mt-1">
                                    <strong>Last error:</strong> ${schedule.last_error}
                                </div>
                            ` : ''}
                        </div>
                        <div class="btn-group btn-group-sm">
                            <button class="btn btn-outline-primary" onclick="AdminDynamicReports.editSchedule(${schedule.id})" title="Edit">
                                ✏️
                            </button>
                            <button class="btn btn-outline-${schedule.is_enabled ? 'secondary' : 'success'}" 
                                    onclick="AdminDynamicReports.toggleSchedule(${schedule.id})" 
                                    title="${schedule.is_enabled ? 'Disable' : 'Enable'}">
                                ${schedule.is_enabled ? '⏸️' : '▶️'}
                            </button>
                            <button class="btn btn-outline-info" onclick="AdminDynamicReports.testSchedule(${schedule.id})" title="Test">
                                🧪
                            </button>
                            <button class="btn btn-outline-danger" onclick="AdminDynamicReports.deleteSchedule(${schedule.id})" title="Delete">
                                🗑️
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `).join('');
        
        container.innerHTML = htmlContent;
        AdminLogs.log('INFO', '✅ Scheduled reports rendered successfully');
    },

    // Debug function to check the current state (call from browser console)
    debugScheduledReports() {
        AdminLogs.log('DEBUG', '🔍 Debugging scheduled reports...');
        
        // Check if container exists
        const container = document.getElementById('scheduled-reports-list');
        AdminLogs.log('DEBUG', '📦 Container found:', !!container);
        if (container) {
            AdminLogs.log('DEBUG', '📦 Container visible:', container.offsetParent !== null);
            AdminLogs.log('DEBUG', '📦 Container content:', container.innerHTML.length > 0 ? 'Has content' : 'Empty');
        }
        
        // Try to load schedules manually
        AdminLogs.log('DEBUG', '🔄 Manually triggering loadScheduledReports...');
        this.loadScheduledReports();
        
        // List all elements with "scheduled" in their ID
        AdminLogs.log('DEBUG', '🔍 All elements with "scheduled" in ID or class:');
        const allElements = document.querySelectorAll('*');
        allElements.forEach(el => {
            if ((el.id && el.id.toLowerCase().includes('scheduled')) || 
                (el.className && el.className.toLowerCase().includes('scheduled'))) {
                AdminLogs.log('DEBUG', `  - ID: ${el.id}, Class: ${el.className}, Visible: ${el.offsetParent !== null}`);
            }
        });
    },

    // Show create schedule modal
    showCreateScheduleModal() {
        // We'll use the existing send report modal but in schedule mode
        const modal = new bootstrap.Modal(document.getElementById('send-dynamic-report-modal'));
        
        // Set the form to schedule mode
        document.getElementById('modal-method-schedule').checked = true;
        this.handleModalSendingMethodChange({ target: { value: 'schedule' } });
        
        // Update modal title
        document.querySelector('#send-dynamic-report-modal .modal-title').textContent = '📅 Create Scheduled Report';
        
        // Update button text
        document.getElementById('modal-unified-action-btn').textContent = '📅 Create Schedule';
        
        modal.show();
    },

    // Toggle schedule
    async toggleSchedule(scheduleId) {
        try {
            const response = await AdminAPI.dynamicReports.toggleSchedule(scheduleId);
            if (response.ok) {
                const result = await response.json();
                AdminNotifications.showSuccess(result.message);
                this.loadScheduledReports();
            } else {
                AdminNotifications.showError('Failed to toggle schedule');
            }
        } catch (error) {
            AdminNotifications.handleApiError(error, 'Error toggling schedule');
        }
    },

    // Delete schedule
    async deleteSchedule(scheduleId) {
        const confirmed = await AdminNotifications.confirm('Are you sure you want to delete this scheduled report?');
        if (!confirmed) return;

        try {
            const response = await AdminAPI.dynamicReports.deleteSchedule(scheduleId);
            if (response.ok) {
                AdminNotifications.showSuccess('Scheduled report deleted successfully');
                this.loadScheduledReports();
            } else {
                AdminNotifications.showError('Failed to delete scheduled report');
            }
        } catch (error) {
            AdminNotifications.handleApiError(error, 'Error deleting scheduled report');
        }
    },

    // Edit schedule
    async editSchedule(scheduleId) {
        // For now, we'll show the create modal with existing data
        // In a full implementation, you'd pre-populate the form
        AdminNotifications.showInfo('Edit functionality coming soon! Please delete and recreate for now.');
    },

    // Test schedule
    async testSchedule(scheduleId) {
        AdminNotifications.showInfo('Test functionality coming soon! This will send a test report using the schedule settings.');
    },

    // Enable all schedules
    async enableAllSchedules() {
        const confirmed = await AdminNotifications.confirm('Enable all scheduled reports?');
        if (!confirmed) return;

        try {
            const response = await AdminAPI.dynamicReports.getSchedules();
            if (response.ok) {
                const schedules = await response.json();
                
                const promises = schedules
                    .filter(s => !s.is_enabled)
                    .map(s => AdminAPI.dynamicReports.toggleSchedule(s.id));
                
                await Promise.all(promises);
                AdminNotifications.showSuccess(`Enabled ${promises.length} scheduled reports`);
                this.loadScheduledReports();
            }
        } catch (error) {
            AdminNotifications.handleApiError(error, 'Error enabling all schedules');
        }
    },

    // Disable all schedules
    async disableAllSchedules() {
        const confirmed = await AdminNotifications.confirm('Disable all scheduled reports?');
        if (!confirmed) return;

        try {
            const response = await AdminAPI.dynamicReports.getSchedules();
            if (response.ok) {
                const schedules = await response.json();
                
                const promises = schedules
                    .filter(s => s.is_enabled)
                    .map(s => AdminAPI.dynamicReports.toggleSchedule(s.id));
                
                await Promise.all(promises);
                AdminNotifications.showSuccess(`Disabled ${promises.length} scheduled reports`);
                this.loadScheduledReports();
            }
        } catch (error) {
            AdminNotifications.handleApiError(error, 'Error disabling all schedules');
        }
    },

    // Test all active schedules
    async testAllSchedules() {
        AdminNotifications.showInfo('Test all functionality coming soon! This will send test reports for all active schedules.');
    },

    // Handle modal unified email action (updated for schedule creation)
    async handleModalUnifiedEmailAction() {
        const method = document.querySelector('input[name="modal-sending-method"]:checked')?.value;
        
        if (method === 'send_now') {
            await this.handleModalSendNow();
        } else if (method === 'test') {
            await this.handleModalSendTest();
        } else if (method === 'schedule') {
            // Check if this is for creating a new schedule vs updating global settings
            const modalTitle = document.querySelector('#send-dynamic-report-modal .modal-title').textContent;
            const actionBtn = document.getElementById('modal-unified-action-btn');
            
            // If modal title contains "Create" or button text contains "Create", it's for individual schedules
            if (modalTitle.includes('Create') || actionBtn.textContent.includes('Create')) {
                await this.handleCreateNewSchedule();
            } else {
                // This is for updating global schedule settings (legacy functionality)
                await this.handleModalSaveSchedule();
            }
        }
    },

    // Handle creating a new schedule
    async handleCreateNewSchedule() {
        const templateId = document.getElementById('modal-unified-template-id').value;
        const recipientsText = document.getElementById('modal-unified-schedule-recipients').value;
        const enabled = document.getElementById('modal-unified-schedule-enabled').checked;
        const frequency = document.getElementById('modal-unified-schedule-frequency').value;
        const hour = parseInt(document.getElementById('modal-unified-schedule-hour').value);
        const timezone = document.getElementById('modal-unified-schedule-timezone').value;

        if (!templateId) {
            AdminNotifications.showError('Please select a template');
            return;
        }

        if (!recipientsText) {
            AdminNotifications.showError('Please enter recipient email addresses');
            return;
        }

        const recipients = recipientsText.split(',').map(email => email.trim()).filter(email => email);
        if (recipients.length === 0) {
            AdminNotifications.showError('Please enter valid recipient email addresses');
            return;
        }

        // Generate a name for the schedule
        const templateResponse = await AdminAPI.dynamicReports.getTemplates();
        const templates = await templateResponse.json();
        const template = templates.find(t => t.id === parseInt(templateId));
        const scheduleName = `${template ? template.name : 'Report'} - ${frequency} at ${String(hour).padStart(2, '0')}:00`;

        try {
            const scheduleData = {
                name: scheduleName,
                description: `Automatically generated ${frequency} report`,
                template_id: parseInt(templateId),
                recipients: recipients,
                frequency: frequency,
                schedule_hour: hour,
                timezone: timezone,
                is_enabled: enabled,
                include_excel: true,
                months_period: 2
            };

            const response = await AdminAPI.dynamicReports.createSchedule(scheduleData);

            if (response.ok) {
                AdminNotifications.showSuccess('Scheduled report created successfully');
                
                // Close modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('send-dynamic-report-modal'));
                if (modal) modal.hide();
                
                // Reload schedules
                this.loadScheduledReports();
                
                // Reset modal title and button
                document.querySelector('#send-dynamic-report-modal .modal-title').textContent = '📧 Send Dynamic Report';
                document.getElementById('modal-unified-action-btn').textContent = '📧 Send Now';
            } else {
                AdminNotifications.showError('Failed to create scheduled report');
            }
        } catch (error) {
            AdminNotifications.handleApiError(error, 'Error creating scheduled report');
        }
    },

    // Ensure initialization when tab becomes active
    ensureInitialized() {
        AdminLogs.log('DEBUG', 'Ensuring dynamic reports module is properly initialized...');
        this.setupEventListeners();
        this.setupModalListeners();
        
        // Check if we're on the email scheduling tab and initialize if needed
        const scheduleTab = document.querySelector('[data-bs-target="#dynamic-reports-email-tab"]');
        if (scheduleTab && scheduleTab.classList.contains('active')) {
            this.initEmailScheduling();
        }

        // Set up scheduled reports tab click handler with multiple possible selectors
        this.setupScheduledReportsTabListener();
        
        // Also try to load schedules immediately if we're already on the scheduled reports tab
        this.tryLoadScheduledReportsIfActive();
    },

    // Setup scheduled reports tab listener with multiple possible selectors
    setupScheduledReportsTabListener() {
        const possibleSelectors = [
            'scheduled-reports-tab',
            'scheduled-reports-tab-btn', 
            'dynamic-reports-scheduled-tab',
            '[data-bs-target="#scheduled-reports-tab"]',
            '[data-bs-target="#dynamic-reports-scheduled-tab"]'
        ];
        
        let tabFound = false;
        
        possibleSelectors.forEach(selector => {
            const tab = selector.startsWith('[') ? 
                document.querySelector(selector) : 
                document.getElementById(selector);
                
            if (tab && !tab.hasAttribute('data-scheduled-listener')) {
                AdminLogs.log('DEBUG', `Found scheduled reports tab with selector: ${selector}`);
                tab.addEventListener('click', () => {
                    AdminLogs.log('DEBUG', 'Scheduled reports tab clicked, loading schedules...');
                    setTimeout(() => this.loadScheduledReports(), 100);
                });
                tab.setAttribute('data-scheduled-listener', 'true');
                tabFound = true;
            }
        });
        
        if (!tabFound) {
            AdminLogs.log('WARNING', 'Scheduled reports tab not found with any of the expected selectors');
            AdminLogs.log('DEBUG', 'Available elements with "scheduled" in id or class:');
            const allElements = document.querySelectorAll('*');
            allElements.forEach(el => {
                if (el.id && el.id.toLowerCase().includes('scheduled')) {
                    AdminLogs.log('DEBUG', `  - ID: ${el.id}`);
                }
                if (el.className && el.className.toLowerCase().includes('scheduled')) {
                    AdminLogs.log('DEBUG', `  - Class: ${el.className}`);
                }
            });
        }
    },

    // Try to load scheduled reports if we're already on the active tab
    tryLoadScheduledReportsIfActive() {
        // Check if any scheduled reports container is visible
        const possibleContainers = [
            'scheduled-reports-list',
            'scheduled-reports-container',
            'dynamic-reports-scheduled-content'
        ];
        
        possibleContainers.forEach(containerId => {
            const container = document.getElementById(containerId);
            if (container && container.offsetParent !== null) {
                AdminLogs.log('DEBUG', `Found visible scheduled reports container: ${containerId}, loading schedules...`);
                setTimeout(() => this.loadScheduledReports(), 100);
            }
        });
    }
};

// Export for global access
window.AdminDynamicReports = AdminDynamicReports;

// Initialize when module loads (but elements might not exist yet)
AdminDynamicReports.init();

AdminLogs.log('INFO', 'Admin dynamic reports module loaded!');
