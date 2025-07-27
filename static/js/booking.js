/* Booking module for user interface */

// Canvas and booking variables
let userCanvas = null;
let currentParkingLot = null;

// Cookie utility functions
const CookieManager = {
    set: function(name, value, days = 30) {
        const expires = new Date();
        expires.setTime(expires.getTime() + (days * 24 * 60 * 60 * 1000));
        document.cookie = `${name}=${encodeURIComponent(value)};expires=${expires.toUTCString()};path=/;SameSite=Lax`;
    },
    
    get: function(name) {
        const nameEQ = name + "=";
        const ca = document.cookie.split(';');
        for(let i = 0; i < ca.length; i++) {
            let c = ca[i];
            while (c.charAt(0) === ' ') c = c.substring(1, c.length);
            if (c.indexOf(nameEQ) === 0) {
                return decodeURIComponent(c.substring(nameEQ.length, c.length));
            }
        }
        return null;
    },
    
    delete: function(name) {
        document.cookie = `${name}=;expires=Thu, 01 Jan 1970 00:00:00 UTC;path=/`;
    }
};

// Cookie keys
const COOKIE_KEYS = {
    LAST_PARKING_LOT: 'booking_last_parking_lot'
};

// DOM elements
const userView = document.getElementById('user-view');
const userBookingView = document.getElementById('user-booking-view');
const userParkingLotsList = document.getElementById('user-parking-lots-list');
const availabilityStartTimeInput = document.getElementById('availability-start-time');
const availabilityEndTimeInput = document.getElementById('availability-end-time');
const datePrevBtn = document.getElementById('date-prev-btn');
const dateNextBtn = document.getElementById('date-next-btn');
const userLotNameHeader = document.getElementById('user-lot-name-header');
const bookingsTableBody = document.getElementById('bookings-table-body');
const showAllBookingsToggle = document.getElementById('show-all-bookings-toggle');

// Modal elements
const bookingModal = new bootstrap.Modal(document.getElementById('booking-modal'));
const bookingModalLabel = document.getElementById('bookingModalLabel');
const createBookingForm = document.getElementById('create-booking-form');
const selectedSpaceIdInput = document.getElementById('selected-space-id');
const licensePlateInput = document.getElementById('license-plate');
const licensePlateDropdown = document.getElementById('license-plate-dropdown');

// Autocomplete variables
let userLicensePlates = [];
let currentAutocompleteIndex = -1;

// Initialize booking functionality
function initBooking() {
    // Initialize canvas
    userCanvas = new fabric.Canvas('user-canvas');
    
    // Setup mobile touch interactions
    setupMobileTouchInteractions();
    
    // Setup event listeners
    if (createBookingForm) {
        createBookingForm.addEventListener('submit', handleCreateBooking);
    }
    
    if (showAllBookingsToggle) {
        showAllBookingsToggle.addEventListener('change', fetchBookings);
    }
    
    if (availabilityStartTimeInput) {
        availabilityStartTimeInput.addEventListener('change', handleAvailabilityChange);
    }
    
    if (availabilityEndTimeInput) {
        availabilityEndTimeInput.addEventListener('change', handleAvailabilityChange);
    }

    // Setup date navigation
    if (datePrevBtn) {
        datePrevBtn.addEventListener('click', () => changeBookingDate(-1));
    }
    
    if (dateNextBtn) {
        dateNextBtn.addEventListener('click', () => changeBookingDate(1));
    }

    // Setup license plate autocomplete
    initLicensePlateAutocomplete();

    // Canvas click handler for booking
    userCanvas.on('mouse:down', handleCanvasClick);
}

// Update view function called from auth module
function updateView() {
    if (userView) userView.style.display = 'block';
    if (userBookingView) userBookingView.style.display = 'block';
    fetchBookings();
    fetchParkingLots(userParkingLotsList, selectParkingLotForUser);
}

// Fetch parking lots for dropdown
async function fetchParkingLots(selectElement, onSelect) {
    if (!selectElement) return;
    
    const response = await window.auth.makeAuthenticatedRequest('/api/parking-lots/');
    if (response.status === 401) {
        return;
    }
    
    const lots = await response.json();
    selectElement.innerHTML = '';
    let firstLot = null;

    const lotsById = {};
    for (const lot of lots) {
        if (!firstLot) firstLot = lot;
        lotsById[lot.id] = lot;
        const option = document.createElement('option');
        option.textContent = lot.name;
        option.value = lot.id;
        selectElement.appendChild(option);
    }

    if (selectElement.handleChange) {
        selectElement.removeEventListener('change', selectElement.handleChange);
    }

    selectElement.handleChange = (event) => {
        const selectedLotId = event.target.value;
        const selectedLot = lotsById[selectedLotId];
        if (selectedLot) {
            onSelect(selectedLot);
        }
    };
    selectElement.addEventListener('change', selectElement.handleChange);

    // Check for saved parking lot preference
    const savedLotId = CookieManager.get(COOKIE_KEYS.LAST_PARKING_LOT);
    let lotToSelect = firstLot;
    
    if (savedLotId && lotsById[savedLotId]) {
        // Use saved parking lot if it exists
        lotToSelect = lotsById[savedLotId];
        console.log(`Restored last parking lot: ${lotToSelect.name}`);
    } else if (savedLotId) {
        // Clean up invalid cookie if the lot no longer exists
        CookieManager.delete(COOKIE_KEYS.LAST_PARKING_LOT);
        console.log('Removed invalid parking lot preference');
    }

    if (lotToSelect) {
        selectElement.value = lotToSelect.id;
        onSelect(lotToSelect);
    }
}

