/**
 * Styling Management Module
 * Handles all branding and styling customization functionality
 */

class AdminStyling {
    constructor() {
        this.currentSettings = null;
        this.previewMode = false;
        this.originalStyleElement = null;
        this.previewStyleElement = null;
        this.init();
    }

    init() {
        this.bindEvents();
        this.loadStylingSettings();
    }

    bindEvents() {
        // Main action buttons
        document.getElementById('refresh-styling-btn')?.addEventListener('click', () => this.loadStylingSettings());
        document.getElementById('reset-styling-btn')?.addEventListener('click', () => this.resetToDefaults());
        document.getElementById('save-styling-btn')?.addEventListener('click', () => this.saveStyling());
        document.getElementById('preview-styling-btn')?.addEventListener('click', () => this.previewChanges());

        // Logo functionality
        document.getElementById('upload-logo-btn')?.addEventListener('click', () => this.uploadLogo());
        document.getElementById('remove-logo-btn')?.addEventListener('click', () => this.removeLogo());
        document.getElementById('logo-upload')?.addEventListener('change', (e) => this.handleLogoFileSelect(e));

        // Color pickers - bind change events for live preview
        const colorInputs = [
            'primary-color', 'secondary-color', 'success-color', 'danger-color',
            'warning-color', 'info-color', 'body-bg-color', 'text-color',
            'link-color', 'link-hover-color', 'navbar-bg-color', 'navbar-text-color'
        ];
        
        colorInputs.forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                element.addEventListener('change', () => this.updateTypographyPreview());
            }
        });

        // Typography changes
        document.getElementById('font-family')?.addEventListener('change', () => this.updateTypographyPreview());
        document.getElementById('heading-font-family')?.addEventListener('change', () => this.updateTypographyPreview());
        document.getElementById('navbar-brand-text-input')?.addEventListener('input', () => this.updateNavbarPreview());

        // Logo settings
        document.getElementById('logo-max-height')?.addEventListener('input', () => this.updateLogoPreview());
        document.getElementById('login-logo-max-height')?.addEventListener('input', () => this.updateLogoPreview());
        document.getElementById('logo-alt-text')?.addEventListener('input', () => this.updateLogoPreview());
    }

    async loadStylingSettings() {
        try {
            const response = await window.AdminAPI.makeRequest('/api/admin/styling-settings/');

            if (!response.ok) {
                throw new Error('Failed to load styling settings');
            }

            this.currentSettings = await response.json();
            this.populateForm();

        } catch (error) {
            console.error('Error loading styling settings:', error);
            if (window.AdminNotifications) {
                AdminNotifications.showError('Failed to load styling settings');
            }
        }
    }

    populateForm() {
        if (!this.currentSettings) return;

        const settings = this.currentSettings;

        // Enable/disable toggle
        document.getElementById('styling-enabled').checked = settings.enabled;

        // Logo settings
        document.getElementById('logo-alt-text').value = settings.logo_alt_text || 'Company Logo';
        document.getElementById('logo-max-height').value = settings.logo_max_height || 50;
        document.getElementById('login-logo-max-height').value = settings.login_logo_max_height || 100;
        document.getElementById('show-logo-navbar').checked = settings.show_logo_in_navbar;
        document.getElementById('show-logo-login').checked = settings.show_logo_on_login;

        // Update logo preview
        this.updateLogoDisplay();

        // Color settings
        document.getElementById('primary-color').value = settings.primary_color;
        document.getElementById('secondary-color').value = settings.secondary_color;
        document.getElementById('success-color').value = settings.success_color;
        document.getElementById('danger-color').value = settings.danger_color;
        document.getElementById('warning-color').value = settings.warning_color;
        document.getElementById('info-color').value = settings.info_color;
        document.getElementById('body-bg-color').value = settings.body_bg_color;
        document.getElementById('text-color').value = settings.text_color;
        document.getElementById('link-color').value = settings.link_color;
        document.getElementById('link-hover-color').value = settings.link_hover_color;
        document.getElementById('navbar-bg-color').value = settings.navbar_bg_color;
        document.getElementById('navbar-text-color').value = settings.navbar_text_color;

        // Typography settings
        document.getElementById('font-family').value = settings.font_family || 'system-ui';
        document.getElementById('heading-font-family').value = settings.heading_font_family || '';
        document.getElementById('navbar-brand-text-input').value = settings.navbar_brand_text || 'Parking Booking';

        // Custom CSS
        document.getElementById('custom-css').value = settings.custom_css || '';

        // Update previews
        this.updateTypographyPreview();
        this.updateNavbarPreview();
    }

    updateLogoDisplay() {
        const logoPreview = document.getElementById('logo-preview');
        const noLogoMessage = document.getElementById('no-logo-message');
        const removeBtn = document.getElementById('remove-logo-btn');

        if (this.currentSettings?.logo_path) {
            logoPreview.src = this.currentSettings.logo_path;
            logoPreview.style.display = 'block';
            noLogoMessage.style.display = 'none';
            removeBtn.style.display = 'inline-block';
        } else {
            logoPreview.style.display = 'none';
            noLogoMessage.style.display = 'block';
            removeBtn.style.display = 'none';
        }
    }

    updateLogoPreview() {
        const logoPreview = document.getElementById('logo-preview');
        const maxHeight = document.getElementById('logo-max-height').value;
        const altText = document.getElementById('logo-alt-text').value;

        if (logoPreview && logoPreview.style.display !== 'none') {
            logoPreview.style.maxHeight = `${maxHeight}px`;
            logoPreview.alt = altText;
        }
    }

    updateTypographyPreview() {
        const preview = document.getElementById('typography-preview');
        if (!preview) return;

        const fontFamily = document.getElementById('font-family').value;
        const headingFontFamily = document.getElementById('heading-font-family').value;
        const textColor = document.getElementById('text-color').value;
        const linkColor = document.getElementById('link-color').value;

        // Apply font family
        preview.style.fontFamily = fontFamily;

        // Apply heading font family
        const headings = preview.querySelectorAll('h1, h2, h3, h4, h5, h6');
        headings.forEach(heading => {
            heading.style.fontFamily = headingFontFamily || fontFamily;
        });

        // Apply text color
        preview.style.color = textColor;

        // Apply link color
        const links = preview.querySelectorAll('a');
        links.forEach(link => {
            link.style.color = linkColor;
        });
    }

    updateNavbarPreview() {
        const brandText = document.getElementById('navbar-brand-text-input').value;
        const navbarBrandElement = document.getElementById('navbar-brand-text');
        
        // Update the actual navbar if styling is enabled
        if (this.currentSettings?.enabled) {
            const navbarBrandTextSpan = document.getElementById('navbar-brand-text');
            if (navbarBrandTextSpan) {
                navbarBrandTextSpan.textContent = brandText;
            }
        }
    }

    handleLogoFileSelect(event) {
        const file = event.target.files[0];
        if (!file) return;

        // Validate file type
        const allowedTypes = ['image/png', 'image/jpeg', 'image/jpg', 'image/svg+xml', 'image/gif'];
        if (!allowedTypes.includes(file.type)) {
            if (window.AdminNotifications) {
                AdminNotifications.showError('Invalid file type. Please select PNG, JPG, SVG, or GIF.');
            }
            return;
        }

        // Validate file size (5MB)
        if (file.size > 5 * 1024 * 1024) {
            if (window.AdminNotifications) {
                AdminNotifications.showError('File too large. Maximum size is 5MB.');
            }
            return;
        }

        // Show preview
        const reader = new FileReader();
        reader.onload = (e) => {
            const logoPreview = document.getElementById('logo-preview');
            const noLogoMessage = document.getElementById('no-logo-message');
            
            logoPreview.src = e.target.result;
            logoPreview.style.display = 'block';
            noLogoMessage.style.display = 'none';
            
            this.updateLogoPreview();
        };
        reader.readAsDataURL(file);
    }

    async uploadLogo() {
        const fileInput = document.getElementById('logo-upload');
        const file = fileInput.files[0];

        if (!file) {
            if (window.AdminNotifications) {
                AdminNotifications.showError('Please select a file first');
            }
            return;
        }

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await window.AdminAPI.makeRequest('/api/admin/styling-settings/upload-logo', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to upload logo');
            }

            const result = await response.json();
            
            // Update current settings
            if (this.currentSettings) {
                this.currentSettings.logo_path = result.logo_path;
            }

            this.updateLogoDisplay();
            if (window.AdminNotifications) {
                AdminNotifications.showSuccess('Logo uploaded successfully');
            }

            // Clear file input
            fileInput.value = '';

        } catch (error) {
            console.error('Error uploading logo:', error);
            if (window.AdminNotifications) {
                AdminNotifications.showError(error.message);
            }
        }
    }

    async removeLogo() {
        if (!confirm('Are you sure you want to remove the current logo?')) {
            return;
        }

        try {
            const response = await window.AdminAPI.makeRequest('/api/admin/styling-settings/logo', {
                method: 'DELETE'
            });

            if (!response.ok) {
                throw new Error('Failed to remove logo');
            }

            // Update current settings
            if (this.currentSettings) {
                this.currentSettings.logo_path = null;
            }

            this.updateLogoDisplay();
            if (window.AdminNotifications) {
                AdminNotifications.showSuccess('Logo removed successfully');
            }

        } catch (error) {
            console.error('Error removing logo:', error);
            if (window.AdminNotifications) {
                AdminNotifications.showError('Failed to remove logo');
            }
        }
    }

    previewChanges() {
        if (this.previewMode) {
            this.exitPreview();
        } else {
            this.enterPreview();
        }
    }

    enterPreview() {
        // Get current form values
        const settings = this.getFormValues();
        
        // Generate preview CSS
        const previewCSS = this.generateCSS(settings);
        
        // Create preview style element
        this.previewStyleElement = document.createElement('style');
        this.previewStyleElement.id = 'styling-preview';
        this.previewStyleElement.textContent = previewCSS;
        document.head.appendChild(this.previewStyleElement);

        // Update UI elements
        this.updateUIElements(settings);

        this.previewMode = true;
        const previewBtn = document.getElementById('preview-styling-btn');
        previewBtn.textContent = '❌ Exit Preview';
        previewBtn.className = 'btn btn-warning';

        if (window.AdminNotifications) {
            AdminNotifications.showInfo('Preview mode enabled. Changes are temporary.');
        }
    }

    exitPreview() {
        // Remove preview styles
        if (this.previewStyleElement) {
            this.previewStyleElement.remove();
            this.previewStyleElement = null;
        }

        // Restore original UI elements
        this.restoreUIElements();

        this.previewMode = false;
        const previewBtn = document.getElementById('preview-styling-btn');
        previewBtn.textContent = '👁️ Preview Changes';
        previewBtn.className = 'btn btn-secondary';

        if (window.AdminNotifications) {
            AdminNotifications.showInfo('Preview mode disabled');
        }
    }

    updateUIElements(settings) {
        // Update navbar brand text
        const navbarBrandText = document.getElementById('navbar-brand-text');
        if (navbarBrandText) {
            navbarBrandText.textContent = settings.navbar_brand_text;
        }

        // Update login title
        const loginTitle = document.getElementById('login-title');
        if (loginTitle) {
            loginTitle.textContent = settings.navbar_brand_text;
        }

        // Update logo visibility and properties
        this.updateLogoElements(settings);
    }

    updateLogoElements(settings) {
        const navbarLogo = document.getElementById('navbar-logo');
        const loginLogo = document.getElementById('login-logo');

        if (settings.logo_path) {
            // Update navbar logo
            if (navbarLogo && settings.show_logo_in_navbar) {
                navbarLogo.src = settings.logo_path;
                navbarLogo.alt = settings.logo_alt_text;
                navbarLogo.style.display = 'inline-block';
                navbarLogo.style.maxHeight = `${settings.logo_max_height}px`;
            } else if (navbarLogo) {
                navbarLogo.style.display = 'none';
            }

            // Update login logo
            if (loginLogo && settings.show_logo_on_login) {
                loginLogo.src = settings.logo_path;
                loginLogo.alt = settings.logo_alt_text;
                loginLogo.style.display = 'block';
                loginLogo.style.maxHeight = `${settings.login_logo_max_height}px`;
            } else if (loginLogo) {
                loginLogo.style.display = 'none';
            }
        } else {
            // Hide logos if no logo path
            if (navbarLogo) navbarLogo.style.display = 'none';
            if (loginLogo) loginLogo.style.display = 'none';
        }
    }

    restoreUIElements() {
        if (!this.currentSettings) return;

        // Restore navbar brand text
        const navbarBrandText = document.getElementById('navbar-brand-text');
        if (navbarBrandText) {
            navbarBrandText.textContent = this.currentSettings.navbar_brand_text || 'Parking Booking';
        }

        // Restore login title
        const loginTitle = document.getElementById('login-title');
        if (loginTitle) {
            loginTitle.textContent = this.currentSettings.navbar_brand_text || 'Parking Booking';
        }

        // Restore logo elements
        this.updateLogoElements(this.currentSettings);
    }

    generateCSS(settings) {
        if (!settings.enabled) {
            return '/* Custom styling disabled */';
        }

        return `
/* Preview styling */
:root {
    --bs-primary: ${settings.primary_color};
    --bs-secondary: ${settings.secondary_color};
    --bs-success: ${settings.success_color};
    --bs-danger: ${settings.danger_color};
    --bs-warning: ${settings.warning_color};
    --bs-info: ${settings.info_color};
    
    --bs-body-bg: ${settings.body_bg_color};
    --bs-body-color: ${settings.text_color};
    --bs-link-color: ${settings.link_color};
    --bs-link-hover-color: ${settings.link_hover_color};
    
    --custom-font-family: ${settings.font_family};
    --custom-heading-font-family: ${settings.heading_font_family || settings.font_family};
    
    --navbar-bg-color: ${settings.navbar_bg_color};
    --navbar-text-color: ${settings.navbar_text_color};
}

body {
    font-family: var(--custom-font-family), -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
    background-color: var(--bs-body-bg) !important;
    color: var(--bs-body-color) !important;
}

h1, h2, h3, h4, h5, h6 {
    font-family: var(--custom-heading-font-family), -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
}

.navbar {
    background-color: var(--navbar-bg-color) !important;
}

.navbar .navbar-brand,
.navbar .nav-link,
.navbar .navbar-text {
    color: var(--navbar-text-color) !important;
}

.btn-primary {
    background-color: var(--bs-primary) !important;
    border-color: var(--bs-primary) !important;
}

.btn-secondary {
    background-color: var(--bs-secondary) !important;
    border-color: var(--bs-secondary) !important;
}

.btn-success {
    background-color: var(--bs-success) !important;
    border-color: var(--bs-success) !important;
}

.btn-danger {
    background-color: var(--bs-danger) !important;
    border-color: var(--bs-danger) !important;
}

.btn-warning {
    background-color: var(--bs-warning) !important;
    border-color: var(--bs-warning) !important;
}

.btn-info {
    background-color: var(--bs-info) !important;
    border-color: var(--bs-info) !important;
}

/* Logo styling */
.navbar-brand img {
    max-height: ${settings.logo_max_height}px;
    height: auto;
    width: auto;
}

.login-logo {
    max-height: ${settings.login_logo_max_height}px;
    height: auto;
    width: auto;
    margin-bottom: 1rem;
}

${settings.login_bg_color ? `
#login-form-container {
    background-color: ${settings.login_bg_color} !important;
}
` : ''}

${settings.login_card_bg_color ? `
#login-form {
    background-color: ${settings.login_card_bg_color} !important;
    padding: 2rem;
    border-radius: 0.5rem;
    box-shadow: 0 0.5rem 1rem rgba(0, 0, 0, 0.1);
}
` : ''}

/* Custom CSS */
${settings.custom_css || ''}
`;
    }

    getFormValues() {
        return {
            enabled: document.getElementById('styling-enabled').checked,
            logo_path: this.currentSettings?.logo_path || null,
            logo_alt_text: document.getElementById('logo-alt-text').value,
            logo_max_height: parseInt(document.getElementById('logo-max-height').value),
            login_logo_max_height: parseInt(document.getElementById('login-logo-max-height').value),
            show_logo_in_navbar: document.getElementById('show-logo-navbar').checked,
            show_logo_on_login: document.getElementById('show-logo-login').checked,
            primary_color: document.getElementById('primary-color').value,
            secondary_color: document.getElementById('secondary-color').value,
            success_color: document.getElementById('success-color').value,
            danger_color: document.getElementById('danger-color').value,
            warning_color: document.getElementById('warning-color').value,
            info_color: document.getElementById('info-color').value,
            body_bg_color: document.getElementById('body-bg-color').value,
            text_color: document.getElementById('text-color').value,
            link_color: document.getElementById('link-color').value,
            link_hover_color: document.getElementById('link-hover-color').value,
            font_family: document.getElementById('font-family').value,
            heading_font_family: document.getElementById('heading-font-family').value,
            navbar_bg_color: document.getElementById('navbar-bg-color').value,
            navbar_text_color: document.getElementById('navbar-text-color').value,
            navbar_brand_text: document.getElementById('navbar-brand-text-input').value,
            custom_css: document.getElementById('custom-css').value
        };
    }

    async saveStyling() {
        try {
            // Exit preview mode if active
            if (this.previewMode) {
                this.exitPreview();
            }

            const settings = this.getFormValues();

            const response = await window.AdminAPI.makeRequest('/api/admin/styling-settings/', {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(settings)
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to save styling settings');
            }

            this.currentSettings = await response.json();
            
            // Immediately apply UI changes (especially brand text)
            this.applyImmediateUIChanges(settings);
            
            // Also reload styling settings globally for all components
            if (window.auth && typeof window.auth.setupUI === 'function') {
                // Call loadStylingSettings from auth module to update all UI elements
                if (window.loadStylingSettings) {
                    window.loadStylingSettings();
                } else if (window.auth.loadStylingSettings) {
                    window.auth.loadStylingSettings();
                }
            }
            
            if (window.AdminNotifications) {
                AdminNotifications.showSuccess('Styling settings saved successfully!');
            }
            
            // Optional page refresh for complete styling reload
            setTimeout(() => {
                if (confirm('Styling settings saved! Would you like to refresh the page to see all changes?')) {
                    window.location.reload();
                }
            }, 1000);

        } catch (error) {
            console.error('Error saving styling settings:', error);
            if (window.AdminNotifications) {
                AdminNotifications.showError(error.message);
            }
        }
    }

    applyImmediateUIChanges(settings) {
        // Immediately update navbar brand text
        const navbarBrandText = document.getElementById('navbar-brand-text');
        if (navbarBrandText && settings.navbar_brand_text) {
            navbarBrandText.textContent = settings.navbar_brand_text;
        }

        // Update login title if visible
        const loginTitle = document.getElementById('login-title');
        if (loginTitle && settings.navbar_brand_text) {
            loginTitle.textContent = settings.navbar_brand_text;
        }

        // Update logo elements if settings are enabled
        if (settings.enabled) {
            this.updateLogoElements(settings);
        }

        // Trigger auth module's loadStylingSettings to update globally
        if (typeof loadStylingSettings === 'function') {
            loadStylingSettings();
        }
    }

    async resetToDefaults() {
        if (!confirm('Are you sure you want to reset all styling to Bootstrap defaults? This will remove your logo and custom settings.')) {
            return;
        }

        try {
            const response = await window.AdminAPI.makeRequest('/api/admin/styling-settings/reset-to-defaults', {
                method: 'POST'
            });

            if (!response.ok) {
                throw new Error('Failed to reset styling settings');
            }

            // Reload settings and refresh page
            await this.loadStylingSettings();
            if (window.AdminNotifications) {
                AdminNotifications.showSuccess('Styling reset to defaults. Page will refresh.');
            }
            
            setTimeout(() => {
                window.location.reload();
            }, 1500);

        } catch (error) {
            console.error('Error resetting styling:', error);
            if (window.AdminNotifications) {
                AdminNotifications.showError('Failed to reset styling settings');
            }
        }
    }
}

// Create and export an instance to window for admin main to use
window.AdminStyling = new AdminStyling();

// Also expose the class constructor for potential future use
window.AdminStyling.constructor = AdminStyling;
