/**
 * User Manager Web Component
 */
class UserManager extends HTMLElement {
    constructor() {
        super();
        this.users = [];
    }

    connectedCallback() {
        this.render();
        this.setupEventListeners();
        if (window.AdminAPI) {
            this.loadUsers();
        } else {
            document.addEventListener('admin-api-loaded', () => this.loadUsers());
        }
    }

    render() {
        this.innerHTML = `
            <div class="card shadow-sm">
                <div class="card-header d-flex justify-content-between align-items-center">
                    <h5 class="card-title mb-0">
                        <i class="fas fa-users me-2"></i>User Management
                    </h5>
                    <div class="btn-group" role="group">
                        <button class="btn btn-primary btn-sm" id="add-user-btn" title="Add New User">
                            Add User
                        </button>
                        <button class="btn btn-light btn-sm" id="refresh-users-btn" title="Refresh">
                            Refresh
                        </button>
                    </div>
                </div>
                <div class="card-body">
                    <div class="table-responsive">
                        <table class="table table-striped table-hover">
                            <thead>
                                <tr>
                                    <th>ID</th>
                                    <th>Name</th>
                                    <th>Email</th>
                                    <th>Is Admin</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody id="user-list">
                                <!-- User rows will be inserted here -->
                            </tbody>
                        </table>
                    </div>
                </div>
                <div id="loading-overlay" class="position-absolute top-0 start-0 w-100 h-100 d-none" 
                     style="background: rgba(255,255,255,0.8); z-index: 10;">
                    <div class="d-flex justify-content-center align-items-center h-100">
                        <div class="spinner-border text-primary" role="status">
                            <span class="visually-hidden">Loading...</span>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Edit User Modal -->
            <div class="modal fade" id="edit-user-modal" tabindex="-1" aria-labelledby="editUserModalLabel" aria-hidden="true">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title" id="editUserModalLabel">Edit User</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body">
                            <p><strong>User ID:</strong> <span id="edit-user-id"></span></p>
                            <p><strong>Email:</strong> <span id="edit-user-email"></span></p>
                            <div class="mb-3">
                                <label for="edit-user-password" class="form-label">New Password</label>
                                <input type="password" class="form-control" id="edit-user-password" placeholder="Enter new password">
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                            <button type="button" class="btn btn-primary" id="save-user-changes-btn">Save changes</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    setupEventListeners() {
        this.querySelector('#refresh-users-btn').addEventListener('click', () => this.loadUsers());
        this.querySelector('#add-user-btn').addEventListener('click', () => this.addUser());

        const userList = this.querySelector('#user-list');
        userList.addEventListener('click', (event) => {
            const target = event.target;
            const row = target.closest('tr');
            if (!row) return;

            const userId = row.dataset.userId;

            if (target.matches('.edit-user-btn')) {
                this.editUser(userId);
            } else if (target.matches('.delete-user-btn')) {
                this.deleteUser(userId);
            } else if (target.matches('.admin-toggle')) {
                this.toggleAdminStatus(userId, target.checked);
            }
        });
        
        const saveChangesBtn = this.querySelector('#save-user-changes-btn');
        saveChangesBtn.addEventListener('click', () => {
            const userId = saveChangesBtn.dataset.userId;
            this.changePassword(userId);
        });
    }

    async loadUsers() {
        this.setLoading(true);
        try {
            const response = await window.AdminAPI.users.getAll();
            if (!response.ok) {
                throw new Error('Failed to fetch users');
            }
            this.users = await response.json();
            this.renderUserList();
        } catch (error) {
            console.error('Failed to load users', error);
            this.querySelector('#user-list').innerHTML = '<tr><td colspan="5" class="text-danger">Failed to load users.</td></tr>';
        } finally {
            this.setLoading(false);
        }
    }

    renderUserList() {
        const userListBody = this.querySelector('#user-list');
        if (this.users.length === 0) {
            userListBody.innerHTML = '<tr><td colspan="5" class="text-center">No users found.</td></tr>';
            return;
        }

        userListBody.innerHTML = this.users.map(user => `
            <tr data-user-id="${user.id}">
                <td>${user.id}</td>
                <td>${user.name || 'N/A'}</td>
                <td>${user.email}</td>
                <td>
                    <div class="form-check form-switch">
                        <input class="form-check-input admin-toggle" type="checkbox" role="switch" ${user.is_admin ? 'checked' : ''}>
                    </div>
                </td>
                <td>
                    <button class="btn btn-sm btn-outline-primary edit-user-btn" title="Edit User">Edit</button>
                    <button class="btn btn-sm btn-outline-danger delete-user-btn" title="Delete User">Delete</button>
                </td>
            </tr>
        `).join('');
    }

    setLoading(loading) {
        const overlay = this.querySelector('#loading-overlay');
        overlay.classList.toggle('d-none', !loading);
    }

    async addUser() {
        const email = prompt('Enter user email:');
        if (!email) return;

        const password = prompt('Enter user password:');
        if (!password) return;

        this.setLoading(true);
        try {
            const response = await window.AdminAPI.users.create({ email, password });
            if (!response.ok) {
                throw new Error('Failed to create user');
            }
            await this.loadUsers();
        } catch (error) {
            console.error('Failed to create user', error);
            alert('Failed to create user.');
        } finally {
            this.setLoading(false);
        }
    }

    async toggleAdminStatus(userId, newAdminStatus) {
        this.setLoading(true);
        try {
            const response = await window.AdminAPI.users.setAdmin(userId, newAdminStatus);
            if (!response.ok) {
                throw new Error('Failed to update user admin status');
            }
            // No need to reload all users, just update the local state
            const user = this.users.find(u => u.id == userId);
            if (user) {
                user.is_admin = newAdminStatus;
            }
        } catch (error) {
            console.error('Failed to update user', error);
            alert('Failed to update user admin status.');
            this.loadUsers(); // Reload to revert the switch state on failure
        } finally {
            this.setLoading(false);
        }
    }

    async editUser(userId) {
        const user = this.users.find(u => u.id == userId);
        if (!user) {
            console.error('User not found for editing');
            return;
        }

        this.querySelector('#edit-user-id').textContent = user.id;
        this.querySelector('#edit-user-email').textContent = user.email;
        this.querySelector('#edit-user-password').value = '';
        
        const saveBtn = this.querySelector('#save-user-changes-btn');
        saveBtn.dataset.userId = userId;

        const modal = new bootstrap.Modal(this.querySelector('#edit-user-modal'));
        modal.show();
    }

    async changePassword(userId) {
        const password = this.querySelector('#edit-user-password').value;
        if (!password) {
            alert('Password cannot be empty.');
            return;
        }

        this.setLoading(true);
        try {
            const response = await window.AdminAPI.users.setPassword(userId, password);
            if (!response.ok) {
                throw new Error('Failed to change password');
            }
            alert('Password changed successfully.');
            const modal = bootstrap.Modal.getInstance(this.querySelector('#edit-user-modal'));
            modal.hide();
        } catch (error) {
            console.error('Failed to change password', error);
            alert('Failed to change password.');
        } finally {
            this.setLoading(false);
        }
    }

    async deleteUser(userId) {
        const user = this.users.find(u => u.id == userId);
        if (!user) {
            console.error('User not found for deletion');
            return;
        }

        if (!confirm(`Are you sure you want to delete user ${user.email}?`)) {
            return;
        }

        this.setLoading(true);
        try {
            const response = await window.AdminAPI.users.delete(userId);
            if (!response.ok) {
                throw new Error('Failed to delete user');
            }
            await this.loadUsers();
        } catch (error) {
            console.error('Failed to delete user', error);
            alert('Failed to delete user.');
        } finally {
            this.setLoading(false);
        }
    }
}

customElements.define('user-manager', UserManager);