// Fetch user bookings
async function fetchBookings() {
    if (!bookingsTableBody) return;
    
    const bookingsResponse = await window.auth.makeAuthenticatedRequest('/api/bookings/');
    const bookings = await bookingsResponse.json();
    bookingsTableBody.innerHTML = '';

    const mobileCardsContainer = document.getElementById('bookings-mobile-cards');
    if (mobileCardsContainer) {
        mobileCardsContainer.innerHTML = '';
    }

    const showAll = showAllBookingsToggle ? showAllBookingsToggle.checked : false;

    for (const booking of bookings) {
        const isPast = new Date(booking.end_time) < new Date();
        const isActive = !booking.is_cancelled && !isPast;

        if (showAll || isActive) {
            const row = document.createElement('tr');
            let statusText = 'Active';
            let statusClass = 'status-active';
            if (booking.is_cancelled) {
                statusText = 'Cancelled';
                statusClass = 'status-cancelled';
            } else if (isPast) {
                statusText = 'Past';
                statusClass = 'status-past';
            }

            row.innerHTML = `
                <td>${booking.space.space_number} (${booking.space.parking_lot.name})</td>
                <td>${new Date(booking.start_time).toLocaleString([], {
                    year: 'numeric',
                    month: '2-digit',
                    day: '2-digit',
                    hour: '2-digit',
                    minute: '2-digit'
                })}</td>
                <td>${new Date(booking.end_time).toLocaleString([], {
                    year: 'numeric',
                    month: '2-digit',
                    day: '2-digit',
                    hour: '2-digit',
                    minute: '2-digit'
                })}</td>
                <td>${booking.license_plate}</td>
                <td><span class="status-badge ${statusClass}">${statusText}</span></td>
                <td>
                    ${isActive ? `<button class="btn btn-danger btn-sm" onclick="cancelBooking(${booking.id})">Cancel</button>` : ''}
                </td>
            `;
            bookingsTableBody.appendChild(row);

            // Create mobile card if container exists
            if (mobileCardsContainer) {
                const mobileCard = document.createElement('div');
                mobileCard.className = 'mobile-card';
                mobileCard.innerHTML = `
                    <div class="mobile-card-header">
                        ${booking.space.space_number} - ${booking.space.parking_lot.name}
                    </div>
                    <div class="mobile-card-body">
                        <div class="mobile-card-row">
                            <span class="mobile-card-label">Start:</span>
                            <span class="mobile-card-value">${new Date(booking.start_time).toLocaleString([], {
                                year: 'numeric',
                                month: '2-digit',
                                day: '2-digit',
                                hour: '2-digit',
                                minute: '2-digit'
                            })}</span>
                        </div>
                        <div class="mobile-card-row">
                            <span class="mobile-card-label">End:</span>
                            <span class="mobile-card-value">${new Date(booking.end_time).toLocaleString([], {
                                year: 'numeric',
                                month: '2-digit',
                                day: '2-digit',
                                hour: '2-digit',
                                minute: '2-digit'
                            })}</span>
                        </div>
                        <div class="mobile-card-row">
                            <span class="mobile-card-label">License Plate:</span>
                            <span class="mobile-card-value">${booking.license_plate}</span>
                        </div>
                        <div class="mobile-card-row">
                            <span class="mobile-card-label">Status:</span>
                            <span class="mobile-card-value"><span class="status-badge ${statusClass}">${statusText}</span></span>
                        </div>
                        ${isActive ? `
                        <div class="mobile-card-row">
                            <button class="btn btn-danger btn-sm w-100 mt-2" onclick="cancelBooking(${booking.id})">Cancel Booking</button>
                        </div>
                        ` : ''}
                    </div>
                `;
                mobileCardsContainer.appendChild(mobileCard);
            }
        }
    }
}

// Select parking lot for user view
async function selectParkingLotForUser(lot) {
    currentParkingLot = lot;
    
    // Save the parking lot choice to cookie
    CookieManager.set(COOKIE_KEYS.LAST_PARKING_LOT, lot.id.toString());
    console.log(`Saved parking lot preference: ${lot.name} (ID: ${lot.id})`);
    
    if (userLotNameHeader) {
        userLotNameHeader.textContent = lot.name;
    }
    
    if (userCanvas && lot.image) {
        userCanvas.setBackgroundImage(lot.image, () => {
            if (userCanvas.backgroundImage) {
                userCanvas.originalWidth = userCanvas.backgroundImage.width;
                userCanvas.originalHeight = userCanvas.backgroundImage.height;
            }
            resizeCanvas(userCanvas, document.querySelector('#user-booking-view .canvas-container'));
        });
    }

    setSmartBookingTimes();
    await refreshParkingSpaceAvailability(lot.id);
    if (userCanvas) {
        resizeCanvas(userCanvas, document.querySelector('#user-booking-view .canvas-container'));
    }
}

