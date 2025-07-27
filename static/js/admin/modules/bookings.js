/* Bookings Module - Comprehensive booking management functionality */

const AdminBookings = {
    // Current filters and pagination state
    currentFilters: {
        user_id: null,
        parking_lot_id: null,
        start_date: null,
        end_date: null,
        include_cancelled: true
    },
    currentPage: 1,
    itemsPerPage: 20,
    totalBookings: 0,
    isLoading: false, // Flag to prevent multiple simultaneous loads

    // Load all bookings with optional filtering
    async loadBookings() {
        // Prevent multiple simultaneous loads
        if (this.isLoading) {
            console.log('📊 [Bookings] Already loading, skipping duplicate call');
            return;
        }
        
        this.isLoading = true;
        console.log('📊 [Bookings] Starting loadBookings...');
        
        const tbody = document.getElementById('admin-bookings-table-body');
        const pagination = document.getElementById('bookings-pagination');
        
        if (!tbody) {
            console.error('📊 [Bookings] ERROR: admin-bookings-table-body element not found!');
            this.isLoading = false;
            return;
        }
        
        tbody.innerHTML = '<tr><td colspan="10" class="text-center">Loading...</td></tr>';
        
        try {
            // Calculate offset for pagination
            const offset = (this.currentPage - 1) * this.itemsPerPage;
            
            // Prepare API parameters
            const params = {
                ...this.currentFilters,
                limit: this.itemsPerPage,
                offset: offset
            };

            // Remove empty values
            Object.keys(params).forEach(key => {
                if (params[key] === null || params[key] === undefined || params[key] === '') {
                    delete params[key];
                }
            });

            const [bookingsResponse, countResponse] = await Promise.all([
                AdminAPI.bookings.getAll(params),
                AdminAPI.bookings.getCount(this.currentFilters)
            ]);
            
            console.log('📊 [Bookings] API responses received:', {
                bookingsOk: bookingsResponse.ok,
                countOk: countResponse.ok,
                bookingsStatus: bookingsResponse.status,
                countStatus: countResponse.status
            });
            
            if (bookingsResponse.ok && countResponse.ok) {
                const bookings = await bookingsResponse.json();
                const countData = await countResponse.json();
                
                console.log('📊 [Bookings] Response data:', {
                    bookings: bookings,
                    bookingsLength: bookings ? bookings.length : 'null/undefined',
                    countData: countData,
                    totalCount: countData ? countData.count : 'null/undefined'
                });
                
                this.totalBookings = countData.count || 0;
                
                tbody.innerHTML = '';
                
                if (!bookings || bookings.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="10" class="text-center text-muted">No bookings found</td></tr>';
                    console.log('📊 [Bookings] No bookings to display');
                } else {
                    console.log('📊 [Bookings] Creating rows for', bookings.length, 'bookings');
                    bookings.forEach((booking, index) => {
                        console.log(`📊 [Bookings] Creating row ${index + 1}:`, booking);
                        const row = this.createBookingRow(booking);
                        console.log(`📊 [Bookings] Row ${index + 1} created:`, row);
                        console.log(`📊 [Bookings] Row ${index + 1} innerHTML:`, row.innerHTML);
                        tbody.appendChild(row);
                        console.log(`📊 [Bookings] After adding row ${index + 1}, tbody children count:`, tbody.children.length);
                        console.log(`📊 [Bookings] Current tbody content:`, tbody.innerHTML);
                    });
                    console.log('📊 [Bookings] All rows created and added to table');
                }
                
                this.updatePagination();
                this.updateResultsInfo();
                console.log('📊 [Bookings] Table update completed');
                
                // Final check after a short delay to see if content gets overwritten
                setTimeout(() => {
                    console.log('📊 [Bookings] FINAL CHECK - Table content after 500ms:', tbody.innerHTML);
                    console.log('📊 [Bookings] FINAL CHECK - Table children count after 500ms:', tbody.children.length);
                }, 500);
            } else {
                console.error('📊 [Bookings] API request failed:', {
                    bookingsOk: bookingsResponse.ok,
                    bookingsStatus: bookingsResponse.status,
                    countOk: countResponse.ok,
                    countStatus: countResponse.status
                });
                tbody.innerHTML = '<tr><td colspan="10" class="text-center text-danger">Failed to load bookings</td></tr>';
            }
        } catch (error) {
            console.error('📊 [Bookings] Exception during loadBookings:', error);
            tbody.innerHTML = '<tr><td colspan="10" class="text-center text-danger">Error loading bookings</td></tr>';
            if (window.AdminNotifications) {
                AdminNotifications.handleApiError(error, 'Failed to load bookings');
            }
        } finally {
            this.isLoading = false;
            console.log('📊 [Bookings] Loading state reset');
        }
    },

    // Create a table row for a booking
    createBookingRow(booking) {
        const row = document.createElement('tr');
        
        // Handle deleted users/spaces
        const userEmail = booking.user ? booking.user.email : 'Deleted User';
        const parkingLot = booking.space && booking.space.parking_lot ? 
            booking.space.parking_lot.name : 
            (booking.deleted_space_info || 'Unknown');
        const spaceNumber = booking.space ? booking.space.space_number : 'Deleted';
        
        // Format dates
        const startTime = new Date(booking.start_time).toLocaleString();
        const endTime = new Date(booking.end_time).toLocaleString();
        
        // Status badge
        const statusBadge = booking.is_cancelled ? 
            '<span class="badge bg-danger">Cancelled</span>' : 
            '<span class="badge bg-success">Active</span>';
        
        row.innerHTML = `
            <td>${booking.id}</td>
            <td title="${userEmail}">${this.truncateText(userEmail, 20)}</td>
            <td title="${parkingLot}">${this.truncateText(parkingLot, 15)}</td>
            <td>${spaceNumber}</td>
            <td title="${startTime}">${this.formatShortDate(booking.start_time)}</td>
            <td title="${endTime}">${this.formatShortDate(booking.end_time)}</td>
            <td title="${booking.license_plate}">${this.truncateText(booking.license_plate, 10)}</td>
            <td>${statusBadge}</td>
            <td title="${new Date(booking.created_at).toLocaleString()}">${this.formatShortDate(booking.created_at)}</td>
            <td>
                <button class="btn btn-danger btn-sm" onclick="AdminBookings.deleteBooking(${booking.id})" 
                        title="Delete booking">
                    <i class="bi bi-trash"></i>
                </button>
            </td>
        `;
        
        return row;
    },

    // Helper to truncate text
    truncateText(text, maxLength) {
        if (!text) return 'N/A';
        return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
    },

    // Helper to format dates
    formatShortDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
    },

    // Update pagination controls
    updatePagination() {
        const pagination = document.getElementById('bookings-pagination');
        if (!pagination) return;
        
        const totalPages = Math.ceil(this.totalBookings / this.itemsPerPage);
        
        if (totalPages <= 1) {
            pagination.innerHTML = '';
            return;
        }
        
        let paginationHTML = '<nav><ul class="pagination pagination-sm justify-content-center">';
        
        // Previous button
        paginationHTML += `
            <li class="page-item ${this.currentPage === 1 ? 'disabled' : ''}">
                <a class="page-link" href="#" onclick="AdminBookings.goToPage(${this.currentPage - 1}); return false;">Previous</a>
            </li>
        `;
        
        // Page numbers
        const startPage = Math.max(1, this.currentPage - 2);
        const endPage = Math.min(totalPages, this.currentPage + 2);
        
        for (let i = startPage; i <= endPage; i++) {
            paginationHTML += `
                <li class="page-item ${i === this.currentPage ? 'active' : ''}">
                    <a class="page-link" href="#" onclick="AdminBookings.goToPage(${i}); return false;">${i}</a>
                </li>
            `;
        }
        
        // Next button
        paginationHTML += `
            <li class="page-item ${this.currentPage === totalPages ? 'disabled' : ''}">
                <a class="page-link" href="#" onclick="AdminBookings.goToPage(${this.currentPage + 1}); return false;">Next</a>
            </li>
        `;
        
        paginationHTML += '</ul></nav>';
        pagination.innerHTML = paginationHTML;
    },

    // Update results info
    updateResultsInfo() {
        const resultsInfo = document.getElementById('bookings-results-info');
        if (!resultsInfo) return;
        
        const start = (this.currentPage - 1) * this.itemsPerPage + 1;
        const end = Math.min(this.currentPage * this.itemsPerPage, this.totalBookings);
        
        resultsInfo.textContent = `Showing ${start}-${end} of ${this.totalBookings} bookings`;
    },

    // Go to specific page
    goToPage(page) {
        const totalPages = Math.ceil(this.totalBookings / this.itemsPerPage);
        if (page >= 1 && page <= totalPages) {
            this.currentPage = page;
            this.loadBookings();
        }
    },

    // Apply filters
    async applyFilters() {
        // Get filter values from form
        this.currentFilters.user_id = document.getElementById('filter-user')?.value || null;
        this.currentFilters.parking_lot_id = document.getElementById('filter-parking-lot')?.value || null;
        this.currentFilters.start_date = document.getElementById('filter-start-date')?.value || null;
        this.currentFilters.end_date = document.getElementById('filter-end-date')?.value || null;
        this.currentFilters.include_cancelled = document.getElementById('filter-include-cancelled')?.checked ?? true;
        
        // Reset to first page when applying filters
        this.currentPage = 1;
        
        await this.loadBookings();
    },

    // Clear all filters
    async clearFilters() {
        // Reset filter values
        this.currentFilters = {
            user_id: null,
            parking_lot_id: null,
            start_date: null,
            end_date: null,
            include_cancelled: true
        };
        
        // Reset form elements
        const filterForm = document.getElementById('bookings-filter-form');
        if (filterForm) {
            filterForm.reset();
            document.getElementById('filter-include-cancelled').checked = true;
        }
        
        // Reset pagination
        this.currentPage = 1;
        
        await this.loadBookings();
    },

    // Delete booking
    async deleteBooking(bookingId) {
        const confirmed = await AdminNotifications.confirm(
            'Are you sure you want to delete this booking? This action cannot be undone.'
        );
        if (!confirmed) return;
        
        try {
            const response = await AdminAPI.bookings.delete(bookingId);

            if (response.ok) {
                AdminNotifications.showSuccess('Booking deleted successfully');
                await this.loadBookings();
            } else {
                const error = await response.json();
                AdminNotifications.showError(error.detail || 'Failed to delete booking');
            }
        } catch (error) {
            AdminNotifications.handleApiError(error, 'Error deleting booking');
        }
    },

    // Export bookings to Excel
    async exportToExcel() {
        try {
            // Show loading state
            const exportBtn = document.getElementById('export-excel-btn');
            if (exportBtn) {
                exportBtn.disabled = true;
                exportBtn.innerHTML = '<i class="bi bi-download"></i> Exporting...';
            }

            const response = await AdminAPI.bookings.exportExcel(this.currentFilters);

            if (response.ok) {
                // Get filename from Content-Disposition header
                const contentDisposition = response.headers.get('Content-Disposition');
                let filename = 'bookings_export.xlsx';
                if (contentDisposition) {
                    const filenameMatch = contentDisposition.match(/filename="?([^"]*)"?/);
                    if (filenameMatch) {
                        filename = filenameMatch[1];
                    }
                }

                // Download the file
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = filename;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);

                AdminNotifications.showSuccess('Excel file downloaded successfully');
            } else {
                AdminNotifications.showError('Failed to export bookings');
            }
        } catch (error) {
            AdminNotifications.handleApiError(error, 'Error exporting bookings');
        } finally {
            // Reset button state
            const exportBtn = document.getElementById('export-excel-btn');
            if (exportBtn) {
                exportBtn.disabled = false;
                exportBtn.innerHTML = '<i class="bi bi-download"></i> Export Excel';
            }
        }
    },

    // Load filter options
    async loadFilterOptions() {
        try {
            const [usersResponse, parkingLotsResponse] = await Promise.all([
                AdminAPI.bookings.getUsersWithBookings(),
                AdminAPI.bookings.getParkingLotsWithBookings()
            ]);

            if (usersResponse.ok) {
                const users = await usersResponse.json();
                const userSelect = document.getElementById('filter-user');
                if (userSelect) {
                    userSelect.innerHTML = '<option value="">All Users</option>';
                    users.forEach(user => {
                        const option = document.createElement('option');
                        option.value = user.id;
                        option.textContent = user.email;
                        userSelect.appendChild(option);
                    });
                }
            }

            if (parkingLotsResponse.ok) {
                const parkingLots = await parkingLotsResponse.json();
                const lotSelect = document.getElementById('filter-parking-lot');
                if (lotSelect) {
                    lotSelect.innerHTML = '<option value="">All Parking Lots</option>';
                    parkingLots.forEach(lot => {
                        const option = document.createElement('option');
                        option.value = lot.id;
                        option.textContent = lot.name;
                        lotSelect.appendChild(option);
                    });
                }
            }
        } catch (error) {
            console.error('Error loading filter options:', error);
        }
    },

    // Initialize bookings module
    init() {
        console.log('Initializing bookings module...');
        this.setupEventListeners();
        console.log('Bookings module initialized');
    },

    // Setup event listeners
    setupEventListeners() {
        // Filter form
        const filterForm = document.getElementById('bookings-filter-form');
        if (filterForm && !filterForm.hasAttribute('data-bookings-listener')) {
            filterForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.applyFilters();
            });
            filterForm.setAttribute('data-bookings-listener', 'true');
        }

        // Clear filters button
        const clearFiltersBtn = document.getElementById('clear-filters-btn');
        if (clearFiltersBtn && !clearFiltersBtn.hasAttribute('data-bookings-listener')) {
            clearFiltersBtn.addEventListener('click', () => this.clearFilters());
            clearFiltersBtn.setAttribute('data-bookings-listener', 'true');
        }

        // Export Excel button
        const exportBtn = document.getElementById('export-excel-btn');
        if (exportBtn && !exportBtn.hasAttribute('data-bookings-listener')) {
            exportBtn.addEventListener('click', () => this.exportToExcel());
            exportBtn.setAttribute('data-bookings-listener', 'true');
        }

        // Refresh button
        const refreshBtn = document.getElementById('refresh-bookings-btn');
        if (refreshBtn && !refreshBtn.hasAttribute('data-bookings-listener')) {
            refreshBtn.addEventListener('click', () => this.loadBookings());
            refreshBtn.setAttribute('data-bookings-listener', 'true');
        }

        // Items per page selector
        const itemsPerPageSelect = document.getElementById('items-per-page');
        if (itemsPerPageSelect && !itemsPerPageSelect.hasAttribute('data-bookings-listener')) {
            itemsPerPageSelect.addEventListener('change', (e) => {
                this.itemsPerPage = parseInt(e.target.value);
                this.currentPage = 1;
                this.loadBookings();
            });
            itemsPerPageSelect.setAttribute('data-bookings-listener', 'true');
        }
    },

    // Ensure initialization when tab becomes active
    async ensureInitialized() {
        console.log('Ensuring bookings module is properly initialized...');
        this.setupEventListeners();
        
        // Load filter options and bookings when tab is activated
        await this.loadFilterOptions();
        await this.loadBookings();
    }
};

// Export for global access
window.AdminBookings = AdminBookings;

// Initialize when module loads
AdminBookings.init();

console.log('Admin bookings module loaded!');
