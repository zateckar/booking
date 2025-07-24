/* OIDC Providers Module - OIDC provider management functionality */

const AdminOIDC = {
    // Load all OIDC providers
    async loadOIDCProviders() {
        const tbody = document.getElementById('oidc-providers-table-body');
        if (!tbody) return;
        
        tbody.innerHTML = '<tr><td colspan="6" class="text-center">Loading...</td></tr>';
        
        try {
            const response = await AdminAPI.oidc.getAll();

            if (response.ok) {
                const providers = await response.json();
                tbody.innerHTML = '';
                providers.forEach(provider => {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td>${provider.id}</td>
                        <td>${provider.issuer}</td>
                        <td>${provider.client_id}</td>
                        <td>${provider.scopes}</td>
                        <td>
                            <button class="btn btn-primary btn-sm me-2" onclick="AdminOIDC.editOIDCProvider(${provider.id})">Edit</button>
                            <button class="btn btn-danger btn-sm" onclick="AdminOIDC.deleteOIDCProvider(${provider.id})">Delete</button>
                        </td>
                    `;
                    tbody.appendChild(row);
                });
            } else {
                tbody.innerHTML = '<tr><td colspan="6" class="text-center text-danger">Failed to load OIDC providers</td></tr>';
            }
        } catch (error) {
            tbody.innerHTML = '<tr><td colspan="6" class="text-center text-danger">Error loading OIDC providers</td></tr>';
            AdminNotifications.handleApiError(error, 'Failed to load OIDC providers');
        }
    },

    // Delete OIDC provider
    async deleteOIDCProvider(providerId) {
        const confirmed = await AdminNotifications.confirm('Are you sure you want to delete this OIDC provider?');
        if (!confirmed) return;
        
        try {
            const response = await AdminAPI.oidc.delete(providerId);

            if (response.ok) {
                AdminNotifications.showSuccess('OIDC provider deleted successfully');
                this.loadOIDCProviders();
            } else {
                AdminNotifications.showError('Failed to delete OIDC provider');
            }
        } catch (error) {
            AdminNotifications.handleApiError(error, 'Error deleting OIDC provider');
        }
    },

    // Handle add OIDC form submission
    async handleAddOidcSubmit(event) {
        event.preventDefault();
        
        try {
            const providerData = {
                display_name: document.getElementById('new-oidc-display-name').value,
                issuer: document.getElementById('new-oidc-issuer').value,
                client_id: document.getElementById('new-oidc-client-id').value,
                client_secret: document.getElementById('new-oidc-client-secret').value,
                well_known_url: document.getElementById('new-oidc-well-known').value,
                scopes: document.getElementById('new-oidc-scopes').value
            };

            const response = await AdminAPI.oidc.create(providerData);

            if (response.ok) {
                AdminNotifications.showSuccess('OIDC provider created successfully');
                this.hideAddOIDCModal();
                this.loadOIDCProviders();
            } else {
                const error = await response.json();
                AdminNotifications.showError(error.detail || 'Failed to create OIDC provider');
            }
        } catch (error) {
            AdminNotifications.handleApiError(error, 'Error creating OIDC provider');
        }
    },

    // Edit OIDC provider
    async editOIDCProvider(providerId) {
        try {
            const response = await AdminAPI.oidc.get(providerId);

            if (response.ok) {
                const provider = await response.json();
                
                // Populate the edit form with current data
                document.getElementById('edit-oidc-id').value = provider.id;
                document.getElementById('edit-oidc-display-name').value = provider.display_name || '';
                document.getElementById('edit-oidc-issuer').value = provider.issuer;
                document.getElementById('edit-oidc-client-id').value = provider.client_id;
                document.getElementById('edit-oidc-client-secret').value = ''; // Leave blank for security
                document.getElementById('edit-oidc-well-known').value = provider.well_known_url;
                document.getElementById('edit-oidc-scopes').value = provider.scopes;
                
                // Show the edit modal
                this.showEditOIDCModal();
            } else {
                AdminNotifications.showError('Failed to load OIDC provider data');
            }
        } catch (error) {
            AdminNotifications.handleApiError(error, 'Error loading OIDC provider data');
        }
    },

    // Handle edit OIDC form submission
    async handleEditOidcSubmit(event) {
        event.preventDefault();
        
        try {
            const providerId = document.getElementById('edit-oidc-id').value;
            const clientSecret = document.getElementById('edit-oidc-client-secret').value;
            
            const providerData = {
                display_name: document.getElementById('edit-oidc-display-name').value,
                issuer: document.getElementById('edit-oidc-issuer').value,
                client_id: document.getElementById('edit-oidc-client-id').value,
                well_known_url: document.getElementById('edit-oidc-well-known').value,
                scopes: document.getElementById('edit-oidc-scopes').value
            };

            // Only include client_secret if it's not empty
            if (clientSecret.trim()) {
                providerData.client_secret = clientSecret;
            }

            const response = await AdminAPI.oidc.update(providerId, providerData);

            if (response.ok) {
                AdminNotifications.showSuccess('OIDC provider updated successfully');
                this.hideEditOIDCModal();
                this.loadOIDCProviders();
            } else {
                const error = await response.json();
                AdminNotifications.showError(error.detail || 'Failed to update OIDC provider');
            }
        } catch (error) {
            AdminNotifications.handleApiError(error, 'Error updating OIDC provider');
        }
    },

    // Show add OIDC modal
    showAddOIDCModal() {
        const modal = new bootstrap.Modal(document.getElementById('add-oidc-modal'));
        document.getElementById('add-oidc-form').reset();
        modal.show();
    },

    // Hide add OIDC modal
    hideAddOIDCModal() {
        const modalElement = document.getElementById('add-oidc-modal');
        const modal = bootstrap.Modal.getInstance(modalElement);
        if (modal) {
            modal.hide();
        }
    },

    // Show edit OIDC modal
    showEditOIDCModal() {
        const modal = new bootstrap.Modal(document.getElementById('edit-oidc-modal'));
        modal.show();
    },

    // Hide edit OIDC modal
    hideEditOIDCModal() {
        const modalElement = document.getElementById('edit-oidc-modal');
        const modal = bootstrap.Modal.getInstance(modalElement);
        if (modal) {
            modal.hide();
        }
    },

    // Initialize OIDC module
    init() {
        console.log('Initializing OIDC providers module...');
        
        // Setup form event listeners with retry mechanism
        this.setupEventListeners();
        
        console.log('OIDC providers module initialized');
    },

    // Setup event listeners with proper error handling
    setupEventListeners() {
        // Setup form event listeners
        const addOidcForm = document.getElementById('add-oidc-form');
        if (addOidcForm && !addOidcForm.hasAttribute('data-oidc-listener')) {
            addOidcForm.addEventListener('submit', this.handleAddOidcSubmit.bind(this));
            addOidcForm.setAttribute('data-oidc-listener', 'true');
            console.log('Add OIDC form listener attached');
        }

        const editOidcForm = document.getElementById('edit-oidc-form');
        if (editOidcForm && !editOidcForm.hasAttribute('data-oidc-listener')) {
            editOidcForm.addEventListener('submit', this.handleEditOidcSubmit.bind(this));
            editOidcForm.setAttribute('data-oidc-listener', 'true');
            console.log('Edit OIDC form listener attached');
        }

        const addOidcBtn = document.getElementById('add-oidc-provider-btn');
        if (addOidcBtn && !addOidcBtn.hasAttribute('data-oidc-listener')) {
            addOidcBtn.addEventListener('click', this.showAddOIDCModal.bind(this));
            addOidcBtn.setAttribute('data-oidc-listener', 'true');
            console.log('Add OIDC provider button listener attached');
        }

        const refreshOidcBtn = document.getElementById('refresh-oidc-providers-btn');
        if (refreshOidcBtn && !refreshOidcBtn.hasAttribute('data-oidc-listener')) {
            refreshOidcBtn.addEventListener('click', this.loadOIDCProviders.bind(this));
            refreshOidcBtn.setAttribute('data-oidc-listener', 'true');
            console.log('Refresh OIDC providers button listener attached');
        }

        // If elements aren't found, they might not be rendered yet
        if (!addOidcForm || !editOidcForm || !addOidcBtn || !refreshOidcBtn) {
            console.log('Some OIDC elements not found yet, will retry when tab is activated');
        }
    },

    // Ensure initialization when tab becomes active
    ensureInitialized() {
        console.log('Ensuring OIDC providers module is properly initialized...');
        this.setupEventListeners();
    }
};

// Export for global access
window.AdminOIDC = AdminOIDC;

// Initialize when module loads (but elements might not exist yet)
AdminOIDC.init();

console.log('Admin OIDC providers module loaded!');