// Set smart default booking times
function setSmartBookingTimes() {
    if (!availabilityStartTimeInput || !availabilityEndTimeInput) return;
    
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    
    // Set smart default times for today
    updateTimesForSelectedDate(today);
}

// Update times based on selected date
function updateTimesForSelectedDate(targetDate = null) {
    if (!availabilityStartTimeInput || !availabilityEndTimeInput) return;
    
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    
    // If no target date provided, get it from current start time input
    let selectedDate;
    if (targetDate) {
        selectedDate = new Date(targetDate);
    } else if (availabilityStartTimeInput.value) {
        selectedDate = new Date(availabilityStartTimeInput.value);
        selectedDate = new Date(selectedDate.getFullYear(), selectedDate.getMonth(), selectedDate.getDate());
    } else {
        selectedDate = today;
    }
    
    let startTime, endTime;
    
    if (selectedDate.getTime() === today.getTime()) {
        // Today: start from now (rounded to next 15 min), end at 16:00
        startTime = new Date(now);
        startTime.setMinutes(Math.ceil(startTime.getMinutes() / 15) * 15);
        startTime.setSeconds(0);
        
        endTime = new Date(selectedDate);
        endTime.setHours(16, 0, 0, 0);
        
        // If current time is after 16:00, set end time to start time + 2 hours
        if (startTime >= endTime) {
            endTime = new Date(startTime);
            endTime.setHours(endTime.getHours() + 2);
        }
    } else if (selectedDate > today) {
        // Future days: start at 8:00, end at 16:00
        startTime = new Date(selectedDate);
        startTime.setHours(8, 0, 0, 0);
        
        endTime = new Date(selectedDate);
        endTime.setHours(16, 0, 0, 0);
    } else {
        // Past dates: allow viewing, set typical day hours (8:00 to 16:00)
        startTime = new Date(selectedDate);
        startTime.setHours(8, 0, 0, 0);
        
        endTime = new Date(selectedDate);
        endTime.setHours(16, 0, 0, 0);
    }
    
    availabilityStartTimeInput.value = formatDateTimeLocal(startTime);
    availabilityEndTimeInput.value = formatDateTimeLocal(endTime);
}

// Change booking date by days (positive for future, negative for past)
function changeBookingDate(days) {
    if (!availabilityStartTimeInput) return;
    
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    
    // Get current date from start time input, or use today as default
    let currentDate;
    if (availabilityStartTimeInput.value) {
        currentDate = new Date(availabilityStartTimeInput.value);
        currentDate = new Date(currentDate.getFullYear(), currentDate.getMonth(), currentDate.getDate());
    } else {
        currentDate = today;
    }
    
    const newDate = new Date(currentDate);
    newDate.setDate(newDate.getDate() + days);
    
    // Allow navigation to any date (past, present, or future)
    updateTimesForSelectedDate(newDate);
    
    if (currentParkingLot) {
        refreshParkingSpaceAvailability(currentParkingLot.id);
    }
}

