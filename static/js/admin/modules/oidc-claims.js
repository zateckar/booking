/* Unified OIDC & Claims Module - Combined OIDC provider and claims mapping management */

const AdminOIDCClaims = {
    currentProvider: null,
    currentMapping: null,

    // Initialize the unified module
    init() {
        console.log('Initializing unified OIDC & Claims module...');
        this.setupEventListeners();
        this.setupModalEventListeners();
        this.startBackdropCleanupMonitor();
        console.log('Unified OIDC & Claims module initialized');
    },

    // Setup event listeners for the unified interface
    setupEventListeners() {
        // Listen for events from the web components
        document.addEventListener('add-provider', (e) => this.showAddProviderModal());
        document.addEventListener('edit-provider', (e) => this.editProvider(e.detail.providerId));
        document.addEventListener('add-mapping', (e) => this.showAddMappingModal());
        document.addEventListener('edit-mapping', (e) => this.editMapping(e.detail.mappingId));
        document.addEventListener('discover-claims', (e) => this.showDiscoveryModal());
        document.addEventListener('view-profile', (e) => this.viewUserProfile(e.detail.profileId));

        // Setup form submission listeners
        this.setupFormListeners();

        console.log('Unified OIDC & Claims event listeners setup complete');
    },

    // Setup form submission event listeners
    setupFormListeners() {
        // Add OIDC Provider form
        const addOidcForm = document.getElementById('add-oidc-form');
        if (addOidcForm && !addOidcForm.hasAttribute('data-unified-listener')) {
            addOidcForm.addEventListener('submit', this.handleAddProviderSubmit.bind(this));
            addOidcForm.setAttribute('data-unified-listener', 'true');
            console.log('Add OIDC form listener attached (unified)');
        }

        // Edit OIDC Provider form
        const editOidcForm = document.getElementById('edit-oidc-form');
        if (editOidcForm && !editOidcForm.hasAttribute('data-unified-listener')) {
            editOidcForm.addEventListener('submit', this.handleEditProviderSubmit.bind(this));
            editOidcForm.setAttribute('data-unified-listener', 'true');
            console.log('Edit OIDC form listener attached (unified)');
        }

        // Add Claim Mapping form
        const addClaimForm = document.getElementById('add-claim-mapping-form');
        if (addClaimForm && !addClaimForm.hasAttribute('data-unified-listener')) {
            addClaimForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.handleAddMappingSubmit();
            });
            addClaimForm.setAttribute('data-unified-listener', 'true');
            console.log('Add claim mapping form listener attached (unified)');
        }

        // Edit Claim Mapping form
        const editClaimForm = document.getElementById('edit-claim-mapping-form');
        if (editClaimForm && !editClaimForm.hasAttribute('data-unified-listener')) {
            editClaimForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.handleEditMappingSubmit();
            });
            editClaimForm.setAttribute('data-unified-listener', 'true');
            console.log('Edit claim mapping form listener attached (unified)');
        }

        // If elements aren't found, they might not be rendered yet
        if (!addOidcForm || !editOidcForm || !addClaimForm || !editClaimForm) {
            console.log('Some unified form elements not found yet, will retry when tab is activated');
        }
    },

    // OIDC Provider Management
    showAddProviderModal() {
        const modal = new bootstrap.Modal(document.getElementById('add-oidc-modal'));
        document.getElementById('add-oidc-form').reset();
        modal.show();
    },

    async editProvider(providerId) {
        try {
            const response = await AdminAPI.oidc.get(providerId);
            if (response.ok) {
                const provider = await response.json();
                this.currentProvider = provider;
                
                // Populate the edit form
                document.getElementById('edit-oidc-id').value = provider.id;
                document.getElementById('edit-oidc-display-name').value = provider.display_name || '';
                document.getElementById('edit-oidc-issuer').value = provider.issuer;
                document.getElementById('edit-oidc-client-id').value = provider.client_id;
                document.getElementById('edit-oidc-client-secret').value = ''; // Leave blank for security
                document.getElementById('edit-oidc-well-known').value = provider.well_known_url;
                document.getElementById('edit-oidc-scopes').value = provider.scopes;
                
                const modal = new bootstrap.Modal(document.getElementById('edit-oidc-modal'));
                modal.show();
            } else {
                AdminNotifications.showError('Failed to load OIDC provider data');
            }
        } catch (error) {
            AdminNotifications.handleApiError(error, 'Error loading OIDC provider data');
        }
    },

    async handleAddProviderSubmit(event) {
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
                this.hideAddProviderModal();
                this.refreshProviders();
            } else {
                const error = await response.json();
                AdminNotifications.showError(error.detail || 'Failed to create OIDC provider');
            }
        } catch (error) {
            AdminNotifications.handleApiError(error, 'Error creating OIDC provider');
        }
    },

    async handleEditProviderSubmit(event) {
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
                this.hideEditProviderModal();
                this.refreshProviders();
            } else {
                const error = await response.json();
                AdminNotifications.showError(error.detail || 'Failed to update OIDC provider');
            }
        } catch (error) {
            AdminNotifications.handleApiError(error, 'Error updating OIDC provider');
        }
    },

    hideAddProviderModal() {
        const modalElement = document.getElementById('add-oidc-modal');
        const modal = bootstrap.Modal.getInstance(modalElement);
        if (modal) {
            modal.hide();
            modal.dispose(); // Properly dispose of the modal instance
        }
        // Force remove any leftover backdrop
        this.forceRemoveBackdrop();
    },

    hideEditProviderModal() {
        const modalElement = document.getElementById('edit-oidc-modal');
        const modal = bootstrap.Modal.getInstance(modalElement);
        if (modal) {
            modal.hide();
            modal.dispose(); // Properly dispose of the modal instance
        }
        // Force remove any leftover backdrop
        this.forceRemoveBackdrop();
    },

    // Force remove any leftover modal backdrop and clean up modal classes
    forceRemoveBackdrop() {
        // Use setTimeout to ensure this runs after Bootstrap's cleanup
        setTimeout(() => {
            // Remove any leftover backdrops (multiple selectors to catch all)
            const backdrops = document.querySelectorAll('.modal-backdrop, .modal-backdrop.show, .modal-backdrop.fade');
            backdrops.forEach(backdrop => {
                backdrop.remove();
            });
            
            // Remove all modal-related classes from body
            document.body.classList.remove('modal-open');
            document.body.classList.remove('modal-backdrop');
            
            // Reset all body styles that might be set by Bootstrap
            document.body.style.overflow = '';
            document.body.style.paddingRight = '';
            document.body.style.marginRight = '';
            
            // Remove any stray modal backdrop elements by tag
            const modalElements = document.querySelectorAll('[class*="modal-backdrop"]');
            modalElements.forEach(element => {
                if (element.classList.contains('modal-backdrop') || 
                    element.className.includes('modal-backdrop')) {
                    element.remove();
                }
            });
            
            console.log('Modal backdrop cleanup completed');
        }, 100); // Wait 200ms for Bootstrap animations to finish
    },
    
    // Setup event listeners for modal cleanup
    setupModalEventListeners() {
        // Add hidden event listeners to all modal elements
        const modalIds = [
            'add-oidc-modal',
            'edit-oidc-modal', 
            'add-claim-mapping-modal',
            'edit-claim-mapping-modal',
            'claims-discovery-modal'
        ];
        
        modalIds.forEach(modalId => {
            const modalElement = document.getElementById(modalId);
            if (modalElement) {
                // Listen for when modal is completely hidden
                modalElement.addEventListener('hidden.bs.modal', () => {
                    console.log(`Modal ${modalId} hidden event triggered`);
                    this.forceRemoveBackdrop();
                });
                
                // Listen for when modal hide starts
                modalElement.addEventListener('hide.bs.modal', () => {
                    console.log(`Modal ${modalId} hide event triggered`);
                });
            }
        });
    },

    // Start smart backdrop cleanup monitor
    startBackdropCleanupMonitor() {
        // Monitor for stuck backdrops every 2 seconds (less aggressive)
        setInterval(() => {
            const backdrops = document.querySelectorAll('.modal-backdrop');
            const openModals = document.querySelectorAll('.modal.show, .modal.showing');
            const modalInstances = document.querySelectorAll('.modal[style*="display: block"]');
            
            // Only remove backdrops if ALL conditions are met:
            // 1. There are backdrops present
            // 2. No modals have the 'show' or 'showing' class
            // 3. No modals have display:block style
            // 4. Body doesn't have modal-open class (indicating no active modals)
            const shouldCleanup = backdrops.length > 0 && 
                                openModals.length === 0 && 
                                modalInstances.length === 0 &&
                                !document.body.classList.contains('modal-open');
            
            if (shouldCleanup) {
                // Double-check by waiting a bit more to ensure modal transitions are complete
                setTimeout(() => {
                    const finalCheck = document.querySelectorAll('.modal.show, .modal.showing, .modal[style*="display: block"]').length === 0;
                    if (finalCheck) {
                        console.log('Found genuinely stuck modal backdrops, removing...');
                        backdrops.forEach(backdrop => backdrop.remove());
                        
                        // Clean up body classes and styles
                        document.body.classList.remove('modal-open');
                        document.body.style.overflow = '';
                        document.body.style.paddingRight = '';
                        document.body.style.marginRight = '';
                    }
                }, 300); // Additional 300ms delay for final check
            }
        }, 2000); // Check every 2 seconds instead of 500ms

        // Only allow backdrop clicking if modal is actually hidden
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('modal-backdrop')) {
                // Check if there's actually a modal that should be open
                const activeModals = document.querySelectorAll('.modal.show, .modal.showing');
                if (activeModals.length === 0) {
                    console.log('Backdrop clicked with no active modals, removing...');
                    e.target.remove();
                    this.forceRemoveBackdrop();
                }
            }
        });
    },

    refreshProviders() {
        const providerManager = document.querySelector('oidc-provider-manager');
        if (providerManager) {
            providerManager.loadProviders();
        }
    },

    // Claims Mapping Management
    showAddMappingModal() {
        // Clear the form
        document.getElementById('add-claim-mapping-form').reset();
        
        // Set up mapping type change handler
        const mappingTypeSelect = document.getElementById('new-mapping-type');
        const roleSection = document.getElementById('role-admin-values-section');
        
        mappingTypeSelect.addEventListener('change', function() {
            if (this.value === 'role') {
                roleSection.style.display = 'block';
            } else {
                roleSection.style.display = 'none';
            }
        });
        
        const modal = new bootstrap.Modal(document.getElementById('add-claim-mapping-modal'));
        modal.show();
    },

    async editMapping(mappingId) {
        try {
            const response = await AdminAPI.claims.getMapping(mappingId);
            if (response.ok) {
                const mapping = await response.json();
                this.currentMapping = mapping;
                this.showEditMappingModal(mapping);
            }
        } catch (error) {
            AdminNotifications.handleApiError(error, 'Error loading claim mapping details');
        }
    },

    showEditMappingModal(mapping) {
        // Populate the form with existing data
        document.getElementById('edit-claim-mapping-id').value = mapping.id;
        document.getElementById('edit-claim-name').value = mapping.claim_name;
        document.getElementById('edit-mapped-field-name').value = mapping.mapped_field_name;
        document.getElementById('edit-mapping-type').value = mapping.mapping_type;
        document.getElementById('edit-display-label').value = mapping.display_label || '';
        document.getElementById('edit-is-required').checked = mapping.is_required;
        document.getElementById('edit-default-value').value = mapping.default_value || '';
        document.getElementById('edit-description').value = mapping.description || '';

        // Handle role admin values
        const roleSection = document.getElementById('edit-role-admin-values-section');
        const roleTextarea = document.getElementById('edit-role-admin-values');
        
        if (mapping.mapping_type === 'role') {
            roleSection.style.display = 'block';
            if (mapping.role_admin_values && mapping.role_admin_values.length > 0) {
                roleTextarea.value = mapping.role_admin_values.join('\n');
            } else {
                roleTextarea.value = '';
            }
        } else {
            roleSection.style.display = 'none';
            roleTextarea.value = '';
        }

        // Set up mapping type change handler for edit form
        const mappingTypeSelect = document.getElementById('edit-mapping-type');
        mappingTypeSelect.addEventListener('change', function() {
            if (this.value === 'role') {
                roleSection.style.display = 'block';
            } else {
                roleSection.style.display = 'none';
            }
        });

        const modal = new bootstrap.Modal(document.getElementById('edit-claim-mapping-modal'));
        modal.show();
    },

    async handleAddMappingSubmit() {
        const formData = {
            claim_name: document.getElementById('new-claim-name').value,
            mapped_field_name: document.getElementById('new-mapped-field-name').value,
            mapping_type: document.getElementById('new-mapping-type').value,
            display_label: document.getElementById('new-display-label').value,
            is_required: document.getElementById('new-is-required').checked,
            default_value: document.getElementById('new-default-value').value || null,
            description: document.getElementById('new-description').value || null,
            role_admin_values: []
        };

        // Handle role admin values if it's a role mapping
        if (formData.mapping_type === 'role') {
            const roleValues = document.getElementById('new-role-admin-values').value;
            if (roleValues.trim()) {
                formData.role_admin_values = roleValues.split('\n').map(v => v.trim()).filter(v => v);
            }
        }

        try {
            const response = await AdminAPI.claims.createMapping(formData);
            
            if (response.ok) {
                AdminNotifications.showSuccess('Claim mapping created successfully');
                this.hideClaimMappingModal('add-claim-mapping-modal');
                this.refreshMappings();
            } else {
                const error = await response.text();
                AdminNotifications.showError(`Failed to create claim mapping: ${error}`);
            }
        } catch (error) {
            AdminNotifications.handleApiError(error, 'Error creating claim mapping');
        }
    },

    async handleEditMappingSubmit() {
        const mappingId = document.getElementById('edit-claim-mapping-id').value;
        const formData = {
            claim_name: document.getElementById('edit-claim-name').value,
            mapped_field_name: document.getElementById('edit-mapped-field-name').value,
            mapping_type: document.getElementById('edit-mapping-type').value,
            display_label: document.getElementById('edit-display-label').value,
            is_required: document.getElementById('edit-is-required').checked,
            default_value: document.getElementById('edit-default-value').value || null,
            description: document.getElementById('edit-description').value || null,
            role_admin_values: []
        };

        // Handle role admin values if it's a role mapping
        if (formData.mapping_type === 'role') {
            const roleValues = document.getElementById('edit-role-admin-values').value;
            if (roleValues.trim()) {
                formData.role_admin_values = roleValues.split('\n').map(v => v.trim()).filter(v => v);
            }
        }

        try {
            const response = await AdminAPI.claims.updateMapping(mappingId, formData);
            
            if (response.ok) {
                AdminNotifications.showSuccess('Claim mapping updated successfully');
                this.hideClaimMappingModal('edit-claim-mapping-modal');
                this.refreshMappings();
            } else {
                const error = await response.text();
                AdminNotifications.showError(`Failed to update claim mapping: ${error}`);
            }
        } catch (error) {
            AdminNotifications.handleApiError(error, 'Error updating claim mapping');
        }
    },

    // Hide claim mapping modal with proper cleanup
    hideClaimMappingModal(modalId) {
        const modalElement = document.getElementById(modalId);
        const modal = bootstrap.Modal.getInstance(modalElement);
        if (modal) {
            modal.hide();
            modal.dispose(); // Properly dispose of the modal instance
        }
        // Force remove any leftover backdrop
        this.forceRemoveBackdrop();
    },

    refreshMappings() {
        const claimsManager = document.querySelector('claims-mapping-manager');
        if (claimsManager) {
            claimsManager.loadMappings();
        }
    },

    // Claims Discovery
    showDiscoveryModal() {
        // Clear previous results
        document.getElementById('sample-oidc-token').value = '';
        document.getElementById('discovery-results').style.display = 'none';
        
        const modal = new bootstrap.Modal(document.getElementById('claims-discovery-modal'));
        modal.show();
    },

    async handleDiscoverClaims() {
        const token = document.getElementById('sample-oidc-token').value.trim();
        
        if (!token) {
            AdminNotifications.showError('Please paste a valid OIDC token or JSON claims object');
            return;
        }

        // Basic validation to help users
        const isJWT = token.includes('.') && token.split('.').length === 3;
        const isJSON = token.startsWith('{') && token.endsWith('}');
        
        if (!isJWT && !isJSON) {
            AdminNotifications.showError('Please provide either a JWT token (e.g., eyJhbGciOi...) or a JSON claims object (e.g., {"sub": "123", "email": "user@example.com"})');
            return;
        }

        try {
            const response = await AdminAPI.claims.discoverClaims({ sample_token: token });
            
            if (response.ok) {
                const data = await response.json();
                this.displayDiscoveryResults(data);
                document.getElementById('discovery-results').style.display = 'block';
                
                const tokenType = isJWT ? 'JWT token' : 'JSON claims object';
                AdminNotifications.showSuccess(`Successfully processed ${tokenType} and discovered ${Object.keys(data.discovered_claims).length} claims`);
            } else {
                const error = await response.text();
                AdminNotifications.showError(`Claims discovery failed: ${error}`);
            }
        } catch (error) {
            AdminNotifications.handleApiError(error, 'Error discovering claims');
        }
    },

    displayDiscoveryResults(data) {
        // Display discovered claims
        const discoveredList = document.getElementById('discovered-claims-list');
        discoveredList.innerHTML = '';
        
        if (data.discovered_claims && Object.keys(data.discovered_claims).length > 0) {
            Object.entries(data.discovered_claims).forEach(([key, value]) => {
                const item = document.createElement('div');
                item.className = 'mb-2 p-2 border rounded';
                item.innerHTML = `
                    <strong>${key}:</strong> 
                    <span class="text-muted">${JSON.stringify(value)}</span>
                `;
                discoveredList.appendChild(item);
            });
        } else {
            discoveredList.innerHTML = '<p class="text-muted">No claims discovered</p>';
        }

        // Display unmapped claims
        const unmappedList = document.getElementById('unmapped-claims-list');
        unmappedList.innerHTML = '';
        
        if (data.unmapped_claims && data.unmapped_claims.length > 0) {
            data.unmapped_claims.forEach(claim => {
                const item = document.createElement('div');
                item.className = 'mb-2 p-2 border rounded bg-warning-subtle';
                item.innerHTML = `
                    <strong>${claim}</strong>
                    <button class="btn btn-sm btn-outline-primary float-end" onclick="AdminOIDCClaims.quickMapClaim('${claim}')">
                        Quick Map
                    </button>
                `;
                unmappedList.appendChild(item);
            });
        } else {
            unmappedList.innerHTML = '<p class="text-muted">All claims are mapped</p>';
        }

        // Display existing mappings
        const mappingsTable = document.getElementById('existing-mappings-table');
        mappingsTable.innerHTML = '';
        
        if (data.existing_mappings && data.existing_mappings.length > 0) {
            data.existing_mappings.forEach(mapping => {
                const row = document.createElement('tr');
                const status = data.discovered_claims[mapping.claim_name] ? 
                    '<span class="badge bg-success">Found</span>' : 
                    '<span class="badge bg-warning">Not Found</span>';
                
                row.innerHTML = `
                    <td>${mapping.claim_name}</td>
                    <td>${mapping.mapped_field_name}</td>
                    <td><span class="badge bg-${mapping.mapping_type === 'role' ? 'warning' : 'info'}">${mapping.mapping_type}</span></td>
                    <td>${status}</td>
                `;
                mappingsTable.appendChild(row);
            });
        }
    },

    quickMapClaim(claimName) {
        this.showAddMappingModal();
        document.getElementById('new-claim-name').value = claimName;
        document.getElementById('new-mapped-field-name').value = claimName.replace(/[^a-zA-Z0-9]/g, '_').toLowerCase();
        document.getElementById('new-display-label').value = claimName.charAt(0).toUpperCase() + claimName.slice(1);
    },

    // User Profile Management
    async viewUserProfile(profileId) {
        try {
            const response = await AdminAPI.claims.getUserProfile(profileId);
            if (response.ok) {
                const profile = await response.json();
                const profileData = JSON.stringify(profile.profile_data, null, 2);
                
                // Show in a modal instead of alert
                const modal = document.getElementById('user-profile-modal');
                if (modal) {
                    document.getElementById('profile-user-email').textContent = profile.email;
                    document.getElementById('profile-data-display').textContent = profileData;
                    new bootstrap.Modal(modal).show();
                } else {
                    AdminNotifications.showInfo(`User Profile for ${profile.email}:\n\n${profileData}`);
                }
            }
        } catch (error) {
            AdminNotifications.handleApiError(error, 'Error loading user profile details');
        }
    },

    // Ensure initialization when tab becomes active
    ensureInitialized() {
        console.log('Ensuring unified OIDC & Claims module is properly initialized...');
        this.setupEventListeners();
        this.setupFormListeners();
    }
};

// Export for global access
window.AdminOIDCClaims = AdminOIDCClaims;

// Initialize when module loads
AdminOIDCClaims.init();

console.log('Unified OIDC & Claims module loaded!');
