/* Hybrid Canvas Manager - Combines WebGPU rendering with Fabric.js interactions */

class HybridCanvasManager {
    constructor() {
        this.webgpuRenderer = null;
        this.fabricCanvas = null;
        this.webgpuCanvas = null;
        this.interactionCanvas = null;
        this.container = null;
        this.useWebGPU = false;
        this.spaces = [];
        this.bookedSpaceIds = [];
        this.spaceLicensePlates = {};
        this.clickHandler = null;
        this.isAdmin = false;
        this.backgroundImage = null;
        this.renderLoop = null;
    }

    // Initialize the hybrid canvas system
    async init(fabricCanvas, container, isAdmin = false) {
        this.fabricCanvas = fabricCanvas;
        this.container = container;
        this.isAdmin = isAdmin;
        
        console.log('Initializing hybrid canvas manager...');
        
        // Try to initialize WebGPU
        if (WebGPURenderer.isSupported()) {
            try {
                await this.initWebGPU();
                if (this.useWebGPU) {
                    console.log('✅ Using WebGPU for high-performance rendering');
                    this.setupHybridMode();
                } else {
                    console.log('⚠️ WebGPU initialization failed, using Fabric.js only');
                }
            } catch (error) {
                console.error('WebGPU initialization error:', error);
                console.log('📱 Falling back to Fabric.js rendering');
            }
        } else {
            console.log('📱 WebGPU not supported, using Fabric.js rendering');
        }
        
        return this.useWebGPU;
    }

    // Initialize WebGPU renderer
    async initWebGPU() {
        // Create WebGPU canvas
        this.webgpuCanvas = document.createElement('canvas');
        this.webgpuCanvas.style.position = 'absolute';
        this.webgpuCanvas.style.top = '0';
        this.webgpuCanvas.style.left = '0';
        this.webgpuCanvas.style.pointerEvents = 'none'; // Let Fabric.js handle interactions
        this.webgpuCanvas.style.zIndex = '1';
        
        // Initialize WebGPU renderer
        this.webgpuRenderer = new WebGPURenderer();
        this.useWebGPU = await this.webgpuRenderer.init(this.webgpuCanvas);
        
        if (this.useWebGPU) {
            // Insert WebGPU canvas before Fabric.js canvas
            this.container.style.position = 'relative';
            this.container.insertBefore(this.webgpuCanvas, this.fabricCanvas.upperCanvasEl);
            
            // Match initial canvas size
            this.syncCanvasSize();
        }
    }

    // Setup hybrid mode where WebGPU renders, Fabric.js handles interactions
    setupHybridMode() {
        // Make Fabric.js canvas transparent for interaction overlay
        this.fabricCanvas.upperCanvasEl.style.backgroundColor = 'transparent';
        this.fabricCanvas.lowerCanvasEl.style.backgroundColor = 'transparent';
        this.fabricCanvas.upperCanvasEl.style.zIndex = '2';
        this.fabricCanvas.lowerCanvasEl.style.zIndex = '2';
        
        // Disable Fabric.js rendering of spaces (we'll use WebGPU for that)
        this.fabricCanvas.renderOnAddRemove = false;
        
        // Hook into Fabric.js events for synchronization
        this.setupFabricEvents();
        
        // Start render loop
        this.startRenderLoop();
    }

    // Setup Fabric.js event handlers
    setupFabricEvents() {
        // Handle canvas resize
        this.fabricCanvas.on('canvas:resized', () => {
            this.syncCanvasSize();
        });
        
        // Handle zoom and pan changes
        this.fabricCanvas.on('viewportTransform', () => {
            if (this.useWebGPU) {
                this.updateWebGPUTransform();
            }
        });
    }

    // Sync canvas sizes between WebGPU and Fabric.js
    syncCanvasSize() {
        if (!this.useWebGPU) return;
        
        const fabricWidth = this.fabricCanvas.width;
        const fabricHeight = this.fabricCanvas.height;
        
        this.webgpuRenderer.setSize(fabricWidth, fabricHeight);
        this.webgpuCanvas.style.width = this.fabricCanvas.upperCanvasEl.style.width;
        this.webgpuCanvas.style.height = this.fabricCanvas.upperCanvasEl.style.height;
    }

    // Update WebGPU transform to match Fabric.js viewport
    updateWebGPUTransform() {
        // This would update the view matrix in WebGPU to match Fabric.js zoom/pan
        // For now, we'll keep it simple and re-render
        if (this.useWebGPU && this.webgpuRenderer) {
            this.requestRender();
        }
    }

    // Start the render loop for WebGPU
    startRenderLoop() {
        if (!this.useWebGPU) return;
        
        const render = () => {
            if (this.webgpuRenderer && this.webgpuRenderer.isInitialized) {
                this.webgpuRenderer.render();
            }
            this.renderLoop = requestAnimationFrame(render);
        };
        
        render();
    }

    // Stop the render loop
    stopRenderLoop() {
        if (this.renderLoop) {
            cancelAnimationFrame(this.renderLoop);
            this.renderLoop = null;
        }
    }