// Format date for date input (YYYY-MM-DD)
function formatDateOnly(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

// Format date for datetime-local input
function formatDateTimeLocal(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    return `${year}-${month}-${day}T${hours}:${minutes}`;
}

// Handle availability time change
async function handleAvailabilityChange() {
    if (currentParkingLot) {
        await refreshParkingSpaceAvailability(currentParkingLot.id);
    }
}

// Refresh parking space availability
async function refreshParkingSpaceAvailability(lotId) {
    if (!availabilityStartTimeInput || !availabilityEndTimeInput) {
        await fetchParkingSpaces(lotId, userCanvas, false, [], {});
        return;
    }

    const start = availabilityStartTimeInput.value;
    const end = availabilityEndTimeInput.value;
    if (!start || !end) {
        await fetchParkingSpaces(lotId, userCanvas, false, [], {});
        return;
    }

    const startDateTime = new Date(start).toISOString();
    const endDateTime = new Date(end).toISOString();

    const availabilityResponse = await window.auth.makeAuthenticatedRequest(
        `/api/parking-lots/${lotId}/spaces/availability?start_time=${encodeURIComponent(startDateTime)}&end_time=${encodeURIComponent(endDateTime)}`
    );
    
    if (availabilityResponse.ok) {
        const availabilityData = await availabilityResponse.json();
        await fetchParkingSpaces(
            lotId, 
            userCanvas, 
            false, 
            availabilityData.booked_space_ids || [], 
            availabilityData.space_license_plates || {}
        );
    } else {
        await fetchParkingSpaces(lotId, userCanvas, false, [], {});
    }
}

// Fetch parking spaces and render on canvas
async function fetchParkingSpaces(lotId, canvasInstance, isAdmin, bookedSpaceIds = [], spaceLicensePlates = {}) {
    if (!canvasInstance) return;
    
    const response = await window.auth.makeAuthenticatedRequest(`/api/parking-lots/${lotId}/spaces/`);
    const spaces = await response.json();
    canvasInstance.remove(...canvasInstance.getObjects());
    
    for (const space of spaces) {
        const isBooked = bookedSpaceIds.includes(space.id);
        const licensePlate = spaceLicensePlates[space.id];
        
        const rect = new fabric.Rect({
            width: space.width,
            height: space.height,
            fill: isBooked ? 'red' : space.color,
            stroke: 'black',
            strokeWidth: 0,
        });

        // Create space number text (always centered)
        const spaceText = new fabric.Text(space.space_number, {
            left: space.width / 2,
            top: space.height / 2,
            fontSize: 18,
            fill: 'black',
            originX: 'center',
            originY: 'center',
            fontWeight: 'bold'
        });

        const groupObjects = [rect, spaceText];

        // Note: License plate text is no longer displayed on the space
        // Click on booked spaces to view booking details

        const group = new fabric.Group(groupObjects, {
            left: space.position_x,
            top: space.position_y,
            selectable: isAdmin,
            hasControls: isAdmin,
            hasBorders: isAdmin,
            data: {
                id: space.id,
                space_number: space.space_number,
                is_booked: isBooked,
                license_plate: licensePlate || null
            }
        });
        canvasInstance.add(group);
    }
}

// Handle canvas click for booking
async function handleCanvasClick(e) {
    if (e.target && e.target.data.id) {
        if (e.target.data.is_booked) {
            // Show booking details for booked space
            await showBookingDetails(e.target.data.id, e.target.data.space_number);
        } else {
            // Handle booking for available space
            // Check if trying to book for a past date
            if (availabilityStartTimeInput && availabilityStartTimeInput.value) {
                const now = new Date();
                const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
                const bookingDate = new Date(availabilityStartTimeInput.value);
                const bookingDateOnly = new Date(bookingDate.getFullYear(), bookingDate.getMonth(), bookingDate.getDate());
                
                if (bookingDateOnly < today) {
                    showErrorNotification('Cannot create bookings for past dates. Please select today or a future date to make a booking.');
                    return; // Don't open the modal
                }
            }
            
            selectedSpaceIdInput.value = e.target.data.id;
            bookingModalLabel.textContent = `Book Space: ${e.target.data.space_number}`;
            bookingModal.show();
        }
    }
}

// Handle booking form submission
async function handleCreateBooking(event) {
    event.preventDefault();
    const space_id = selectedSpaceIdInput.value;
    const license_plate = licensePlateInput.value;
    const start_time = availabilityStartTimeInput.value;
    const end_time = availabilityEndTimeInput.value;

    // Check if booking is for a past date
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const bookingDate = new Date(start_time);
    const bookingDateOnly = new Date(bookingDate.getFullYear(), bookingDate.getMonth(), bookingDate.getDate());
    
    if (bookingDateOnly < today) {
        showErrorMessage('Cannot create bookings for past dates. Please select today or a future date.');
        return;
    }

    const startDateTime = new Date(start_time).toISOString();
    const endDateTime = new Date(end_time).toISOString();

    const response = await window.auth.makeAuthenticatedRequest('/api/bookings/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            space_id: parseInt(space_id),
            license_plate,
            start_time: startDateTime,
            end_time: endDateTime
        }),
    });

    if (response.ok) {
        licensePlateInput.value = '';
        bookingModal.hide();
        await fetchBookings();
        const lotId = parseInt(userParkingLotsList.value);
        if (lotId) {
            await refreshParkingSpaceAvailability(lotId);
        }
        showSuccessMessage('Booking created successfully!');
    } else {
        const error = await response.json();
        // Close the modal and clear the input on error
        licensePlateInput.value = '';
        bookingModal.hide();
        // Show floating error notification that's always visible
        showErrorNotification(`Booking failed: ${error.detail}`);
    }
}

// Show booking details for a booked space
async function showBookingDetails(spaceId, spaceNumber) {
    const modal = new bootstrap.Modal(document.getElementById('booking-details-modal'));
    const loadingDiv = document.getElementById('booking-detail-loading');
    const errorDiv = document.getElementById('booking-detail-error');
    
    // Reset modal content
    document.getElementById('booking-detail-space').textContent = spaceNumber;
    document.getElementById('booking-detail-user').textContent = '-';
    document.getElementById('booking-detail-license-plate').textContent = '-';
    document.getElementById('booking-detail-start-time').textContent = '-';
    document.getElementById('booking-detail-end-time').textContent = '-';
    
    // Show loading and hide error
    loadingDiv.style.display = 'block';
    errorDiv.style.display = 'none';
    
    // Show modal
    modal.show();
    
    try {
        // Get current time range for booking search
        const start = availabilityStartTimeInput?.value;
        const end = availabilityEndTimeInput?.value;
        
        if (!start || !end) {
            throw new Error('No time range specified');
        }
        
        const startDateTime = new Date(start).toISOString();
        const endDateTime = new Date(end).toISOString();
        
        // Fetch all bookings in the time range using admin endpoint
        const response = await window.auth.makeAuthenticatedRequest(
            `/api/bookings/all?start_date=${start.split('T')[0]}&end_date=${end.split('T')[0]}`
        );
        
        if (!response.ok) {
            throw new Error('Failed to fetch booking details');
        }
        
        const bookings = await response.json();
        
        // Find booking for this space that overlaps with the selected time range
        const selectedStart = new Date(startDateTime);
        const selectedEnd = new Date(endDateTime);
        
        const relevantBooking = bookings.find(booking => 
            booking.space.id === spaceId && 
            !booking.is_cancelled &&
            new Date(booking.start_time) < selectedEnd &&
            new Date(booking.end_time) > selectedStart
        );
        
        if (relevantBooking) {
            // Populate modal with booking details
            document.getElementById('booking-detail-user').textContent = relevantBooking.user.email;
            document.getElementById('booking-detail-license-plate').textContent = relevantBooking.license_plate;
            document.getElementById('booking-detail-start-time').textContent = new Date(relevantBooking.start_time).toLocaleString([], {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit'
            });
            document.getElementById('booking-detail-end-time').textContent = new Date(relevantBooking.end_time).toLocaleString([], {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit'
            });
        } else {
            // No booking found for the selected time range
            document.getElementById('booking-detail-user').textContent = 'Booking not found';
            document.getElementById('booking-detail-license-plate').textContent = '-';
        }
        
        // Hide loading
        loadingDiv.style.display = 'none';
        
    } catch (error) {
        console.error('Error fetching booking details:', error);
        
        // Hide loading and show error
        loadingDiv.style.display = 'none';
        errorDiv.style.display = 'block';
    }
}

