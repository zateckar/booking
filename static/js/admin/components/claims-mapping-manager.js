/* Claims Mapping Manager Web Component */

class ClaimsMappingManager extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
        this.mappings = [];
        this.userProfiles = [];
    }

    connectedCallback() {
        this.render();
        this.setupEventListeners();
        // Wait for auth module to be ready before loading data
        this.waitForAuthAndLoad();
    }

    render() {
        this.shadowRoot.innerHTML = `
            <style>
                :host {
                    display: block;
                    font-family: inherit;
                }
                
                .claims-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 1rem;
                    padding: 1rem;
                    background: #f8f9fa;
                    border-radius: 0.375rem;
                }
                
                .claims-table {
                    width: 100%;
                    border-collapse: collapse;
                    margin-bottom: 1rem;
                }
                
                .claims-table th,
                .claims-table td {
                    padding: 0.75rem;
                    text-align: left;
                    border-bottom: 1px solid #dee2e6;
                }
                
                .claims-table th {
                    background-color: #f8f9fa;
                    font-weight: 600;
                }
                
                .btn {
                    padding: 0.375rem 0.75rem;
                    margin: 0 0.125rem;
                    border: 1px solid transparent;
                    border-radius: 0.375rem;
                    cursor: pointer;
                    text-decoration: none;
                    display: inline-block;
                    font-size: 0.875rem;
                    transition: all 0.15s ease-in-out;
                }
                
                .btn-primary {
                    color: #fff;
                    background-color: #0d6efd;
                    border-color: #0d6efd;
                }
                
                .btn-primary:hover {
                    background-color: #0b5ed7;
                    border-color: #0a58ca;
                }
                
                .btn-success {
                    color: #fff;
                    background-color: #198754;
                    border-color: #198754;
                }
                
                .btn-success:hover {
                    background-color: #157347;
                    border-color: #146c43;
                }
                
                .btn-info {
                    color: #000;
                    background-color: #0dcaf0;
                    border-color: #0dcaf0;
                }
                
                .btn-info:hover {
                    background-color: #31d2f2;
                    border-color: #25cff2;
                }
                
                .btn-danger {
                    color: #fff;
                    background-color: #dc3545;
                    border-color: #dc3545;
                }
                
                .btn-danger:hover {
                    background-color: #bb2d3b;
                    border-color: #b02a37;
                }
                
                .btn-sm {
                    padding: 0.25rem 0.5rem;
                    font-size: 0.75rem;
                    border-radius: 0.25rem;
                }
                
                .badge {
                    display: inline-block;
                    padding: 0.25em 0.5em;
                    font-size: 0.75em;
                    font-weight: 700;
                    line-height: 1;
                    text-align: center;
                    white-space: nowrap;
                    vertical-align: baseline;
                    border-radius: 0.375rem;
                }
                
                .bg-warning {
                    color: #000;
                    background-color: #ffc107;
                }
                
                .bg-info {
                    color: #000;
                    background-color: #0dcaf0;
                }
                
                .bg-danger {
                    color: #fff;
                    background-color: #dc3545;
                }
                
                .bg-secondary {
                    color: #fff;
                    background-color: #6c757d;
                }
                
                .loading {
                    text-align: center;
                    padding: 2rem;
                    color: #6c757d;
                }
                
                .error {
                    color: #dc3545;
                    text-align: center;
                    padding: 1rem;
                }
                
                .empty {
                    text-align: center;
                    padding: 2rem;
                    color: #6c757d;
                }
                
                .alert {
                    padding: 0.75rem 1.25rem;
                    margin-bottom: 1rem;
                    border: 1px solid transparent;
                    border-radius: 0.375rem;
                }
                
                .alert-info {
                    color: #055160;
                    background-color: #cff4fc;
                    border-color: #b6effb;
                }
                
                .tabs {
                    display: flex;
                    border-bottom: 1px solid #dee2e6;
                    margin-bottom: 1rem;
                }
                
                .tab {
                    padding: 0.75rem 1rem;
                    cursor: pointer;
                    border-bottom: 2px solid transparent;
                    transition: all 0.15s ease-in-out;
                }
                
                .tab.active {
                    border-bottom-color: #0d6efd;
                    color: #0d6efd;
                }
                
                .tab:hover {
                    background-color: #f8f9fa;
                }
                
                .tab-content {
                    display: none;
                }
                
                .tab-content.active {
                    display: block;
                }
            </style>
            
            <div class="claims-header">
                <div>
                    <h5>🔗 Claims Mapping</h5>
                    <small>Map OIDC token claims to user profile fields</small>
                </div>
                <div>
                    <button class="btn btn-success btn-sm" id="add-mapping-btn">➕ Add Mapping</button>
                    <button class="btn btn-info btn-sm" id="discover-claims-btn">🔍 Discover Claims</button>
                    <button class="btn btn-primary btn-sm" id="refresh-mappings-btn">🔄 Refresh</button>
                </div>
            </div>
            
            <div class="alert alert-info">
                <strong>Claims Mapping:</strong> Configure how OIDC token claims are mapped to internal user profile fields. 
                Use "Discover Claims" to analyze a sample token from your OIDC provider.
            </div>
            
            <div class="tabs">
                <div class="tab active" data-tab="mappings">Claim Mappings</div>
                <div class="tab" data-tab="profiles">User Profiles</div>
            </div>
            
            <div class="tab-content active" id="mappings-content">
                <div class="loading">Loading claim mappings...</div>
            </div>
            
            <div class="tab-content" id="profiles-content">
                <div class="loading">Loading user profiles...</div>
            </div>
        `;
    }

    setupEventListeners() {
        const addBtn = this.shadowRoot.getElementById('add-mapping-btn');
        const discoverBtn = this.shadowRoot.getElementById('discover-claims-btn');
        const refreshBtn = this.shadowRoot.getElementById('refresh-mappings-btn');
        const tabs = this.shadowRoot.querySelectorAll('.tab');
        
        addBtn.addEventListener('click', () => this.showAddMappingModal());
        discoverBtn.addEventListener('click', () => this.showDiscoveryModal());
        refreshBtn.addEventListener('click', () => this.loadMappings());
        
        tabs.forEach(tab => {
            tab.addEventListener('click', () => this.switchTab(tab.dataset.tab));
        });
    }

    switchTab(tabName) {
        // Update tab buttons
        this.shadowRoot.querySelectorAll('.tab').forEach(tab => {
            tab.classList.toggle('active', tab.dataset.tab === tabName);
        });
        
        // Update tab content
        this.shadowRoot.querySelectorAll('.tab-content').forEach(content => {
            content.classList.toggle('active', content.id === `${tabName}-content`);
        });
        
        // Load data for the active tab
        if (tabName === 'profiles' && this.userProfiles.length === 0) {
            this.loadUserProfiles();
        }
    }

    async waitForAuthAndLoad() {
        const content = this.shadowRoot.getElementById('mappings-content');
        content.innerHTML = '<div class="loading">Loading claim mappings...</div>';
        
        // Wait for auth module to be ready
        let retries = 0;
        const maxRetries = 20; // 10 seconds max wait
        
        while (retries < maxRetries) {
            if (window.auth && window.AdminAPI) {
                await this.loadMappings();
                return;
            }
            
            retries++;
            await new Promise(resolve => setTimeout(resolve, 500));
        }
        
        // If auth module still not ready after timeout
        content.innerHTML = '<div class="error">Authentication module not ready. Please refresh the page.</div>';
    }
    
    async loadMappings() {
        const content = this.shadowRoot.getElementById('mappings-content');
        
        try {
            if (!window.AdminAPI || !window.auth) {
                throw new Error('Required modules not loaded');
            }
            
            const response = await AdminAPI.claims.getMappings();
            if (response.ok) {
                this.mappings = await response.json();
                this.renderMappings();
            } else {
                content.innerHTML = '<div class="error">Failed to load claim mappings</div>';
            }
        } catch (error) {
            content.innerHTML = '<div class="error">Error loading claim mappings</div>';
            console.error('Failed to load mappings:', error);
        }
    }

    async loadUserProfiles() {
        const content = this.shadowRoot.getElementById('profiles-content');
        content.innerHTML = '<div class="loading">Loading user profiles...</div>';
        
        try {
            const response = await AdminAPI.claims.getUserProfiles();
            if (response.ok) {
                const data = await response.json();
                this.userProfiles = data.profiles || [];
                this.renderUserProfiles();
            } else {
                content.innerHTML = '<div class="error">Failed to load user profiles</div>';
            }
        } catch (error) {
            content.innerHTML = '<div class="error">Error loading user profiles</div>';
            console.error('Failed to load user profiles:', error);
        }
    }

    renderMappings() {
        const content = this.shadowRoot.getElementById('mappings-content');
        
        if (this.mappings.length === 0) {
            content.innerHTML = '<div class="empty">No claim mappings configured</div>';
            return;
        }
        
        const table = document.createElement('table');
        table.className = 'claims-table';
        table.innerHTML = `
            <thead>
                <tr>
                    <th>Claim Name</th>
                    <th>Mapped Field</th>
                    <th>Type</th>
                    <th>Required</th>
                    <th>Display Label</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                ${this.mappings.map(mapping => `
                    <tr>
                        <td>${this.escapeHtml(mapping.claim_name)}</td>
                        <td>${this.escapeHtml(mapping.mapped_field_name)}</td>
                        <td>
                            <span class="badge ${mapping.mapping_type === 'role' ? 'bg-warning' : 'bg-info'}">${mapping.mapping_type}</span>
                        </td>
                        <td>
                            <span class="badge ${mapping.is_required ? 'bg-danger' : 'bg-secondary'}">${mapping.is_required ? 'Yes' : 'No'}</span>
                        </td>
                        <td>${this.escapeHtml(mapping.display_label || '')}</td>
                        <td>
                            <button class="btn btn-primary btn-sm" onclick="this.getRootNode().host.editMapping(${mapping.id})">Edit</button>
                            <button class="btn btn-danger btn-sm" onclick="this.getRootNode().host.deleteMapping(${mapping.id})">Delete</button>
                        </td>
                    </tr>
                `).join('')}
            </tbody>
        `;
        
        content.innerHTML = '';
        content.appendChild(table);
    }

    renderUserProfiles() {
        const content = this.shadowRoot.getElementById('profiles-content');
        
        if (this.userProfiles.length === 0) {
            content.innerHTML = '<div class="empty">No user profiles found</div>';
            return;
        }
        
        const table = document.createElement('table');
        table.className = 'claims-table';
        table.innerHTML = `
            <thead>
                <tr>
                    <th>User Email</th>
                    <th>Profile Fields</th>
                    <th>Last OIDC Update</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                ${this.userProfiles.map(profile => {
                    const profileFields = Object.keys(profile.profile_data || {}).length;
                    const lastUpdate = profile.last_oidc_update ? 
                        new Date(profile.last_oidc_update).toLocaleString() : 'Never';
                    
                    return `
                        <tr>
                            <td>${this.escapeHtml(profile.email)}</td>
                            <td>${profileFields} fields</td>
                            <td>${lastUpdate}</td>
                            <td>
                                <button class="btn btn-info btn-sm" onclick="this.getRootNode().host.viewProfile(${profile.user_id})">View Details</button>
                            </td>
                        </tr>
                    `;
                }).join('')}
            </tbody>
        `;
        
        content.innerHTML = '';
        content.appendChild(table);
    }

    escapeHtml(unsafe) {
        return unsafe
            ? unsafe
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;")
                .replace(/"/g, "&quot;")
                .replace(/'/g, "&#039;")
            : '';
    }

    showAddMappingModal() {
        this.dispatchEvent(new CustomEvent('add-mapping', {
            bubbles: true,
            detail: { action: 'add' }
        }));
    }

    showDiscoveryModal() {
        this.dispatchEvent(new CustomEvent('discover-claims', {
            bubbles: true,
            detail: { action: 'discover' }
        }));
    }

    editMapping(mappingId) {
        this.dispatchEvent(new CustomEvent('edit-mapping', {
            bubbles: true,
            detail: { mappingId, action: 'edit' }
        }));
    }

    async deleteMapping(mappingId) {
        if (!confirm('Are you sure you want to delete this claim mapping?')) {
            return;
        }

        try {
            const response = await AdminAPI.claims.deleteMapping(mappingId);
            if (response.ok) {
                this.dispatchEvent(new CustomEvent('mapping-deleted', {
                    bubbles: true,
                    detail: { mappingId }
                }));
                await this.loadMappings();
            } else {
                alert('Failed to delete mapping');
            }
        } catch (error) {
            console.error('Error deleting mapping:', error);
            alert('Error deleting mapping');
        }
    }

    viewProfile(profileId) {
        this.dispatchEvent(new CustomEvent('view-profile', {
            bubbles: true,
            detail: { profileId, action: 'view' }
        }));
    }
}

customElements.define('claims-mapping-manager', ClaimsMappingManager);
