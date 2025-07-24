/* Users Module - User management functionality */

const AdminUsers = {
    // Load all users
    async loadUsers() {
        const tbody = document.getElementById('users-table-body');
        if (!tbody) return;
        
        tbody.innerHTML = '<tr><td colspan="5" class="text-center">Loading...</td></tr>';
        
        try {
            const response = await AdminAPI.users.getAll();
            
            if (response.ok) {
                const users = await response.json();
                tbody.innerHTML = '';
                users.forEach(user => {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td>${user.id}</td>
                        <td>${user.email}</td>
                        <td>
                            <div class="form-check form-switch">
                                <input class="form-check-input" type="checkbox" ${user.is_admin ? 'checked' : ''} 
                                       onchange="AdminUsers.toggleUserAdmin(${user.id}, this.checked)">
                            </div>
                        </td>
                        <td>${user.bookings ? user.bookings.length : 0}</td>
                        <td>
                            <button class="btn btn-danger btn-sm" onclick="AdminUsers.deleteUser(${user.id})">Delete</button>
                        </td>
                    `;
                    tbody.appendChild(row);
                });
            } else {
                tbody.innerHTML = '<tr><td colspan="5" class="text-center text-danger">Failed to load users</td></tr>';
            }
        } catch (error) {
            tbody.innerHTML = '<tr><td colspan="5" class="text-center text-danger">Error loading users</td></tr>';
            AdminNotifications.handleApiError(error, 'Failed to load users');
        }
    },

    // Toggle user admin status
    async toggleUserAdmin(userId, isAdmin) {
        try {
            const response = await AdminAPI.users.setAdmin(userId, isAdmin);

            if (response.ok) {
                AdminNotifications.showSuccess('User admin status updated');
            } else {
                AdminNotifications.showError('Failed to update user admin status');
                this.loadUsers(); // Reload to revert the checkbox
            }
        } catch (error) {
            AdminNotifications.handleApiError(error, 'Error updating user admin status');
            this.loadUsers();
        }
    },

    // Delete user
    async deleteUser(userId) {
        const confirmed = await AdminNotifications.confirm('Are you sure you want to delete this user?');
        if (!confirmed) return;
        
        try {
            const response = await AdminAPI.users.delete(userId);

            if (response.ok) {
                AdminNotifications.showSuccess('User deleted successfully');
                this.loadUsers();
            } else {
                AdminNotifications.showError('Failed to delete user');
            }
        } catch (error) {
            AdminNotifications.handleApiError(error, 'Error deleting user');
        }
    },

    // Handle add user form submission
    async handleAddUserSubmit(event) {
        event.preventDefault();
        
        try {
            const userData = {
                email: document.getElementById('new-user-email').value,
                password: document.getElementById('new-user-password').value
            };

            const response = await AdminAPI.users.create(userData);

            if (response.ok) {
                const user = await response.json();
                
                // If admin checkbox is checked, set admin status
                if (document.getElementById('new-user-admin').checked) {
                    await AdminAPI.users.setAdmin(user.id, true);
                }
                
                AdminNotifications.showSuccess('User created successfully');
                this.hideAddUserModal();
                this.loadUsers();
            } else {
                const error = await response.json();
                AdminNotifications.showError(error.detail || 'Failed to create user');
            }
        } catch (error) {
            AdminNotifications.handleApiError(error, 'Error creating user');
        }
    },

    // Show add user modal
    showAddUserModal() {
        const modal = new bootstrap.Modal(document.getElementById('add-user-modal'));
        document.getElementById('add-user-form').reset();
        modal.show();
    },

    // Hide add user modal
    hideAddUserModal() {
        const modalElement = document.getElementById('add-user-modal');
        const modal = bootstrap.Modal.getInstance(modalElement);
        if (modal) {
            modal.hide();
        }
    },

    // Initialize users module
    init() {
        console.log('Initializing users module...');
        
        // Setup form event listeners with retry mechanism
        this.setupEventListeners();
        
        console.log('Users module initialized');
    },

    // Setup event listeners with proper error handling
    setupEventListeners() {
        // Setup form event listeners
        const addUserForm = document.getElementById('add-user-form');
        if (addUserForm && !addUserForm.hasAttribute('data-users-listener')) {
            addUserForm.addEventListener('submit', this.handleAddUserSubmit.bind(this));
            addUserForm.setAttribute('data-users-listener', 'true');
            console.log('Add user form listener attached');
        }

        const addUserBtn = document.getElementById('add-user-btn');
        if (addUserBtn && !addUserBtn.hasAttribute('data-users-listener')) {
            addUserBtn.addEventListener('click', this.showAddUserModal.bind(this));
            addUserBtn.setAttribute('data-users-listener', 'true');
            console.log('Add user button listener attached');
        }

        const refreshUsersBtn = document.getElementById('refresh-users-btn');
        if (refreshUsersBtn && !refreshUsersBtn.hasAttribute('data-users-listener')) {
            refreshUsersBtn.addEventListener('click', this.loadUsers.bind(this));
            refreshUsersBtn.setAttribute('data-users-listener', 'true');
            console.log('Refresh users button listener attached');
        }

        // If elements aren't found, they might not be rendered yet
        if (!addUserForm || !addUserBtn || !refreshUsersBtn) {
            console.log('Some users elements not found yet, will retry when tab is activated');
        }
    },

    // Ensure initialization when tab becomes active
    ensureInitialized() {
        console.log('Ensuring users module is properly initialized...');
        this.setupEventListeners();
    }
};

// Export for global access
window.AdminUsers = AdminUsers;

// Initialize when module loads (but elements might not exist yet)
AdminUsers.init();

console.log('Admin users module loaded!');