// Cancel booking
async function cancelBooking(bookingId) {
    if (confirm('Are you sure you want to cancel this booking?')) {
        await window.auth.makeAuthenticatedRequest(`/api/bookings/${bookingId}/cancel`, {
            method: 'PUT'
        });
        await fetchBookings();
    }
}

// Resize canvas for responsiveness with device-aware scaling limits
function resizeCanvas(canvas, container) {
    if (!canvas || !container) return;
    
    const containerWidth = container.clientWidth;
    if (containerWidth > 0 && canvas.originalWidth) {
        // Calculate initial scale factor based on container width
        let scaleFactor = Math.min(1, (containerWidth - 20) / canvas.originalWidth);
        
        // Apply device-aware scaling limits
        const isMobile = window.innerWidth <= 768;
        
        if (isMobile) {
            // Mobile limits: min 40%, max 100% of original size
            scaleFactor = Math.max(0.4, Math.min(1.0, scaleFactor));
        } else {
            // Desktop limits: min 20%, max 150% of original size
            scaleFactor = Math.max(0.2, Math.min(1.5, scaleFactor));
        }
        
        const canvasWidth = canvas.originalWidth * scaleFactor;
        const canvasHeight = canvas.originalHeight * scaleFactor;

        canvas.setDimensions({ width: canvasWidth, height: canvasHeight });
        if (canvas.backgroundImage) {
            canvas.backgroundImage.scaleToWidth(canvasWidth);
            canvas.backgroundImage.scaleToHeight(canvasHeight);
        }
        canvas.setZoom(scaleFactor);
        canvas.requestRenderAll();
    }
}

// Enhanced resize function that forces background image refresh
function resizeCanvasWithBackgroundRefresh(canvas, container) {
    if (!canvas || !container) return;
    
    // Store the background image URL if it exists
    let backgroundImageUrl = null;
    if (canvas.backgroundImage && canvas.backgroundImage._element && canvas.backgroundImage._element.src) {
        backgroundImageUrl = canvas.backgroundImage._element.src;
    }
    
    // Clear the background image temporarily
    canvas.setBackgroundImage(null, () => {
        // If we had a background image, reload it with proper scaling
        if (backgroundImageUrl) {
            canvas.setBackgroundImage(backgroundImageUrl, () => {
                if (canvas.backgroundImage) {
                    canvas.originalWidth = canvas.backgroundImage.width;
                    canvas.originalHeight = canvas.backgroundImage.height;
                }
                // Now resize with the refreshed background
                resizeCanvas(canvas, container);
            });
        } else {
            // No background image, just resize normally
            resizeCanvas(canvas, container);
        }
    });
}

// Debounced orientation change handler
let orientationChangeTimeout = null;
function handleOrientationChange() {
    // Clear any existing timeout
    if (orientationChangeTimeout) {
        clearTimeout(orientationChangeTimeout);
    }
    
    // Wait for orientation change to complete
    orientationChangeTimeout = setTimeout(() => {
        const userCanvasContainer = document.querySelector('#user-booking-view .canvas-container');
        if (userCanvasContainer && userBookingView && userBookingView.style.display !== 'none' && userCanvas) {
            resizeCanvasWithBackgroundRefresh(userCanvas, userCanvasContainer);
        }
    }, 250); // Wait 250ms for orientation change to complete
}

// Setup responsive canvases
function setupResponsiveCanvases() {
    const userCanvasContainer = document.querySelector('#user-booking-view .canvas-container');
    if (userCanvasContainer && userCanvas) {
        resizeCanvas(userCanvas, userCanvasContainer);
    }
    
    // Standard resize event handler
    window.addEventListener('resize', () => {
        if (userCanvasContainer && userBookingView && userBookingView.style.display !== 'none') {
            resizeCanvas(userCanvas, userCanvasContainer);
        }
    });
    
    // Mobile orientation change handlers
    // Modern browsers
    if (screen.orientation) {
        screen.orientation.addEventListener('change', handleOrientationChange);
    }
    
    // Legacy browsers
    window.addEventListener('orientationchange', handleOrientationChange);
    
    // Additional mobile detection for better compatibility
    window.addEventListener('resize', () => {
        // Detect if this might be an orientation change on mobile
        if (window.innerHeight !== window.innerWidth) {
            const isMobile = window.innerWidth <= 768 || window.innerHeight <= 768;
            if (isMobile) {
                handleOrientationChange();
            }
        }
    });
}