    // Request a render (for when data changes)
    requestRender() {
        if (this.useWebGPU && this.webgpuRenderer) {
            // WebGPU will render on next frame
        }
    }

    // Set background image
    async setBackgroundImage(imageUrl) {
        this.backgroundImage = imageUrl;
        
        if (this.useWebGPU && this.webgpuRenderer) {
            await this.webgpuRenderer.loadBackgroundImage(imageUrl);
            this.requestRender();
        } else {
            // Fallback to Fabric.js background
            this.fabricCanvas.setBackgroundImage(imageUrl, () => {
                if (this.fabricCanvas.backgroundImage) {
                    this.fabricCanvas.originalWidth = this.fabricCanvas.backgroundImage.width;
                    this.fabricCanvas.originalHeight = this.fabricCanvas.backgroundImage.height;
                }
                this.fabricCanvas.requestRenderAll();
            });
        }
    }

    // Update parking spaces
    updateSpaces(spaces, bookedSpaceIds = [], spaceLicensePlates = {}) {
        this.spaces = spaces;
        this.bookedSpaceIds = bookedSpaceIds;
        this.spaceLicensePlates = spaceLicensePlates;
        
        if (this.useWebGPU && this.webgpuRenderer) {
            // Use WebGPU for rendering spaces
            this.webgpuRenderer.updateSpaces(spaces);
            this.webgpuRenderer.updateAvailability(bookedSpaceIds);
            
            // Clear Fabric.js objects since WebGPU will handle rendering
            this.clearFabricSpaces();
            
            // Create invisible interaction objects for Fabric.js click handling
            this.createInteractionObjects(spaces, bookedSpaceIds, spaceLicensePlates);
            
            this.requestRender();
        } else {
            // Fallback to original Fabric.js rendering
            this.renderSpacesWithFabric(spaces, bookedSpaceIds, spaceLicensePlates);
        }
    }

    // Clear existing Fabric.js space objects
    clearFabricSpaces() {
        const objectsToRemove = this.fabricCanvas.getObjects().filter(obj => 
            obj.data && obj.data.id !== undefined
        );
        objectsToRemove.forEach(obj => this.fabricCanvas.remove(obj));
    }

    // Create invisible interaction objects for click handling
    createInteractionObjects(spaces, bookedSpaceIds, spaceLicensePlates) {
        const bookedSet = new Set(bookedSpaceIds);
        
        for (const space of spaces) {
            const isBooked = bookedSet.has(space.id);
            const licensePlate = spaceLicensePlates[space.id];
            
            // Create invisible rect for interaction
            const rect = new fabric.Rect({
                width: space.width,
                height: space.height,
                left: space.position_x,
                top: space.position_y,
                fill: 'transparent',
                stroke: 'transparent',
                strokeWidth: 0,
                selectable: this.isAdmin,
                hasControls: this.isAdmin,
                hasBorders: this.isAdmin,
                visible: false, // Make completely invisible
                data: {
                    id: space.id,
                    space_number: space.space_number,
                    is_booked: isBooked,
                    license_plate: licensePlate || null
                }
            });
            
            this.fabricCanvas.add(rect);
        }
        
        this.fabricCanvas.requestRenderAll();
    }

    // Fallback to Fabric.js rendering (original implementation)
    renderSpacesWithFabric(spaces, bookedSpaceIds, spaceLicensePlates) {
        // Clear existing objects
        this.fabricCanvas.remove(...this.fabricCanvas.getObjects());
        
        const bookedSet = new Set(bookedSpaceIds);
        
        for (const space of spaces) {
            const isBooked = bookedSet.has(space.id);
            const licensePlate = spaceLicensePlates[space.id];
            
            const rect = new fabric.Rect({
                width: space.width,
                height: space.height,
                fill: isBooked ? 'red' : space.color,
                stroke: 'black',
                strokeWidth: 0,
            });

            // Create space number text
            const spaceText = new fabric.Text(space.space_number, {
                left: space.width / 2,
                top: licensePlate ? space.height / 2 - 10 : space.height / 2,
                fontSize: 18,
                fill: 'black',
                originX: 'center',
                originY: 'center',
                fontWeight: 'bold'
            });

            const groupObjects = [rect, spaceText];

            // Add license plate text if space is booked
            if (licensePlate) {
                const licensePlateText = new fabric.Text(licensePlate, {
                    left: space.width / 2,
                    top: space.height / 2 + 12,
                    fontSize: 16,
                    fill: 'black',
                    originX: 'center',
                    originY: 'center',
                    fontWeight: 'normal'
                });
                groupObjects.push(licensePlateText);
            }

            const group = new fabric.Group(groupObjects, {
                left: space.position_x,
                top: space.position_y,
                selectable: this.isAdmin,
                hasControls: this.isAdmin,
                hasBorders: this.isAdmin,
                data: {
                    id: space.id,
                    space_number: space.space_number,
                    is_booked: isBooked,
                    license_plate: licensePlate || null
                }
            });
            
            this.fabricCanvas.add(group);
        }
        
        this.fabricCanvas.requestRenderAll();
    }

