/* OIDC Provider Manager Web Component */

class OIDCProviderManager extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
        this.providers = [];
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
                
                .provider-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 1rem;
                    padding: 1rem;
                    background: #f8f9fa;
                    border-radius: 0.375rem;
                }
                
                .provider-table {
                    width: 100%;
                    border-collapse: collapse;
                    margin-bottom: 1rem;
                }
                
                .provider-table th,
                .provider-table td {
                    padding: 0.75rem;
                    text-align: left;
                    border-bottom: 1px solid #dee2e6;
                }
                
                .provider-table th {
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
            </style>
            
            <div class="provider-header">
                <div>
                    <h5>🔐 OIDC Providers</h5>
                    <small>Manage OpenID Connect identity providers</small>
                </div>
                <div>
                    <button class="btn btn-success btn-sm" id="add-provider-btn">➕ Add Provider</button>
                    <button class="btn btn-primary btn-sm" id="refresh-providers-btn">🔄 Refresh</button>
                </div>
            </div>
            
            <div id="providers-content">
                <div class="loading">Loading providers...</div>
            </div>
        `;
    }

    setupEventListeners() {
        const addBtn = this.shadowRoot.getElementById('add-provider-btn');
        const refreshBtn = this.shadowRoot.getElementById('refresh-providers-btn');
        
        addBtn.addEventListener('click', () => this.showAddModal());
        refreshBtn.addEventListener('click', () => this.loadProviders());
    }

    async waitForAuthAndLoad() {
        const content = this.shadowRoot.getElementById('providers-content');
        content.innerHTML = '<div class="loading">Loading providers...</div>';
        
        // Wait for auth module to be ready
        let retries = 0;
        const maxRetries = 20; // 10 seconds max wait
        
        while (retries < maxRetries) {
            if (window.auth && window.auth.makeAuthenticatedRequest && window.AdminAPI) {
                await this.loadProviders();
                return;
            }
            
            retries++;
            await new Promise(resolve => setTimeout(resolve, 500));
        }
        
        // If auth module still not ready after timeout
        content.innerHTML = '<div class="error">Authentication module not ready. Please refresh the page.</div>';
    }
    
    async loadProviders() {
        const content = this.shadowRoot.getElementById('providers-content');
        
        try {
            if (!window.AdminAPI || !window.auth) {
                throw new Error('Required modules not loaded');
            }
            
            const response = await AdminAPI.oidc.getAll();
            if (response.ok) {
                this.providers = await response.json();
                this.renderProviders();
            } else {
                content.innerHTML = '<div class="error">Failed to load providers</div>';
            }
        } catch (error) {
            content.innerHTML = '<div class="error">Error loading providers</div>';
            console.error('Failed to load providers:', error);
        }
    }

    renderProviders() {
        const content = this.shadowRoot.getElementById('providers-content');
        
        if (this.providers.length === 0) {
            content.innerHTML = '<div class="empty">No OIDC providers configured</div>';
            return;
        }
        
        const table = document.createElement('table');
        table.className = 'provider-table';
        table.innerHTML = `
            <thead>
                <tr>
                    <th>Display Name</th>
                    <th>Issuer</th>
                    <th>Client ID</th>
                    <th>Scopes</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                ${this.providers.map(provider => `
                    <tr>
                        <td><strong>${this.escapeHtml(provider.display_name || provider.issuer)}</strong></td>
                        <td><small>${this.escapeHtml(provider.issuer)}</small></td>
                        <td>${this.escapeHtml(provider.client_id)}</td>
                        <td>${this.escapeHtml(provider.scopes || '')}</td>
                        <td>
                            <button class="btn btn-primary btn-sm" onclick="this.getRootNode().host.editProvider(${provider.id})">Edit</button>
                            <button class="btn btn-danger btn-sm" onclick="this.getRootNode().host.deleteProvider(${provider.id})">Delete</button>
                        </td>
                    </tr>
                `).join('')}
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

    showAddModal() {
        this.dispatchEvent(new CustomEvent('add-provider', {
            bubbles: true,
            detail: { action: 'add' }
        }));
    }

    editProvider(providerId) {
        this.dispatchEvent(new CustomEvent('edit-provider', {
            bubbles: true,
            detail: { providerId, action: 'edit' }
        }));
    }

    async deleteProvider(providerId) {
        if (!confirm('Are you sure you want to delete this OIDC provider?')) {
            return;
        }

        try {
            const response = await AdminAPI.oidc.delete(providerId);
            if (response.ok) {
                this.dispatchEvent(new CustomEvent('provider-deleted', {
                    bubbles: true,
                    detail: { providerId }
                }));
                await this.loadProviders();
            } else {
                alert('Failed to delete provider');
            }
        } catch (error) {
            console.error('Error deleting provider:', error);
            alert('Error deleting provider');
        }
    }
}

customElements.define('oidc-provider-manager', OIDCProviderManager);