// License Plate Autocomplete Functions
async function initLicensePlateAutocomplete() {
    if (!licensePlateInput || !licensePlateDropdown) return;
    
    // Fetch user's license plates when modal is shown
    document.getElementById('booking-modal').addEventListener('shown.bs.modal', async () => {
        await fetchUserLicensePlates();
        licensePlateInput.focus();
    });

    // Input event for filtering
    licensePlateInput.addEventListener('input', handleLicensePlateInput);
    
    // Focus event to show dropdown if there are suggestions
    licensePlateInput.addEventListener('focus', () => {
        if (userLicensePlates.length > 0) {
            showAutocompleteDropdown(licensePlateInput.value);
        }
    });
    
    // Blur event to hide dropdown (with delay to allow clicking)
    licensePlateInput.addEventListener('blur', () => {
        setTimeout(() => hideAutocompleteDropdown(), 200);
    });
    
    // Keyboard navigation
    licensePlateInput.addEventListener('keydown', handleLicensePlateKeydown);
    
    // Hide dropdown when modal is hidden
    document.getElementById('booking-modal').addEventListener('hidden.bs.modal', () => {
        hideAutocompleteDropdown();
        licensePlateInput.value = '';
    });
}

async function fetchUserLicensePlates() {
    try {
        const response = await window.auth.makeAuthenticatedRequest('/api/users/me/license-plates');
        if (response.ok) {
            userLicensePlates = await response.json();
        } else {
            userLicensePlates = [];
        }
    } catch (error) {
        console.error('Failed to fetch license plates:', error);
        userLicensePlates = [];
    }
}

function handleLicensePlateInput(event) {
    const value = event.target.value;
    showAutocompleteDropdown(value);
}

function handleLicensePlateKeydown(event) {
    const items = licensePlateDropdown.querySelectorAll('.autocomplete-item');
    
    switch (event.key) {
        case 'ArrowDown':
            event.preventDefault();
            currentAutocompleteIndex = Math.min(currentAutocompleteIndex + 1, items.length - 1);
            updateAutocompleteHighlight(items);
            break;
            
        case 'ArrowUp':
            event.preventDefault();
            currentAutocompleteIndex = Math.max(currentAutocompleteIndex - 1, -1);
            updateAutocompleteHighlight(items);
            break;
            
        case 'Enter':
            event.preventDefault();
            if (currentAutocompleteIndex >= 0 && items[currentAutocompleteIndex]) {
                selectAutocompleteItem(items[currentAutocompleteIndex].textContent);
            }
            break;
            
        case 'Escape':
            hideAutocompleteDropdown();
            break;
    }
}

function showAutocompleteDropdown(filterValue) {
    if (!licensePlateDropdown || userLicensePlates.length === 0) return;
    
    const filteredPlates = userLicensePlates.filter(plate => 
        plate.toLowerCase().includes(filterValue.toLowerCase())
    );
    
    licensePlateDropdown.innerHTML = '';
    currentAutocompleteIndex = -1;
    
    if (filteredPlates.length === 0) {
        if (filterValue.trim() === '') {
            // Show all plates if no filter
            showAllLicensePlates();
        } else {
            hideAutocompleteDropdown();
        }
        return;
    }
    
    filteredPlates.forEach(plate => {
        const item = document.createElement('div');
        item.className = 'autocomplete-item';
        item.textContent = plate;
        item.addEventListener('click', () => selectAutocompleteItem(plate));
        licensePlateDropdown.appendChild(item);
    });
    
    licensePlateDropdown.classList.add('show');
}

function showAllLicensePlates() {
    if (!licensePlateDropdown || userLicensePlates.length === 0) return;
    
    licensePlateDropdown.innerHTML = '';
    currentAutocompleteIndex = -1;
    
    userLicensePlates.forEach(plate => {
        const item = document.createElement('div');
        item.className = 'autocomplete-item';
        item.textContent = plate;
        item.addEventListener('click', () => selectAutocompleteItem(plate));
        licensePlateDropdown.appendChild(item);
    });
    
    licensePlateDropdown.classList.add('show');
}

function hideAutocompleteDropdown() {
    if (licensePlateDropdown) {
        licensePlateDropdown.classList.remove('show');
        currentAutocompleteIndex = -1;
    }
}

function selectAutocompleteItem(plate) {
    if (licensePlateInput) {
        licensePlateInput.value = plate;
        hideAutocompleteDropdown();
        licensePlateInput.focus();
    }
}

function updateAutocompleteHighlight(items) {
    items.forEach((item, index) => {
        if (index === currentAutocompleteIndex) {
            item.classList.add('highlighted');
        } else {
            item.classList.remove('highlighted');
        }
    });
}

