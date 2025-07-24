/* Claims Mapping Module - OIDC claims mapping functionality */

const AdminClaims = {
    // Load claim mappings
    async loadClaimMappings() {
        const tbody = document.getElementById('claim-mappings-table-body');
        if (!tbody) return;
        
        tbody.innerHTML = '<tr><td colspan="6" class="text-center">Loading...</td></tr>';
        
        try {
            const response = await AdminAPI.claims.getMappings();

            if (response.ok) {
                const mappings = await response.json();
                tbody.innerHTML = '';
                mappings.forEach(mapping => {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td>${mapping.claim_name}</td>
                        <td>${mapping.mapped_field_name}</td>
                        <td>
                            <span class="badge bg-${mapping.mapping_type === 'role' ? 'warning' : 'info'}">${mapping.mapping_type}</span>
                        </td>
                        <td>
                            <span class="badge bg-${mapping.is_required ? 'danger' : 'secondary'}">${mapping.is_required ? 'Yes' : 'No'}</span>
                        </td>
                        <td>${mapping.display_label}</td>
                        <td>
                            <button class="btn btn-primary btn-sm me-2" onclick="AdminClaims.editClaimMapping(${mapping.id})">Edit</button>
                            <button class="btn btn-danger btn-sm" onclick="AdminClaims.deleteClaimMapping(${mapping.id})">Delete</button>
                        </td>
                    `;
                    tbody.appendChild(row);
                });
            } else {
                tbody.innerHTML = '<tr><td colspan="6" class="text-center text-danger">Failed to load claim mappings</td></tr>';
            }
        } catch (error) {
            tbody.innerHTML = '<tr><td colspan="6" class="text-center text-danger">Error loading claim mappings</td></tr>';
            AdminNotifications.handleApiError(error, 'Failed to load claim mappings');
        }
    },

    // Load user profiles
    async loadUserProfiles() {
        const tbody = document.getElementById('user-profiles-table-body');
        if (!tbody) return;
        
        tbody.innerHTML = '<tr><td colspan="4" class="text-center">Loading...</td></tr>';
        
        try {
            const response = await AdminAPI.claims.getUserProfiles();

            if (response.ok) {
                const data = await response.json();
                const profiles = data.profiles || [];
                tbody.innerHTML = '';
                profiles.forEach(profile => {
                    const row = document.createElement('tr');
                    const profileFields = Object.keys(profile.profile_data || {}).length;
                    const lastUpdate = profile.last_oidc_update ? 
                        new Date(profile.last_oidc_update).toLocaleString() : 'Never';
                    
                    row.innerHTML = `
                        <td>${profile.email}</td>
                        <td>${profileFields} fields</td>
                        <td>${lastUpdate}</td>
                        <td>
                            <button class="btn btn-info btn-sm" onclick="AdminClaims.viewUserProfile(${profile.user_id})">View Details</button>
                        </td>
                    `;
                    tbody.appendChild(row);
                });
            } else {
                tbody.innerHTML = '<tr><td colspan="4" class="text-center text-danger">Failed to load user profiles</td></tr>';
            }
        } catch (error) {
            tbody.innerHTML = '<tr><td colspan="4" class="text-center text-danger">Error loading user profiles</td></tr>';
            AdminNotifications.handleApiError(error, 'Failed to load user profiles');
        }
    },

    // Show add claim mapping modal
    showAddClaimMappingModal() {
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
        
        // Show the modal
        const modal = new bootstrap.Modal(document.getElementById('add-claim-mapping-modal'));
        modal.show();
    },

    // Show claims discovery modal
    showClaimsDiscoveryModal() {
        // Clear previous results
        document.getElementById('sample-oidc-token').value = '';
        document.getElementById('discovery-results').style.display = 'none';
        
        // Show the modal
        const modal = new bootstrap.Modal(document.getElementById('claims-discovery-modal'));
        modal.show();
    },

    // Edit claim mapping
    async editClaimMapping(mappingId) {
        try {
            const response = await AdminAPI.claims.getMapping(mappingId);
            if (response.ok) {
                const mapping = await response.json();
                this.showEditClaimMappingModal(mapping);
            }
        } catch (error) {
            AdminNotifications.handleApiError(error, 'Error loading claim mapping details');
        }
    },

    // Show edit claim mapping modal
    showEditClaimMappingModal(mapping) {
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

        // Show the modal
        const modal = new bootstrap.Modal(document.getElementById('edit-claim-mapping-modal'));
        modal.show();
    },

    // Delete claim mapping
    async deleteClaimMapping(mappingId) {
        const confirmed = await AdminNotifications.confirm('Are you sure you want to delete this claim mapping?');
        if (!confirmed) return;
        
        try {
            const response = await AdminAPI.claims.deleteMapping(mappingId);

            if (response.ok) {
                AdminNotifications.showSuccess('Claim mapping deleted successfully');
                this.loadClaimMappings();
            } else {
                AdminNotifications.showError('Failed to delete claim mapping');
            }
        } catch (error) {
            AdminNotifications.handleApiError(error, 'Error deleting claim mapping');
        }
    },

    // View user profile
    async viewUserProfile(profileId) {
        try {
            const response = await AdminAPI.claims.getUserProfile(profileId);
            if (response.ok) {
                const profile = await response.json();
                const profileData = JSON.stringify(profile.profile_data, null, 2);
                // For now, show an alert - would need to create a modal
                AdminNotifications.showInfo(`User Profile for ${profile.email}:\n\n${profileData}`);
            }
        } catch (error) {
            AdminNotifications.handleApiError(error, 'Error loading user profile details');
        }
    },

    // Initialize claims mapping module
    init() {
        console.log('Claims mapping module initialized');
    },

    // Ensure initialization - sets up event listeners
    ensureInitialized() {
        this.setupEventListeners();
    },

    // Handle adding a new claim mapping
    async handleAddClaimMapping() {
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
                bootstrap.Modal.getInstance(document.getElementById('add-claim-mapping-modal')).hide();
                this.loadClaimMappings();
            } else {
                const error = await response.text();
                AdminNotifications.showError(`Failed to create claim mapping: ${error}`);
            }
        } catch (error) {
            AdminNotifications.handleApiError(error, 'Error creating claim mapping');
        }
    },

    // Handle claims discovery
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
                
                // Show helpful message about what was processed
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

    // Display claims discovery results
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
                    <button class="btn btn-sm btn-outline-primary float-end" onclick="AdminClaims.quickMapClaim('${claim}')">
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

    // Quick map a claim (opens add modal with claim name pre-filled)
    quickMapClaim(claimName) {
        this.showAddClaimMappingModal();
        document.getElementById('new-claim-name').value = claimName;
        document.getElementById('new-mapped-field-name').value = claimName.replace(/[^a-zA-Z0-9]/g, '_').toLowerCase();
        document.getElementById('new-display-label').value = claimName.charAt(0).toUpperCase() + claimName.slice(1);
    },

    // Handle updating a claim mapping
    async handleUpdateClaimMapping() {
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
                bootstrap.Modal.getInstance(document.getElementById('edit-claim-mapping-modal')).hide();
                this.loadClaimMappings();
            } else {
                const error = await response.text();
                AdminNotifications.showError(`Failed to update claim mapping: ${error}`);
            }
        } catch (error) {
            AdminNotifications.handleApiError(error, 'Error updating claim mapping');
        }
    },

    // Setup event listeners for buttons
    setupEventListeners() {
        // Add Mapping button
        const addMappingBtn = document.getElementById('add-claim-mapping-btn');
        if (addMappingBtn) {
            addMappingBtn.addEventListener('click', () => {
                this.showAddClaimMappingModal();
            });
        }

        // Discover Claims button
        const discoverClaimsBtn = document.getElementById('discover-claims-btn');
        if (discoverClaimsBtn) {
            discoverClaimsBtn.addEventListener('click', () => {
                this.showClaimsDiscoveryModal();
            });
        }

        // Refresh Claims Mappings button
        const refreshMappingsBtn = document.getElementById('refresh-claim-mappings-btn');
        if (refreshMappingsBtn) {
            refreshMappingsBtn.addEventListener('click', () => {
                this.loadClaimMappings();
            });
        }

        // Refresh User Profiles button
        const refreshProfilesBtn = document.getElementById('refresh-user-profiles-btn');
        if (refreshProfilesBtn) {
            refreshProfilesBtn.addEventListener('click', () => {
                this.loadUserProfiles();
            });
        }

        console.log('Claims mapping event listeners setup complete');
    }
};

// Export for global access
window.AdminClaims = AdminClaims;

// Initialize when module loads
AdminClaims.init();

console.log('Admin claims mapping module loaded!');