    // Update only availability (more efficient for real-time updates)
    updateAvailability(bookedSpaceIds, spaceLicensePlates = {}) {
        this.bookedSpaceIds = bookedSpaceIds;
        this.spaceLicensePlates = spaceLicensePlates;
        
        if (this.useWebGPU && this.webgpuRenderer) {
            // WebGPU can update availability very efficiently
            this.webgpuRenderer.updateAvailability(bookedSpaceIds);
            
            // Update interaction objects data
            this.updateInteractionObjectsData(bookedSpaceIds, spaceLicensePlates);
            
            this.requestRender();
        } else {
            // Update Fabric.js objects
            this.updateFabricAvailability(bookedSpaceIds, spaceLicensePlates);
        }
    }

    // Update interaction objects data for click handling
    updateInteractionObjectsData(bookedSpaceIds, spaceLicensePlates) {
        const bookedSet = new Set(bookedSpaceIds);
        
        this.fabricCanvas.getObjects().forEach(obj => {
            if (obj.data && obj.data.id !== undefined) {
                const isBooked = bookedSet.has(obj.data.id);
                const licensePlate = spaceLicensePlates[obj.data.id];
                
                obj.data.is_booked = isBooked;
                obj.data.license_plate = licensePlate || null;
            }
        });
    }

    // Update Fabric.js availability (fallback)
    updateFabricAvailability(bookedSpaceIds, spaceLicensePlates) {
        const bookedSet = new Set(bookedSpaceIds);
        
        this.fabricCanvas.getObjects().forEach(obj => {
            if (obj.data && obj.data.id !== undefined) {
                const isBooked = bookedSet.has(obj.data.id);
                const licensePlate = spaceLicensePlates[obj.data.id];
                
                // Update visual state
                if (obj.type === 'group') {
                    const rect = obj.getObjects()[0];
                    if (rect) {
                        rect.set('fill', isBooked ? 'red' : obj.data.originalColor || 'green');
                    }
                }
                
                // Update data
                obj.data.is_booked = isBooked;
                obj.data.license_plate = licensePlate || null;
            }
        });
        
        this.fabricCanvas.requestRenderAll();
    }

    // Handle canvas click (works for both WebGPU and Fabric.js modes)
    handleCanvasClick(clickHandler) {
        this.clickHandler = clickHandler;
        
        this.fabricCanvas.on('mouse:down', (e) => {
            if (e.target && e.target.data && e.target.data.id && clickHandler) {
                clickHandler(e);
            }
        });
    }

    // Resize the hybrid canvas system
    resize(container) {
        if (this.useWebGPU) {
            this.syncCanvasSize();
        }
        
        // Let the original resize logic handle Fabric.js
        if (this.fabricCanvas && this.fabricCanvas.originalWidth) {
            const containerWidth = container.clientWidth;
            if (containerWidth > 0) {
                let scaleFactor = Math.min(1, (containerWidth - 20) / this.fabricCanvas.originalWidth);
                
                const isMobile = window.innerWidth <= 768;
                if (isMobile) {
                    scaleFactor = Math.max(0.4, Math.min(1.0, scaleFactor));
                } else {
                    scaleFactor = Math.max(0.2, Math.min(1.5, scaleFactor));
                }
                
                const canvasWidth = this.fabricCanvas.originalWidth * scaleFactor;
                const canvasHeight = this.fabricCanvas.originalHeight * scaleFactor;

                this.fabricCanvas.setDimensions({ width: canvasWidth, height: canvasHeight });
                if (this.fabricCanvas.backgroundImage) {
                    this.fabricCanvas.backgroundImage.scaleToWidth(canvasWidth);
                    this.fabricCanvas.backgroundImage.scaleToHeight(canvasHeight);
                }
                this.fabricCanvas.setZoom(scaleFactor);
                this.fabricCanvas.requestRenderAll();
                
                // Sync WebGPU canvas size
                if (this.useWebGPU) {
                    this.syncCanvasSize();
                }
            }
        }
    }

    // Get performance stats
    getPerformanceStats() {
        return {
            useWebGPU: this.useWebGPU,
            spaceCount: this.spaces.length,
            renderer: this.useWebGPU ? 'WebGPU' : 'Fabric.js',
            webgpuSupported: WebGPURenderer.isSupported()
        };
    }

    // Clean up resources
    destroy() {
        this.stopRenderLoop();
        
        if (this.webgpuRenderer) {
            this.webgpuRenderer.destroy();
            this.webgpuRenderer = null;
        }
        
        if (this.webgpuCanvas && this.webgpuCanvas.parentNode) {
            this.webgpuCanvas.parentNode.removeChild(this.webgpuCanvas);
        }
        
        this.useWebGPU = false;
    }
}

// Export for global access
window.HybridCanvasManager = HybridCanvasManager;

console.log('Hybrid Canvas Manager loaded');