// Mobile Touch Interactions
function setupMobileTouchInteractions() {
    if (!userCanvas) return;
    
    // Check if device supports touch
    const isTouchDevice = 'ontouchstart' in window || navigator.maxTouchPoints > 0 || navigator.msMaxTouchPoints > 0;
    const isMobile = window.innerWidth <= 768;
    
    if (!isTouchDevice || !isMobile) return;
    
    // Variables for touch interactions
    let isPanning = false;
    let lastPanPoint = null;
    let lastDistance = 0;
    let isZooming = false;
    let touchStartTime = 0;
    let touchStartPoint = null;
    let activeTouches = [];
    
    // Minimum and maximum zoom levels
    const minZoom = 0.2;
    const maxZoom = 3.0;
    
    // Helper function to get touch distance for pinch gestures
    function getTouchDistance(touches) {
        const dx = touches[0].clientX - touches[1].clientX;
        const dy = touches[0].clientY - touches[1].clientY;
        return Math.sqrt(dx * dx + dy * dy);
    }
    
    // Helper function to get touch center point for pinch gestures
    function getTouchCenter(touches) {
        return {
            x: (touches[0].clientX + touches[1].clientX) / 2,
            y: (touches[0].clientY + touches[1].clientY) / 2
        };
    }
    
    // Convert screen coordinates to canvas coordinates
    function getCanvasPoint(screenX, screenY) {
        const rect = userCanvas.upperCanvasEl.getBoundingClientRect();
        return new fabric.Point(screenX - rect.left, screenY - rect.top);
    }
    
    // Touch start handler
    userCanvas.upperCanvasEl.addEventListener('touchstart', function(e) {
        e.preventDefault();
        e.stopPropagation();
        
        const touches = e.touches;
        touchStartTime = Date.now();
        activeTouches = Array.from(touches);
        
        if (touches.length === 1) {
            // Single touch - potential pan or tap
            isPanning = false;
            isZooming = false;
            touchStartPoint = getCanvasPoint(touches[0].clientX, touches[0].clientY);
            lastPanPoint = { x: touches[0].clientX, y: touches[0].clientY };
        } else if (touches.length === 2) {
            // Two touches - pinch zoom
            isZooming = true;
            isPanning = false;
            lastDistance = getTouchDistance(touches);
        }
    }, { passive: false });
    
    // Touch move handler
    userCanvas.upperCanvasEl.addEventListener('touchmove', function(e) {
        e.preventDefault();
        e.stopPropagation();
        
        const touches = e.touches;
        
        if (touches.length === 1 && !isZooming) {
            // Single touch pan
            if (lastPanPoint) {
                const currentPoint = { x: touches[0].clientX, y: touches[0].clientY };
                const deltaX = currentPoint.x - lastPanPoint.x;
                const deltaY = currentPoint.y - lastPanPoint.y;
                
                // Only start panning if moved enough distance
                if (!isPanning && (Math.abs(deltaX) > 10 || Math.abs(deltaY) > 10)) {
                    isPanning = true;
                }
                
                if (isPanning) {
                    // Pan the canvas
                    const vpt = userCanvas.viewportTransform.slice();
                    vpt[4] += deltaX;
                    vpt[5] += deltaY;
                    userCanvas.setViewportTransform(vpt);
                    userCanvas.requestRenderAll();
                }
                
                lastPanPoint = currentPoint;
            }
        } else if (touches.length === 2) {
            // Two touch pinch zoom
            const currentDistance = getTouchDistance(touches);
            const center = getTouchCenter(touches);
            const canvasCenter = getCanvasPoint(center.x, center.y);
            
            if (lastDistance > 0) {
                let scaleFactor = currentDistance / lastDistance;
                const currentZoom = userCanvas.getZoom();
                let newZoom = currentZoom * scaleFactor;
                
                // Apply zoom limits
                newZoom = Math.max(minZoom, Math.min(maxZoom, newZoom));
                scaleFactor = newZoom / currentZoom;
                
                if (scaleFactor !== 1) {
                    // Zoom towards the pinch center
                    userCanvas.zoomToPoint(canvasCenter, newZoom);
                    userCanvas.requestRenderAll();
                }
            }
            
            lastDistance = currentDistance;
        }
    }, { passive: false });
    
    // Touch end handler
    userCanvas.upperCanvasEl.addEventListener('touchend', function(e) {
        e.preventDefault();
        e.stopPropagation();
        
        const touchEndTime = Date.now();
        const touchDuration = touchEndTime - touchStartTime;
        
        // If it was a quick tap (not a pan or zoom), treat it as a click
        if (!isPanning && !isZooming && touchDuration < 300 && touchStartPoint && e.touches.length === 0) {
            // Find the target at the touch point
            const pointer = userCanvas.getPointer({ clientX: touchStartPoint.x, clientY: touchStartPoint.y });
            const target = userCanvas.findTarget({ clientX: touchStartPoint.x, clientY: touchStartPoint.y });
            
            if (target && target.data && target.data.id) {
                // Trigger either booking modal or booking details based on space status
                setTimeout(() => {
                    handleCanvasClick({ target: target });
                }, 50); // Small delay to ensure touch event is complete
            }
        }
        
        // Reset state when all touches are gone
        if (e.touches.length === 0) {
            isPanning = false;
            isZooming = false;
            lastPanPoint = null;
            lastDistance = 0;
            touchStartPoint = null;
            activeTouches = [];
        }
    }, { passive: false });
    
    // Add double-tap to reset zoom
    let lastTap = 0;
    userCanvas.upperCanvasEl.addEventListener('touchend', function(e) {
        if (e.touches.length === 0) {  // Only on final touch release
            const currentTime = new Date().getTime();
            const tapLength = currentTime - lastTap;
            
            if (tapLength < 500 && tapLength > 0) {
                // Double tap detected - reset zoom and position
                e.preventDefault();
                resetCanvasViewport();
            }
            
            lastTap = currentTime;
        }
    }, { passive: false });
    
    // Function to reset canvas viewport
    function resetCanvasViewport() {
        if (!userCanvas) return;
        
        // Reset zoom and pan to fit the canvas in the container
        const container = document.querySelector('#user-booking-view .canvas-container');
        if (container && userCanvas.originalWidth && userCanvas.originalHeight) {
            const containerWidth = container.clientWidth;
            const containerHeight = container.clientHeight - 20; // Account for padding
            
            // Calculate scale to fit
            const scaleX = containerWidth / userCanvas.originalWidth;
            const scaleY = containerHeight / userCanvas.originalHeight;
            let scale = Math.min(scaleX, scaleY);
            
            // Apply device-specific limits
            const isMobile = window.innerWidth <= 768;
            if (isMobile) {
                scale = Math.max(0.3, Math.min(1.0, scale));
            } else {
                scale = Math.max(0.2, Math.min(1.5, scale));
            }
            
            // Reset viewport transform
            userCanvas.setViewportTransform([1, 0, 0, 1, 0, 0]);
            userCanvas.setZoom(scale);
            
            // Center the canvas
            const canvasWidth = userCanvas.originalWidth * scale;
            const canvasHeight = userCanvas.originalHeight * scale;
            const offsetX = (containerWidth - canvasWidth) / 2;
            const offsetY = Math.max(0, (containerHeight - canvasHeight) / 2);
            
            userCanvas.setViewportTransform([scale, 0, 0, scale, offsetX, offsetY]);
            userCanvas.requestRenderAll();
        }
    }
    
    // Disable default touch behaviors on canvas container
    const canvasContainer = document.querySelector('#user-booking-view .canvas-container');
    if (canvasContainer) {
        canvasContainer.style.touchAction = 'none';
        canvasContainer.style.webkitUserSelect = 'none';
        canvasContainer.style.userSelect = 'none';
    }
    
    // Disable Fabric.js default touch scrolling to prevent conflicts
    userCanvas.allowTouchScrolling = false;
    
    console.log('Mobile touch interactions enabled for user canvas');
}

