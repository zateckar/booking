/* Parking Lots Module - Parking lot management functionality */

const AdminParkingLots = {
    // Load all parking lots for admin view
    async loadParkingLotsAdmin() {
        console.log('🚗 [ParkingLots] Starting loadParkingLotsAdmin()');
        
        const tbody = document.getElementById('parking-lots-admin-table-body');
        if (!tbody) {
            console.error('🚗 [ParkingLots] ERROR: Table body element "parking-lots-admin-table-body" not found!');
            console.log('🚗 [ParkingLots] Available elements with "parking" in ID:', 
                Array.from(document.querySelectorAll('*')).filter(el => el.id && el.id.includes('parking')).map(el => el.id));
            return;
        }
        
        console.log('🚗 [ParkingLots] Table body element found, setting loading state');
        tbody.innerHTML = '<tr><td colspan="5" class="text-center">Loading...</td></tr>';
        
        try {
            console.log('🚗 [ParkingLots] Checking AdminAPI availability...');
            if (!window.AdminAPI) {
                console.error('🚗 [ParkingLots] ERROR: AdminAPI not available on window object!');
                tbody.innerHTML = '<tr><td colspan="5" class="text-center text-danger">AdminAPI not loaded</td></tr>';
                return;
            }
            
            if (!window.AdminAPI.parkingLots) {
                console.error('🚗 [ParkingLots] ERROR: AdminAPI.parkingLots not available!');
                tbody.innerHTML = '<tr><td colspan="5" class="text-center text-danger">ParkingLots API not available</td></tr>';
                return;
            }
            
            console.log('🚗 [ParkingLots] AdminAPI available, making API call...');
            const response = await AdminAPI.parkingLots.getAll();
            
            console.log('🚗 [ParkingLots] API Response received:', {
                ok: response.ok,
                status: response.status,
                statusText: response.statusText,
                url: response.url
            });

            if (response.ok) {
                console.log('🚗 [ParkingLots] Response OK, parsing JSON...');
                const lots = await response.json();
                console.log('🚗 [ParkingLots] Parking lots data received:', lots);
                console.log('🚗 [ParkingLots] Number of lots:', lots.length);
                
                tbody.innerHTML = '';
                
                if (lots.length === 0) {
                    console.log('🚗 [ParkingLots] No parking lots found');
                    tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">No parking lots found</td></tr>';
                    return;
                }
                
                lots.forEach((lot, index) => {
                    console.log(`🚗 [ParkingLots] Processing lot ${index + 1}:`, lot);
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td>${lot.id}</td>
                        <td>${lot.name}</td>
                        <td><img src="${lot.image}" alt="Lot Image" style="max-width: 100px; max-height: 60px;"></td>
                        <td>${lot.space_count}</td>
                        <td>
                            <button class="btn btn-danger btn-sm delete-lot-btn" data-lot-id="${lot.id}">Delete</button>
                        </td>
                    `;
                    tbody.appendChild(row);
                });

                console.log('🚗 [ParkingLots] Setting up delete button event listeners...');
                document.querySelectorAll('.delete-lot-btn').forEach(button => {
                    button.addEventListener('click', (event) => {
                        const lotId = event.target.getAttribute('data-lot-id');
                        console.log('🚗 [ParkingLots] Delete button clicked for lot ID:', lotId);
                        this.deleteParkingLot(lotId);
                    });
                });
                
                console.log('🚗 [ParkingLots] ✅ Successfully loaded and displayed parking lots');
            } else {
                console.error('🚗 [ParkingLots] API Response not OK:', response.status, response.statusText);
                try {
                    const errorData = await response.json();
                    console.error('🚗 [ParkingLots] Error details:', errorData);
                } catch (e) {
                    console.error('🚗 [ParkingLots] Could not parse error response');
                }
                tbody.innerHTML = '<tr><td colspan="5" class="text-center text-danger">Failed to load parking lots</td></tr>';
            }
        } catch (error) {
            console.error('🚗 [ParkingLots] Exception occurred during loadParkingLotsAdmin:', error);
            console.error('🚗 [ParkingLots] Error stack:', error.stack);
            tbody.innerHTML = '<tr><td colspan="5" class="text-center text-danger">Error loading parking lots</td></tr>';
            if (window.AdminNotifications) {
                AdminNotifications.handleApiError(error, 'Failed to load parking lots');
            } else {
                console.error('🚗 [ParkingLots] AdminNotifications not available for error handling');
            }
        }
    },

    // Delete parking lot
    async deleteParkingLot(lotId) {
        const confirmed = await AdminNotifications.confirm('Are you sure you want to delete this parking lot? This will also delete all associated spaces and bookings.');
        if (!confirmed) return;
        
        try {
            const response = await AdminAPI.parkingLots.delete(lotId);

            if (response.ok) {
                const result = await response.json();
                console.log('🚗 [ParkingLots] Delete response:', result);
                
                let message = result.message || 'Parking lot deleted successfully';
                if (result.deleted_spaces > 0 || result.preserved_bookings > 0) {
                    const details = [];
                    if (result.deleted_spaces > 0) {
                        details.push(`${result.deleted_spaces} parking space${result.deleted_spaces > 1 ? 's' : ''} deleted`);
                    }
                    if (result.preserved_bookings > 0) {
                        details.push(`${result.preserved_bookings} booking${result.preserved_bookings > 1 ? 's' : ''} preserved for historical reporting`);
                    }
                    message += `. ${details.join(', ')}.`;
                }
                
                AdminNotifications.showSuccess(message);
                this.loadParkingLotsAdmin();
                
                // Refresh parking spaces if that module is loaded
                if (window.AdminParkingSpaces && typeof window.AdminParkingSpaces.loadParkingLotsForSpaces === 'function') {
                    window.AdminParkingSpaces.loadParkingLotsForSpaces();
                }
            } else {
                const errorData = await response.json().catch(() => ({}));
                AdminNotifications.showError(errorData.detail || 'Failed to delete parking lot');
            }
        } catch (error) {
            AdminNotifications.handleApiError(error, 'Error deleting parking lot');
        }
    },

    // Handle add parking lot form submission
    async handleAddParkingLotSubmit(event) {
        event.preventDefault();
        
        try {
            const formData = new FormData();
            formData.append('name', document.getElementById('new-lot-name').value);
            
            const imageUrl = document.getElementById('new-lot-image').value;
            const imageFile = document.getElementById('new-lot-image-file').files[0];
            
            if (imageFile) {
                formData.append('upload_image', imageFile);
            } else if (imageUrl) {
                formData.append('image', imageUrl);
            } else {
                AdminNotifications.showError('Please provide either an image URL or upload an image file');
                return;
            }

            const response = await AdminAPI.parkingLots.create(formData);

            if (response.ok) {
                AdminNotifications.showSuccess('Parking lot created successfully');
                this.hideAddParkingLotModal();
                this.loadParkingLotsAdmin();
                
                // Refresh spaces dropdown if parking spaces module is loaded
                if (window.AdminParkingSpaces) {
                    window.AdminParkingSpaces.loadParkingLotsForSpaces();
                }
            } else {
                const error = await response.json();
                AdminNotifications.showError(error.detail || 'Failed to create parking lot');
            }
        } catch (error) {
            AdminNotifications.handleApiError(error, 'Error creating parking lot');
        }
    },

    // Show add parking lot modal
    showAddParkingLotModal() {
        const modal = new bootstrap.Modal(document.getElementById('add-parking-lot-modal'));
        document.getElementById('add-parking-lot-form').reset();
        modal.show();
    },

    // Hide add parking lot modal
    hideAddParkingLotModal() {
        const modalElement = document.getElementById('add-parking-lot-modal');
        const modal = bootstrap.Modal.getInstance(modalElement);
        if (modal) {
            modal.hide();
        }
    },

    // Initialize parking lots module
    init() {
        console.log('Initializing parking lots module...');
        
        // Setup form event listeners with retry mechanism
        this.setupEventListeners();
        
        console.log('Parking lots module initialized');
    },

    // Setup event listeners with proper error handling
    setupEventListeners() {
        // Setup form event listeners
        const addParkingLotForm = document.getElementById('add-parking-lot-form');
        if (addParkingLotForm && !addParkingLotForm.hasAttribute('data-parking-lots-listener')) {
            addParkingLotForm.addEventListener('submit', this.handleAddParkingLotSubmit.bind(this));
            addParkingLotForm.setAttribute('data-parking-lots-listener', 'true');
            console.log('Add parking lot form listener attached');
        }

        const addParkingLotBtn = document.getElementById('add-parking-lot-btn');
        if (addParkingLotBtn && !addParkingLotBtn.hasAttribute('data-parking-lots-listener')) {
            addParkingLotBtn.addEventListener('click', this.showAddParkingLotModal.bind(this));
            addParkingLotBtn.setAttribute('data-parking-lots-listener', 'true');
            console.log('Add parking lot button listener attached');
        }

        const refreshParkingLotsBtn = document.getElementById('refresh-parking-lots-btn');
        if (refreshParkingLotsBtn && !refreshParkingLotsBtn.hasAttribute('data-parking-lots-listener')) {
            refreshParkingLotsBtn.addEventListener('click', this.loadParkingLotsAdmin.bind(this));
            refreshParkingLotsBtn.setAttribute('data-parking-lots-listener', 'true');
            console.log('Refresh parking lots button listener attached');
        }

        // If elements aren't found, they might not be rendered yet
        if (!addParkingLotForm || !addParkingLotBtn || !refreshParkingLotsBtn) {
            console.log('Some parking lots elements not found yet, will retry when tab is activated');
        }
    },

    // Ensure initialization when tab becomes active
    ensureInitialized() {
        console.log('Ensuring parking lots module is properly initialized...');
        this.setupEventListeners();
    }
};

// Export for global access
window.AdminParkingLots = AdminParkingLots;

// Initialize when module loads (but elements might not exist yet)
AdminParkingLots.init();

console.log('Admin parking lots module loaded!');
