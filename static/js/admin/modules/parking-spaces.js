/* Parking Spaces Module - Visual parking space management with Fabric.js */

const AdminParkingSpaces = {
    // Module-specific variables
    adminCanvas: null,
    adminCurrentLot: null,
    adminSpaces: [],
    adminSelectedSpace: null,
    isDrawingMode: false,
    drawingRect: null,
    startPointer: null,
    nextSpaceNumber: 1,
    adminOrientationChangeTimeout: null,

    // Load parking lots for spaces dropdown
    async loadParkingLotsForSpaces() {
        const select = document.getElementById('spaces-lot-filter');
        if (!select) return;
        
        try {
            const response = await AdminAPI.parkingLots.getAll();

            if (response.ok) {
                const lots = await response.json();
                select.innerHTML = '<option value="">Select Parking Lot</option>';
                lots.forEach(lot => {
                    const option = document.createElement('option');
                    option.value = lot.id;
                    option.textContent = lot.name;
                    select.appendChild(option);
                });
            } else {
                AdminNotifications.showError('Failed to load parking lots');
            }
        } catch (error) {
            AdminNotifications.handleApiError(error, 'Error loading parking lots');
        }
    },

    // Handle spaces lot filter change
    handleSpacesLotFilterChange(event) {
        const selectedLotId = event.target.value;
        const refreshBtn = document.getElementById('refresh-spaces-btn');
        const noLotSelected = document.getElementById('no-lot-selected');
        const spacesContent = document.getElementById('spaces-content');
        
        if (selectedLotId) {
            refreshBtn.disabled = false;
            noLotSelected.style.display = 'none';
            spacesContent.style.display = 'block';
            
            if (!this.adminCanvas) {
                this.initializeAdminCanvas();
            }
            
            document.getElementById('visual-interface').style.display = 'block';
            this.loadAdminVisualData();
        } else {
            refreshBtn.disabled = true;
            noLotSelected.style.display = 'block';
            spacesContent.style.display = 'none';
            document.getElementById('visual-interface').style.display = 'none';
        }
    },

    // Load visual data for selected parking lot
    async loadAdminVisualData() {
        const selectedLotId = document.getElementById('spaces-lot-filter').value;
        if (!selectedLotId || !this.adminCanvas) return;

        try {
            const lotResponse = await AdminAPI.parkingLots.get(selectedLotId);

            if (lotResponse.ok) {
                this.adminCurrentLot = await lotResponse.json();
                
                if (this.adminCurrentLot.image) {
                    // Use synchronized background loading
                    await this.loadBackgroundImageSynchronized(this.adminCurrentLot.image);
                } else {
                    // No background image, ensure canvas is ready
                    await this.ensureAdminCanvasReady();
                }

                // Only load spaces after background is fully ready
                await this.loadAdminParkingSpaces();
                this.showAdminStatus(`Loaded parking lot: ${this.adminCurrentLot.name}`, 'success');
            }
        } catch (error) {
            this.showAdminStatus('Error loading visual data: ' + error.message, 'danger');
            AdminNotifications.handleApiError(error, 'Error loading visual data');
        }
    },

    // Synchronized background image loading
    async loadBackgroundImageSynchronized(imageUrl) {
        return new Promise((resolve, reject) => {
            fabric.Image.fromURL(imageUrl, (img) => {
                if (!img) {
                    reject(new Error('Failed to load background image'));
                    return;
                }
                
                this.adminCanvas.setBackgroundImage(img, () => {
                    if (this.adminCanvas.backgroundImage) {
                        this.adminCanvas.originalWidth = this.adminCanvas.backgroundImage.width;
                        this.adminCanvas.originalHeight = this.adminCanvas.backgroundImage.height;
                    }
                    
                    // Ensure canvas is properly sized before resolving
                    this.resizeAdminCanvas(this.adminCanvas, document.getElementById('admin-canvas-container'));
                    
                    // Add small delay to ensure rendering is complete
                    setTimeout(() => {
                        resolve();
                    }, 50);
                });
            }, { crossOrigin: 'anonymous' });
        });
    },

    // Ensure canvas is ready for rendering
    async ensureAdminCanvasReady() {
        return new Promise((resolve) => {
            if (!this.adminCanvas) {
                resolve();
                return;
            }
            
            // If no background image, just ensure canvas dimensions are set
            const container = document.getElementById('admin-canvas-container');
            if (container) {
                this.resizeAdminCanvas(this.adminCanvas, container);
            }
            
            // Small delay to ensure canvas is ready
            setTimeout(() => {
                resolve();
            }, 50);
        });
    },

    // Load parking spaces for current lot
    async loadAdminParkingSpaces() {
        if (!this.adminCurrentLot || !this.adminCanvas) return;

        try {
            const response = await AdminAPI.parkingLots.getSpaces(this.adminCurrentLot.id);

            if (response.ok) {
                this.adminSpaces = await response.json();
                
                // Also fetch current booking information
                await this.loadAdminBookingInfo();
                
                this.renderAdminSpaces();
            }
        } catch (error) {
            this.showAdminStatus('Error loading parking spaces: ' + error.message, 'danger');
            AdminNotifications.handleApiError(error, 'Error loading parking spaces');
        }
    },

    // Load booking information for spaces
    async loadAdminBookingInfo() {
        if (!this.adminCurrentLot) return;

        try {
            // Get current time and set end time to 24 hours from now to show current bookings
            const now = new Date();
            const endTime = new Date(now.getTime() + 24 * 60 * 60 * 1000); // 24 hours from now
            
            const startDateTime = now.toISOString();
            const endDateTime = endTime.toISOString();

            const availabilityResponse = await AdminAPI.parkingLots.getAvailability(
                this.adminCurrentLot.id, startDateTime, endDateTime
            );
            
            if (availabilityResponse.ok) {
                const availabilityData = await availabilityResponse.json();
                
                // Store booking information globally for admin use
                window.adminBookedSpaceIds = availabilityData.booked_space_ids || [];
                window.adminSpaceLicensePlates = availabilityData.space_license_plates || {};
            } else {
                window.adminBookedSpaceIds = [];
                window.adminSpaceLicensePlates = {};
            }
        } catch (error) {
            console.error('Error loading booking info:', error);
            window.adminBookedSpaceIds = [];
            window.adminSpaceLicensePlates = {};
        }
    },

    // Render spaces on canvas
    renderAdminSpaces() {
        if (!this.adminCanvas) return;
        
        this.adminCanvas.getObjects().forEach(obj => {
            if (obj.spaceData) {
                this.adminCanvas.remove(obj);
            }
        });

        this.adminSpaces.forEach(space => {
            this.createAdminSpaceObject(space);
        });

        this.adminCanvas.renderAll();
    },

    // Create space object on canvas
    createAdminSpaceObject(spaceData) {
        if (!this.adminCanvas) return null;

        // Check if space is currently booked
        const isBooked = window.adminBookedSpaceIds && window.adminBookedSpaceIds.includes(spaceData.id);
        const licensePlate = window.adminSpaceLicensePlates && window.adminSpaceLicensePlates[spaceData.id];

        const rect = new fabric.Rect({
            left: spaceData.position_x,
            top: spaceData.position_y,
            width: spaceData.width,
            height: spaceData.height,
            fill: isBooked ? '#dc3545' : (spaceData.color || '#28a745'), // Red if booked, otherwise use space color
            stroke: '#000',
            strokeWidth: 0,
            selectable: true,
            hasControls: true,
            hasBorders: false,
            objectCaching: false
        });

        // Create space number text
        const spaceText = new fabric.Text(spaceData.space_number, {
            left: spaceData.position_x + spaceData.width / 2,
            top: spaceData.position_y + spaceData.height / 2 - (licensePlate ? 10 : 0),
            fontSize: 18,
            fill: 'black',
            fontWeight: 'bold',
            originX: 'center',
            originY: 'center',
            selectable: false
        });

        const groupObjects = [rect, spaceText];

        // Add license plate text if space is booked
        if (licensePlate) {
            const licensePlateText = new fabric.Text(licensePlate, {
                left: spaceData.position_x + spaceData.width / 2,
                top: spaceData.position_y + spaceData.height / 2 + 12,
                fontSize: 16,
                fill: 'black',
                fontWeight: 'normal',
                originX: 'center',
                originY: 'center',
                selectable: false
            });
            groupObjects.push(licensePlateText);
        }

        const group = new fabric.Group(groupObjects, {
            left: spaceData.position_x,
            top: spaceData.position_y,
            selectable: true,
            hasControls: true,
            hasBorders: false,
            spaceData: spaceData,
            objectCaching: false
        });

        // Add custom controls for delete and clone
        group.controls.deleteControl = new fabric.Control({
            x: 0.5,
            y: -0.5,
            offsetY: -16,
            offsetX: 16,
            cursorStyle: 'pointer',
            mouseUpHandler: this.deleteObject.bind(this),
            render: this.renderIcon(window.AdminCore.deleteImg),
            cornerSize: 24,
        });

        group.controls.cloneControl = new fabric.Control({
            x: -0.5,
            y: -0.5,
            offsetY: -16,
            offsetX: -16,
            cursorStyle: 'pointer',
            mouseUpHandler: this.cloneObject.bind(this),
            render: this.renderIcon(window.AdminCore.cloneImg),
            cornerSize: 24,
        });

        this.adminCanvas.add(group);
        return group;
    },

    // Initialize admin canvas
    initializeAdminCanvas() {
        if (this.adminCanvas) return;
        
        this.adminCanvas = new fabric.Canvas('admin-parking-canvas', {
            width: 800,
            height: 600,
            backgroundColor: '#f8f9fa'
        });

        this.setupCanvasEventHandlers();
        this.setupResponsiveAdminCanvas();
        
        fabric.Object.prototype.transparentCorners = false;
        fabric.Object.prototype.cornerColor = 'blue';
        fabric.Object.prototype.cornerStyle = 'circle';
    },

    // Setup canvas event handlers for drawing functionality
    setupCanvasEventHandlers() {
        if (!this.adminCanvas) return;

        // Handle mouse down for starting rectangle drawing
        this.adminCanvas.on('mouse:down', (options) => {
            if (!this.adminCurrentLot) return;
            
            // Only start drawing when clicking on empty area (not on existing objects)
            if (!options.target) {
                this.isDrawingMode = true;
                const pointer = this.adminCanvas.getPointer(options.e);
                this.startPointer = pointer;
                
                // Create temporary rectangle for visual feedback
                this.drawingRect = new fabric.Rect({
                    left: pointer.x,
                    top: pointer.y,
                    width: 0,
                    height: 0,
                    fill: 'rgba(40, 167, 69, 0.3)',
                    stroke: '#28a745',
                    strokeWidth: 0,
                    selectable: false,
                    evented: false
                });
                
                this.adminCanvas.add(this.drawingRect);
            }
        });

        // Handle mouse move during drawing
        this.adminCanvas.on('mouse:move', (options) => {
            if (!this.isDrawingMode || !this.drawingRect) return;
            
            const pointer = this.adminCanvas.getPointer(options.e);
            const width = Math.abs(pointer.x - this.startPointer.x);
            const height = Math.abs(pointer.y - this.startPointer.y);
            
            this.drawingRect.set({
                left: Math.min(pointer.x, this.startPointer.x),
                top: Math.min(pointer.y, this.startPointer.y),
                width: width,
                height: height
            });
            
            this.adminCanvas.renderAll();
        });

        // Handle mouse up to complete rectangle drawing
        this.adminCanvas.on('mouse:up', (options) => {
            if (!this.isDrawingMode || !this.drawingRect) return;
            
            this.isDrawingMode = false;
            
            // Check if rectangle is large enough to be valid
            if (this.drawingRect.width >= 50 && this.drawingRect.height >= 30) {
                // Generate new space number
                const newSpaceNumber = this.generateNextSpaceNumber();
                
                // Create new space data
                const newSpaceData = {
                    id: null, // Will be set when saved
                    space_number: newSpaceNumber,
                    position_x: Math.round(this.drawingRect.left),
                    position_y: Math.round(this.drawingRect.top),
                    width: Math.round(this.drawingRect.width),
                    height: Math.round(this.drawingRect.height),
                    color: '#28a745',
                    lot_id: this.adminCurrentLot.id
                };
                
                // Add to spaces array
                this.adminSpaces.push(newSpaceData);
                
                // Remove temporary drawing rectangle
                this.adminCanvas.remove(this.drawingRect);
                
                // Create actual space object
                const spaceObj = this.createAdminSpaceObject(newSpaceData);
                this.adminCanvas.setActiveObject(spaceObj);
                
                this.showAdminStatus(`New space "${newSpaceNumber}" created. Remember to save changes.`, 'info');
            } else {
                // Remove small rectangle
                this.adminCanvas.remove(this.drawingRect);
                this.showAdminStatus('Rectangle too small. Minimum size: 50x30 pixels.', 'warning');
            }
            
            this.drawingRect = null;
            this.startPointer = null;
        });

        // Handle double-click to edit space label
        this.adminCanvas.on('mouse:dblclick', (options) => {
            if (!this.adminCurrentLot) return;
            
            // Check if double-click target is a space object
            if (options.target && options.target.spaceData) {
                const spaceObj = options.target;
                this.showAdminEditLabelModal(spaceObj);
            }
        });
    },

    // Generate next space number
    generateNextSpaceNumber() {
        const existingNumbers = this.adminSpaces.map(space => space.space_number);
        
        // Try to find next available number
        let num = this.nextSpaceNumber;
        while (existingNumbers.includes(`S-${num.toString().padStart(2, '0')}`)) {
            num++;
        }
        
        this.nextSpaceNumber = num + 1;
        return `S-${num.toString().padStart(2, '0')}`;
    },

    // Save all admin changes
    async saveAllAdminChanges() {
        if (!this.adminCurrentLot) {
            this.showAdminStatus('No parking lot selected.', 'warning');
            return;
        }

        try {
            this.showAdminStatus('Saving changes...', 'info');

            for (const space of this.adminSpaces) {
                const canvasObj = this.adminCanvas.getObjects().find(obj => obj.spaceData === space);
                if (canvasObj) {
                    // Get the actual zoom factor
                    const zoom = this.adminCanvas.getZoom();
                    
                    // Calculate positions accounting for zoom
                    space.position_x = Math.round(canvasObj.left);
                    space.position_y = Math.round(canvasObj.top);
                    
                    // Get dimensions from the bounding box
                    space.width = Math.round(canvasObj.width * canvasObj.scaleX);
                    space.height = Math.round(canvasObj.height * canvasObj.scaleY);
                }

                if (space.id === null) {
                    const response = await AdminAPI.parkingLots.createSpace(this.adminCurrentLot.id, {
                        space_number: space.space_number,
                        position_x: space.position_x,
                        position_y: space.position_y,
                        width: space.width,
                        height: space.height,
                        color: space.color
                    });

                    if (response.ok) {
                        const newSpace = await response.json();
                        space.id = newSpace.id;
                    } else {
                        throw new Error(`Failed to create space ${space.space_number}`);
                    }
                } else {
                    const response = await AdminAPI.parkingLots.updateSpace(this.adminCurrentLot.id, space.id, {
                        space_number: space.space_number,
                        position_x: space.position_x,
                        position_y: space.position_y,
                        width: space.width,
                        height: space.height,
                        color: space.color
                    });

                    if (!response.ok) {
                        throw new Error(`Failed to update space ${space.space_number}`);
                    }
                }
            }

            this.showAdminStatus('All changes saved successfully!', 'success');
            await this.loadAdminParkingSpaces();
            
        } catch (error) {
            this.showAdminStatus('Error saving changes: ' + error.message, 'danger');
            AdminNotifications.handleApiError(error, 'Error saving changes');
        }
    },

    // Show admin status message
    showAdminStatus(message, type = 'secondary') {
        if (window.AdminCore && window.AdminCore.showAdminStatus) {
            window.AdminCore.showAdminStatus(message, type);
        } else {
            const statusElement = document.getElementById('admin-status-message');
            if (statusElement) {
                statusElement.className = `alert alert-${type}`;
                statusElement.textContent = message;
                
                if (type === 'success' || type === 'info') {
                    setTimeout(() => {
                        statusElement.className = 'alert alert-secondary';
                        statusElement.textContent = 'Ready for visual editing.';
                    }, 3000);
                }
            }
        }
    },

    // Delete space object
    async deleteObject(_eventData, transform) {
        const canvas = transform.target.canvas;
        const spaceObj = transform.target;
        
        if (!spaceObj.spaceData) return;

        const spaceData = spaceObj.spaceData;
        const spaceNumber = spaceData.space_number;

        try {
            // If space has an ID, it exists in the database and needs API deletion
            if (spaceData.id !== null && spaceData.id !== undefined) {
                const confirmed = await AdminNotifications.confirm(`Are you sure you want to delete parking space "${spaceNumber}"?`);
                if (!confirmed) return;

                this.showAdminStatus(`Deleting space "${spaceNumber}"...`, 'info');

                const response = await AdminAPI.parkingLots.deleteSpace(this.adminCurrentLot.id, spaceData.id);

                if (!response.ok) {
                    throw new Error(`Failed to delete space from server: ${response.status}`);
                }

                this.showAdminStatus(`Space "${spaceNumber}" deleted successfully!`, 'success');
            } else {
                // Space not yet saved to database, just confirm local deletion
                const confirmed = await AdminNotifications.confirm(`Are you sure you want to delete the unsaved space "${spaceNumber}"?`);
                if (!confirmed) return;
                
                this.showAdminStatus(`Unsaved space "${spaceNumber}" removed.`, 'info');
            }

            // Remove from adminSpaces array
            const spaceIndex = this.adminSpaces.findIndex(space => space === spaceData);
            if (spaceIndex > -1) {
                this.adminSpaces.splice(spaceIndex, 1);
            }
            
            // Remove from canvas
            canvas.remove(spaceObj);
            canvas.requestRenderAll();

        } catch (error) {
            console.error('Error deleting space:', error);
            this.showAdminStatus(`Error deleting space "${spaceNumber}": ${error.message}`, 'danger');
        }
    },

    // Clone space object
    cloneObject(_eventData, transform) {
        const canvas = transform.target.canvas;
        const originalSpace = transform.target;
        
        if (originalSpace.spaceData) {
            // Create new space data
            const newSpaceData = {
                id: null, // Will be set when saved
                space_number: this.generateNextSpaceNumber(),
                position_x: originalSpace.spaceData.position_x + 10,
                position_y: originalSpace.spaceData.position_y + 10,
                width: originalSpace.spaceData.width,
                height: originalSpace.spaceData.height,
                color: originalSpace.spaceData.color,
                lot_id: originalSpace.spaceData.lot_id
            };
            
            // Add to spaces array
            this.adminSpaces.push(newSpaceData);
            
            // Create new space object
            const clonedSpace = this.createAdminSpaceObject(newSpaceData);
            canvas.setActiveObject(clonedSpace);
            
            this.showAdminStatus(`Space "${newSpaceData.space_number}" cloned. Remember to save changes.`, 'info');
        }
    },

    // Render icon helper for Fabric.js controls
    renderIcon(icon) {
        return function (ctx, left, top, _styleOverride, fabricObject) {
            const size = this.cornerSize;
            
            // Validate that icon is a proper image element and is loaded
            if (!icon || !icon.complete || icon.naturalWidth === 0) {
                // Fallback: draw a simple geometric shape instead
                ctx.save();
                ctx.translate(left, top);
                ctx.rotate(fabric.util.degreesToRadians(fabricObject.angle));
                
                // Draw a simple circle as fallback
                ctx.fillStyle = '#007bff';
                ctx.strokeStyle = '#ffffff';
                ctx.lineWidth = 2;
                ctx.beginPath();
                ctx.arc(0, 0, size / 2 - 2, 0, 2 * Math.PI);
                ctx.fill();
                ctx.stroke();
                
                ctx.restore();
                return;
            }
            
            try {
                ctx.save();
                ctx.translate(left, top);
                ctx.rotate(fabric.util.degreesToRadians(fabricObject.angle));
                ctx.drawImage(icon, -size / 2, -size / 2, size, size);
                ctx.restore();
            } catch (error) {
                console.warn('Error drawing fabric.js control icon:', error);
                // Fallback: draw a simple geometric shape
                ctx.save();
                ctx.translate(left, top);
                ctx.rotate(fabric.util.degreesToRadians(fabricObject.angle));
                
                ctx.fillStyle = '#dc3545';
                ctx.strokeStyle = '#ffffff';
                ctx.lineWidth = 2;
                ctx.beginPath();
                ctx.arc(0, 0, size / 2 - 2, 0, 2 * Math.PI);
                ctx.fill();
                ctx.stroke();
                
                ctx.restore();
            }
        };
    },

    // Responsive canvas functions with device-aware scaling limits
    resizeAdminCanvas(canvas, container) {
        if (!canvas || !container) return;
        
        const containerWidth = container.clientWidth;
        if (containerWidth > 0 && canvas.originalWidth) {
            // Calculate initial scale factor based on container width
            let scaleFactor = Math.min(1, (containerWidth - 20) / canvas.originalWidth);
            
            // Apply device-aware scaling limits
            const isMobile = window.innerWidth <= 768;
            
            if (isMobile) {
                // Mobile limits: min 30%, max 100% of original size
                scaleFactor = Math.max(0.3, Math.min(1.0, scaleFactor));
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
    },

    // Enhanced resize function that forces background image refresh for admin canvas
    resizeAdminCanvasWithBackgroundRefresh(canvas, container) {
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
                fabric.Image.fromURL(backgroundImageUrl, (img) => {
                    canvas.setBackgroundImage(img, () => {
                        if (canvas.backgroundImage) {
                            canvas.originalWidth = canvas.backgroundImage.width;
                            canvas.originalHeight = canvas.backgroundImage.height;
                        }
                        // Now resize with the refreshed background
                        this.resizeAdminCanvas(canvas, container);
                    });
                });
            } else {
                // No background image, just resize normally
                this.resizeAdminCanvas(canvas, container);
            }
        });
    },

    // Debounced orientation change handler for admin canvas
    handleAdminOrientationChange() {
        // Clear any existing timeout
        if (this.adminOrientationChangeTimeout) {
            clearTimeout(this.adminOrientationChangeTimeout);
        }
        
        // Wait for orientation change to complete
        this.adminOrientationChangeTimeout = setTimeout(() => {
            const adminCanvasContainer = document.getElementById('admin-canvas-container');
            const spacesPane = document.getElementById('parking-spaces-pane');
            if (adminCanvasContainer && spacesPane && spacesPane.classList.contains('show') && this.adminCanvas) {
                this.resizeAdminCanvasWithBackgroundRefresh(this.adminCanvas, adminCanvasContainer);
            }
        }, 250); // Wait 250ms for orientation change to complete
    },

    setupResponsiveAdminCanvas() {
        const adminCanvasContainer = document.getElementById('admin-canvas-container');
        if (!adminCanvasContainer) return;
        
        // Initial resize
        if (this.adminCanvas) {
            this.resizeAdminCanvas(this.adminCanvas, adminCanvasContainer);
        }
        
        // Standard resize event listener
        window.addEventListener('resize', () => {
            const spacesPane = document.getElementById('parking-spaces-pane');
            if (spacesPane && spacesPane.classList.contains('show') && this.adminCanvas) {
                this.resizeAdminCanvas(this.adminCanvas, adminCanvasContainer);
            }
        });

        // Mobile orientation change handlers for admin canvas
        // Modern browsers
        if (screen.orientation) {
            screen.orientation.addEventListener('change', () => this.handleAdminOrientationChange());
        }
        
        // Legacy browsers
        window.addEventListener('orientationchange', () => this.handleAdminOrientationChange());
        
        // Additional mobile detection for better compatibility
        window.addEventListener('resize', () => {
            // Detect if this might be an orientation change on mobile
            if (window.innerHeight !== window.innerWidth) {
                const isMobile = window.innerWidth <= 768 || window.innerHeight <= 768;
                if (isMobile) {
                    this.handleAdminOrientationChange();
                }
            }
        });
    },

    // Show edit label modal
    showAdminEditLabelModal(spaceObj) {
        const modal = new bootstrap.Modal(document.getElementById('admin-edit-label-modal'));
        document.getElementById('admin-edit-space-number').value = spaceObj.spaceData.space_number;
        document.getElementById('admin-edit-space-color').value = spaceObj.spaceData.color;
        this.adminSelectedSpace = spaceObj;
        modal.show();
    },

    // Save label changes
    saveAdminLabelChanges() {
        if (!this.adminSelectedSpace) return;

        const newNumber = document.getElementById('admin-edit-space-number').value;
        const newColor = document.getElementById('admin-edit-space-color').value;

        this.adminSelectedSpace.spaceData.space_number = newNumber;
        this.adminSelectedSpace.spaceData.color = newColor;

        const text = this.adminSelectedSpace.getObjects()[1];
        const rect = this.adminSelectedSpace.getObjects()[0];
        text.set('text', newNumber);
        rect.set('fill', newColor);

        this.adminCanvas.renderAll();
        bootstrap.Modal.getInstance(document.getElementById('admin-edit-label-modal')).hide();
        this.showAdminStatus('Space label updated. Remember to save changes.', 'info');
    },

    // Initialize parking spaces module
    init() {
        // Setup event listeners
        const spacesLotFilter = document.getElementById('spaces-lot-filter');
        if (spacesLotFilter) {
            spacesLotFilter.addEventListener('change', this.handleSpacesLotFilterChange.bind(this));
        }

        const refreshBtn = document.getElementById('refresh-spaces-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', this.loadAdminVisualData.bind(this));
        }

        // Properties panel buttons
        const applyBtn = document.getElementById('admin-apply-properties');
        const cancelBtn = document.getElementById('admin-cancel-properties');
        const saveAllBtn = document.getElementById('admin-save-all-btn');

        if (applyBtn) applyBtn.addEventListener('click', this.applyAdminSpaceProperties.bind(this));
        if (cancelBtn) cancelBtn.addEventListener('click', this.hideAdminSpaceProperties.bind(this));
        if (saveAllBtn) saveAllBtn.addEventListener('click', this.saveAllAdminChanges.bind(this));

        // Edit label modal save button
        const saveLabelBtn = document.getElementById('admin-save-label-changes');
        if (saveLabelBtn) {
            saveLabelBtn.addEventListener('click', this.saveAdminLabelChanges.bind(this));
        }

        // Load parking lots for the dropdown when module initializes
        this.loadParkingLotsForSpaces();

        console.log('Parking spaces module initialized');
    },

    // Apply space properties (placeholder for future implementation)
    applyAdminSpaceProperties() {
        // Implementation for applying space properties
        console.log('Apply space properties');
    },

    // Hide space properties panel (placeholder for future implementation)
    hideAdminSpaceProperties() {
        const propertiesPanel = document.getElementById('admin-space-properties');
        if (propertiesPanel) {
            propertiesPanel.style.display = 'none';
        }
    }
};

// Export for global access
window.AdminParkingSpaces = AdminParkingSpaces;

// Initialize when module loads
AdminParkingSpaces.init();

console.log('Admin parking spaces module loaded!');
