/**
 * Booking Manager Web Component
 */
class BookingManager extends HTMLElement {
    constructor() {
        super();
        this.bookings = [];
    }

    connectedCallback() {
        this.render();
        this.setupEventListeners();
        if (window.AdminAPI) {
            this.loadBookings();
        } else {
            document.addEventListener('admin-api-loaded', () => this.loadBookings());
        }
    }

    render() {
        this.innerHTML = `
            <div class="card shadow-sm mt-4">
                <div class="card-header d-flex justify-content-between align-items-center">
                    <h5 class="card-title mb-0">
                        <i class="fas fa-calendar-alt me-2"></i>Booking Management
                    </h5>
                    <div class="btn-group" role="group">
                        <button class="btn btn-light btn-sm" id="refresh-bookings-btn" title="Refresh">
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
                                    <th>User</th>
                                    <th>Parking Space</th>
                                    <th>Start Time</th>
                                    <th>End Time</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody id="booking-list">
                                <!-- Booking rows will be inserted here -->
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
        `;
    }

    setupEventListeners() {
        this.querySelector('#refresh-bookings-btn').addEventListener('click', () => this.loadBookings());
        this.querySelector('#booking-list').addEventListener('click', (event) => this.handleCancelClick(event));
    }

    async loadBookings() {
        this.setLoading(true);
        try {
            const response = await window.AdminAPI.bookings.getAll();
            if (!response.ok) {
                throw new Error('Failed to fetch bookings');
            }
            this.bookings = await response.json();
            this.renderBookingList();
        } catch (error) {
            console.error('Failed to load bookings', error);
            this.querySelector('#booking-list').innerHTML = '<tr><td colspan="6" class="text-danger">Failed to load bookings.</td></tr>';
        } finally {
            this.setLoading(false);
        }
    }

    renderBookingList() {
        const bookingListBody = this.querySelector('#booking-list');
        if (this.bookings.length === 0) {
            bookingListBody.innerHTML = '<tr><td colspan="6" class="text-center">No bookings found.</td></tr>';
            return;
        }

        bookingListBody.innerHTML = this.bookings.map(booking => `
            <tr>
                <td>${booking.id}</td>
                <td>${booking.user ? booking.user.email : 'N/A'}</td>
                <td>${booking.space ? booking.space.space_number : 'N/A'}</td>
                <td>${new Date(booking.start_time).toLocaleString()}</td>
                <td>${new Date(booking.end_time).toLocaleString()}</td>
                <td>
                    <button class="btn btn-sm btn-outline-danger" data-booking-id="${booking.id}">Cancel</button>
                </td>
            </tr>
        `).join('');
    }

    async handleCancelClick(event) {
        if (event.target.classList.contains('btn-outline-danger')) {
            const bookingId = event.target.dataset.bookingId;
            if (!bookingId) return;

            if (confirm('Are you sure you want to cancel this booking?')) {
                this.setLoading(true);
                try {
                    const response = await window.AdminAPI.bookings.delete(bookingId);
                    if (!response.ok) {
                        throw new Error('Failed to cancel booking');
                    }
                    await this.loadBookings();
                } catch (error) {
                    console.error('Failed to cancel booking', error);
                    // You might want to show a more user-friendly error message
                } finally {
                    this.setLoading(false);
                }
            }
        }
    }

    setLoading(loading) {
        const overlay = this.querySelector('#loading-overlay');
        overlay.classList.toggle('d-none', !loading);
    }
}

customElements.define('booking-manager', BookingManager);