// Floating notification system
function showFloatingNotification(message, type = 'error', duration = 5000) {
    // Remove any existing floating notifications
    removeExistingFloatingNotifications();
    
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `floating-notification ${type}`;
    
    // Create icon based on type
    let icon = '';
    switch (type) {
        case 'error':
            icon = '❌';
            break;
        case 'success':
            icon = '✅';
            break;
        case 'warning':
            icon = '⚠️';
            break;
        default:
            icon = 'ℹ️';
    }
    
    // Create notification HTML
    notification.innerHTML = `
        <span class="notification-icon">${icon}</span>
        <span class="notification-message">${message}</span>
        <button class="notification-close" onclick="removeFloatingNotification(this.parentElement)">&times;</button>
    `;
    
    // Add to page
    document.body.appendChild(notification);
    
    // Auto-remove after duration
    if (duration > 0) {
        setTimeout(() => {
            removeFloatingNotification(notification);
        }, duration);
    }
    
    // Allow clicking anywhere on notification to close it
    notification.addEventListener('click', (e) => {
        if (e.target.className !== 'notification-close') {
            removeFloatingNotification(notification);
        }
    });
    
    return notification;
}

function removeFloatingNotification(notification) {
    if (notification && notification.parentElement) {
        notification.classList.add('removing');
        setTimeout(() => {
            if (notification.parentElement) {
                notification.remove();
            }
        }, 300); // Match animation duration
    }
}

function removeExistingFloatingNotifications() {
    document.querySelectorAll('.floating-notification').forEach(el => {
        removeFloatingNotification(el);
    });
}

function showErrorNotification(message, duration = 6000) {
    return showFloatingNotification(message, 'error', duration);
}

function showSuccessNotification(message, duration = 4000) {
    return showFloatingNotification(message, 'success', duration);
}

function showWarningNotification(message, duration = 5000) {
    return showFloatingNotification(message, 'warning', duration);
}

// Legacy message utilities for backward compatibility
function showErrorMessage(message) {
    showErrorNotification(message);
}

function showSuccessMessage(message) {
    showSuccessNotification(message);
}

function removeExistingMessages() {
    removeExistingFloatingNotifications();
    // Also remove any old-style messages that might still exist
    document.querySelectorAll('.error-message, .success-message').forEach(el => el.remove());
}

// Initialize booking when DOM is ready
document.addEventListener('DOMContentLoaded', initBooking);

// Export functions for global access
window.updateView = updateView;
window.setupResponsiveCanvases = setupResponsiveCanvases;
window.cancelBooking = cancelBooking;
window.showSuccessMessage = showSuccessMessage;
window.showErrorMessage = showErrorMessage;
