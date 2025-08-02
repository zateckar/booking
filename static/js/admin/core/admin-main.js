/* Admin Main - Core initialization and shared utilities */

// Global admin variables
let adminCanvas = null;
let adminCurrentTool = 'create';
let adminSelectedSpace = null;
let adminCurrentLot = null;
let adminSpaces = [];
let adminIsDrawing = false;
let adminStartPoint = null;
let adminTempRect = null;
let isDrawingMode = false;
let drawingRect = null;
let startPointer = null;
let nextSpaceNumber = 1;

// Module registry for tracking loaded modules
const AdminModules = {
    loaded: new Set(),
    modules: {}
};

// Control images for fabric.js
const deleteIcon = "data:image/svg+xml,%3C%3Fxml version='1.0' encoding='utf-8'%3F%3E%3C!DOCTYPE svg PUBLIC '-//W3C//DTD SVG 1.1//EN' 'http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd'%3E%3Csvg version='1.1' id='Ebene_1' xmlns='http://www.w3.org/2000/svg' xmlns:xlink='http://www.w3.org/1999/xlink' x='0px' y='0px' width='595.275px' height='595.275px' viewBox='200 215 230 470' xml:space='preserve'%3E%3Ccircle style='fill:%23F44336;' cx='299.76' cy='439.067' r='218.516'/%3E%3Cg%3E%3Crect x='267.162' y='307.978' transform='matrix(0.7071 -0.7071 0.7071 0.7071 -222.6202 340.6915)' style='fill:white;' width='65.545' height='262.18'/%3E%3Crect x='266.988' y='308.153' transform='matrix(0.7071 0.7071 -0.7071 0.7071 398.3889 -83.3116)' style='fill:white;' width='65.544' height='262.179'/%3E%3C/g%3E%3C/svg%3E";

const cloneIcon = "data:image/svg+xml,%3C%3Fxml version='1.0' encoding='iso-8859-1'%3F%3E%3Csvg version='1.1' xmlns='http://www.w3.org/2000/svg' xmlns:xlink='http://www.w3.org/1999/xlink' viewBox='0 0 55.699 55.699' width='100px' height='100px' xml:space='preserve'%3E%3Cpath style='fill:%23010002;' d='M51.51,18.001c-0.006-0.085-0.022-0.167-0.05-0.248c-0.012-0.034-0.02-0.067-0.035-0.1 c-0.049-0.106-0.109-0.206-0.194-0.291v-0.001l0,0c0,0-0.001-0.001-0.001-0.002L34.161,0.293c-0.086-0.087-0.188-0.148-0.295-0.197 c-0.027-0.013-0.057-0.02-0.086-0.03c-0.086-0.029-0.174-0.048-0.265-0.053C33.494,0.011,33.475,0,33.453,0H22.177 c-3.678,0-6.669,2.992-6.669,6.67v1.674h-4.663c-3.678,0-6.67,2.992-6.67,6.67V49.03c0,3.678,2.992,6.669,6.67,6.669h22.677 c3.677,0,6.669-2.991,6.669-6.669v-1.675h4.664c3.678,0,6.669-2.991,6.669-6.669V18.069C51.524,18.045,51.512,18.025,51.51,18.001z M34.454,3.414l13.655,13.655h-8.985c-2.575,0-4.67-2.095-4.67-4.67V3.414z M38.191,49.029c0,2.574-2.095,4.669-4.669,4.669H10.845 c-2.575,0-4.67-2.095-4.67-4.669V15.014c0-2.575,2.095-4.67,4.67-4.67h5.663h4.614v10.399c0,3.678,2.991,6.669,6.668,6.669h10.4 v18.942L38.191,49.029L38.191,49.029z M36.777,25.412h-8.986c-2.574,0-4.668-2.094-4.668-4.669v-8.985L36.777,25.412z M44.855,45.355h-4.664V26.412c0-0.023-0.012-0.044-0.014-0.067c-0.006-0.085-0.021-0.167-0.049-0.249 c-0.012-0.033-0.021-0.066-0.036-0.1c-0.048-0.105-0.109-0.205-0.194-0.29l0,0l0,0c0-0.001-0.001-0.002-0.001-0.002L22.829,8.637 c-0.087-0.086-0.188-0.147-0.295-0.196c-0.029-0.013-0.058-0.021-0.088-0.031c-0.086-0.03-0.172-0.048-0.263-0.053 c-0.021-0.002-0.04-0.013-0.062-0.013h-4.614V6.67c0-2.575,2.095-4.67,4.669-4.67h10.277v10.4c0,3.678,2.992,6.67,6.67,6.67h10.399 v21.616C49.524,43.26,47.429,45.355,44.855,45.355z'/%3E%3C/svg%3E%0A";

let deleteImg, cloneImg;

// Module loader utility
async function loadAdminModule(moduleName) {
    if (AdminModules.loaded.has(moduleName)) {
        return;
    }
    
    try {
        const script = document.createElement('script');
        script.src = `/static/js/admin/modules/${moduleName}.js`;
        script.async = true; // Load scripts asynchronously
        
        return new Promise((resolve, reject) => {
            script.onload = () => {
                AdminModules.loaded.add(moduleName);
                resolve();
            };
            script.onerror = () => {
                reject(new Error(`Failed to load module: ${moduleName}`));
            };
            document.head.appendChild(script);
        });
    } catch (error) {
        console.error(`Error loading admin module ${moduleName}:`, error);
        throw error;
    }
}

// Load web components
async function loadWebComponents() {
    // Load shared styles first
    try {
        const sharedStylesScript = document.createElement('script');
        sharedStylesScript.src = '/static/js/admin/components/shared-styles.js';
        sharedStylesScript.async = false; // Load synchronously to ensure it's available
        
        await new Promise((resolve, reject) => {
            sharedStylesScript.onload = resolve;
            sharedStylesScript.onerror = reject;
            document.head.appendChild(sharedStylesScript);
        });
        
        console.log('🎨 Shared styles loaded successfully');
    } catch (error) {
        console.error('❌ Failed to load shared styles:', error);
    }
    
    const components = ['dashboard-card', 'dashboard-chart', 'oidc-provider-manager', 'claims-mapping-manager', 'backup-manager', 'timezone-manager', 'email-manager'];
    
    for (const component of components) {
        try {
            const script = document.createElement('script');
            script.src = `/static/js/admin/components/${component}.js`;
            script.async = true;
            
            await new Promise((resolve, reject) => {
                script.onload = () => {
                    console.log(`✅ Web component script loaded: ${component}`);
                    resolve();
                };
                script.onerror = () => {
                    console.error(`❌ Failed to load component script: ${component}`);
                    reject(new Error(`Failed to load component: ${component}`));
                };
                document.head.appendChild(script);
            });
            
            console.log(`📦 Web component registered: ${component}`);
            
            // Verify the custom element is actually defined
            setTimeout(() => {
                const isDefined = customElements.get(component);
                console.log(`🔍 Custom element '${component}' defined:`, !!isDefined);
            }, 100);
        } catch (error) {
            console.error(`Error loading web component ${component}:`, error);
        }
    }
}

// Initialize admin functionality
async function initAdmin() {
    console.log('Admin.js main initialization...');
    
    try {
        // Load core components first
        await loadAdminModule('api-client');
        await loadAdminModule('notifications');
        
        // Load web components for dashboard
        await loadWebComponents();
        
        setupAdminEventListeners();
        await initializeControlImages();
        
        console.log('Admin main initialized successfully!');
    } catch (error) {
        console.error('Failed to initialize admin:', error);
    }
}

// Setup admin event listeners to handle lazy loading of modules and data
function setupAdminEventListeners() {
    const tabsConfig = [
        { id: 'dashboard-tab', module: 'dashboard', objectName: 'AdminDashboard', load: () => window.AdminDashboard.init() },
        { id: 'users-tab', module: 'users', objectName: 'AdminUsers', load: () => window.AdminUsers.loadUsers() },
        { id: 'bookings-tab', module: 'bookings', objectName: 'AdminBookings', load: () => window.AdminBookings.ensureInitialized() },
        { id: 'oidc-claims-tab', module: 'oidc-claims', objectName: 'AdminOIDCClaims', load: async () => {
            // Web components will auto-load their data, but ensure module is loaded
            console.log('OIDC & Claims tab activated - ensuring module and web components are ready');
            
            // Ensure the AdminOIDCClaims module is properly initialized
            if (window.AdminOIDCClaims && typeof window.AdminOIDCClaims.ensureInitialized === 'function') {
                window.AdminOIDCClaims.ensureInitialized();
            }
            
            // Give web components a moment to initialize if they haven't already
            await new Promise(resolve => setTimeout(resolve, 100));
            
            // Check if web components loaded successfully, if not provide manual refresh option
            setTimeout(() => {
                const oidcProvider = document.querySelector('oidc-provider-manager');
                const claimsManager = document.querySelector('claims-mapping-manager');
                
                if (oidcProvider && claimsManager) {
                    const providerContent = oidcProvider.shadowRoot?.getElementById('providers-content');
                    const claimsContent = claimsManager.shadowRoot?.getElementById('mappings-content');
                    
                    const hasError = (providerContent?.textContent?.includes('Failed to load') || 
                                    providerContent?.textContent?.includes('Error loading') ||
                                    claimsContent?.textContent?.includes('Failed to load') || 
                                    claimsContent?.textContent?.includes('Error loading'));
                    
                    if (hasError) {
                        console.log('OIDC & Claims components had loading errors, user can use refresh buttons');
                        if (window.AdminNotifications) {
                            window.AdminNotifications.showWarning('Some OIDC & Claims data failed to load. Use the Refresh buttons to retry.');
                        }
                    }
                }
            }, 2000);
        }},
        { id: 'parking-lots-tab', module: 'parking-lots', objectName: 'AdminParkingLots', load: () => window.AdminParkingLots.loadParkingLotsAdmin() },
        { id: 'parking-spaces-tab', module: 'parking-spaces', objectName: 'AdminParkingSpaces', load: () => {
            window.AdminParkingSpaces.loadParkingLotsForSpaces();
            window.AdminParkingSpaces.initializeAdminCanvas();
        }},
        { id: 'logs-tab', module: 'logs', objectName: 'AdminLogs', load: () => {
            window.AdminLogs.loadLogs();
            window.AdminLogs.loadLoggerNames();
        }},
        { id: 'dynamic-reports-tab', module: 'dynamic-reports', objectName: 'AdminDynamicReports', load: () => {
            window.AdminDynamicReports.loadDynamicReportsData();
            window.AdminDynamicReports.loadReportTemplates();
        }},
        { id: 'branding-tab', module: 'styling', objectName: 'AdminStyling', load: () => {
            // The AdminStyling module will automatically load settings in its constructor
            console.log('Branding & Styling tab activated');
        }},
        { id: 'system-tab', modules: [], objectNames: [], load: async () => {
            // All system functionality now handled by web components
            // backup-manager, timezone-manager, and email-manager will auto-initialize
            console.log('🔧 System tab loaded - checking for web components...');
            
            // Check if web components are present in DOM
            const backupManager = document.querySelector('backup-manager');
            const timezoneManager = document.querySelector('timezone-manager');
            const emailManager = document.querySelector('email-manager');
            
            console.log('🔍 Web components in DOM:', {
                backupManager: !!backupManager,
                timezoneManager: !!timezoneManager,
                emailManager: !!emailManager
            });
            
            if (backupManager) console.log('🔧 backup-manager element found');
            if (timezoneManager) console.log('🕐 timezone-manager element found');
            if (emailManager) console.log('📧 email-manager element found');

            // Ensure AdminBackup module's event listeners are attached
            if (window.AdminBackup && typeof window.AdminBackup.ensureInitialized === 'function') {
                window.AdminBackup.ensureInitialized();
            }
        }}
    ];

    const exposeModuleFunctions = (moduleObject) => {
        if (!moduleObject) return;
        for (const key in moduleObject) {
            if (typeof moduleObject[key] === 'function') {
                window[key] = moduleObject[key].bind(moduleObject);
            }
        }
    };

    // Enhanced module loading with proper error handling and timing
    const loadTabData = async (tabConfig) => {
        if (!tabConfig) {
            console.warn('🔄 [AdminMain] loadTabData called with null/undefined tabConfig');
            return;
        }

        console.log(`🔄 [AdminMain] Loading tab data for module: ${tabConfig.module}`);
        console.log(`🔄 [AdminMain] Tab config:`, tabConfig);
        
        try {
            // Handle multi-module tabs (like system tab) or single module tabs
            const modules = tabConfig.modules || [tabConfig.module];
            const objectNames = tabConfig.objectNames || [tabConfig.objectName];
            const primaryModule = modules[0];
            
            // Show loading state
            showLoadingState(primaryModule);
            
            // Load all module scripts
            for (const moduleName of modules) {
                console.log(`🔄 [AdminMain] Loading module script: ${moduleName}`);
                await loadAdminModule(moduleName);
                console.log(`🔄 [AdminMain] Module script loaded: ${moduleName}`);
            }
            
            // Wait for all module objects to be available
            const moduleObjects = [];
            for (const objectName of objectNames) {
                console.log(`🔄 [AdminMain] Waiting for module object: ${objectName}`);
                const moduleObject = await waitForModuleObject(objectName, 5000);
                
                if (moduleObject) {
                    console.log(`🔄 [AdminMain] ✅ Module ${objectName} loaded successfully`);
                    console.log(`🔄 [AdminMain] Module object methods:`, Object.getOwnPropertyNames(moduleObject).filter(name => typeof moduleObject[name] === 'function'));
                    
                    // Expose module functions globally
                    exposeModuleFunctions(moduleObject);
                    moduleObjects.push(moduleObject);
                } else {
                    throw new Error(`Module object ${objectName} not found after loading script`);
                }
            }
            
            // Store module references
            modules.forEach((moduleName, index) => {
                if (!AdminModules.modules[moduleName]) {
                    AdminModules.modules[moduleName] = moduleObjects[index];
                }
            });
            
            // Wait a bit more to ensure modules are fully initialized
            console.log(`🔄 [AdminMain] Waiting for module initialization: ${primaryModule}`);
            await new Promise(resolve => setTimeout(resolve, 100));
            
            // Ensure module event listeners are set up for all modules
            moduleObjects.forEach((moduleObject, index) => {
                if (typeof moduleObject.ensureInitialized === 'function') {
                    console.log(`🔄 [AdminMain] Ensuring initialization for ${objectNames[index]}`);
                    moduleObject.ensureInitialized();
                } else {
                    console.log(`🔄 [AdminMain] No ensureInitialized method found for ${objectNames[index]}`);
                }
            });
            
            // Special debug for parking lots
            if (primaryModule === 'parking-lots') {
                console.log('🚗 [AdminMain] PARKING LOTS DEBUG:');
                console.log('🚗 [AdminMain] - window.AdminParkingLots:', window.AdminParkingLots);
                console.log('🚗 [AdminMain] - window.AdminAPI:', window.AdminAPI);
                console.log('🚗 [AdminMain] - window.AdminAPI.parkingLots:', window.AdminAPI?.parkingLots);
                console.log('🚗 [AdminMain] - DOM element check:');
                console.log('🚗 [AdminMain]   - parking-lots-admin-table-body:', document.getElementById('parking-lots-admin-table-body'));
                console.log('🚗 [AdminMain]   - refresh-parking-lots-btn:', document.getElementById('refresh-parking-lots-btn'));
                console.log('🚗 [AdminMain]   - add-parking-lot-btn:', document.getElementById('add-parking-lot-btn'));
            }
            
            // Execute the load function
            if (tabConfig.load) {
                console.log(`🔄 [AdminMain] Executing load function for ${primaryModule}`);
                
                // Special handling for parking lots
                if (primaryModule === 'parking-lots') {
                    console.log('🚗 [AdminMain] About to call window.AdminParkingLots.loadParkingLotsAdmin()');
                    console.log('🚗 [AdminMain] Function exists:', typeof window.AdminParkingLots.loadParkingLotsAdmin);
                }
                
                await tabConfig.load();
                console.log(`🔄 [AdminMain] ✅ Data loading completed for ${primaryModule}`);
            } else {
                console.log(`🔄 [AdminMain] No load function defined for ${primaryModule}`);
            }
            
            // Clear loading state
            clearLoadingState(primaryModule);
        } catch (error) {
            console.error(`🔄 [AdminMain] ❌ Failed to load tab data for module ${tabConfig.module}:`, error);
            console.error(`🔄 [AdminMain] Error stack:`, error.stack);
            showErrorState(tabConfig.module, error.message);
            
            // Show user-friendly error message
            if (window.AdminNotifications) {
                window.AdminNotifications.showError(`Failed to load ${tabConfig.module}: ${error.message}`);
            }
        }
    };

    // Wait for module object to be available
    const waitForModuleObject = (objectName, timeout = 5000) => {
        return new Promise((resolve, reject) => {
            const startTime = Date.now();
            
            const checkForObject = () => {
                if (window[objectName]) {
                    resolve(window[objectName]);
                } else if (Date.now() - startTime > timeout) {
                    reject(new Error(`Timeout waiting for ${objectName} to be available`));
                } else {
                    setTimeout(checkForObject, 50);
                }
            };
            
            checkForObject();
        });
    };

    // Show loading state for a module
    const showLoadingState = (moduleName) => {
        const tabContent = getTabContentElement(moduleName);
        if (tabContent) {
            const loadingElement = tabContent.querySelector('.loading-indicator');
            if (!loadingElement) {
                const loading = document.createElement('div');
                loading.className = 'loading-indicator text-center p-3';
                loading.innerHTML = `
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                    <p class="mt-2">Loading ${moduleName}...</p>
                `;
                tabContent.insertBefore(loading, tabContent.firstChild);
            }
        }
    };

    // Clear loading state
    const clearLoadingState = (moduleName) => {
        const tabContent = getTabContentElement(moduleName);
        if (tabContent) {
            const loadingElement = tabContent.querySelector('.loading-indicator');
            if (loadingElement) {
                loadingElement.remove();
            }
        }
    };

    // Show error state
    const showErrorState = (moduleName, errorMessage) => {
        clearLoadingState(moduleName);
        const tabContent = getTabContentElement(moduleName);
        if (tabContent) {
            const errorElement = document.createElement('div');
            errorElement.className = 'alert alert-danger error-indicator';
            errorElement.innerHTML = `
                <h6>Error loading ${moduleName}</h6>
                <p>${errorMessage}</p>
                <button class="btn btn-sm btn-outline-danger" onclick="location.reload()">Reload Page</button>
            `;
            tabContent.insertBefore(errorElement, tabContent.firstChild);
        }
    };

    // Get tab content element for a module
    const getTabContentElement = (moduleName) => {
        const tabMapping = {
            'dashboard': 'dashboard-pane',
            'users': 'users-pane',
            'bookings': 'bookings-pane',
            'oidc-claims': 'oidc-claims-pane',
            'parking-lots': 'parking-lots-pane',
            'parking-spaces': 'parking-spaces-pane',
            'email-settings': 'email-pane',
            'timezone-settings': 'timezone-pane',
            'logs': 'logs-pane',
            'dynamic-reports': 'dynamic-reports-pane',
            'styling': 'branding-pane',
        };
        
        const paneId = tabMapping[moduleName] || 'system-pane';
        return paneId ? document.getElementById(paneId) : null;
    };

    // Set up tab event listeners
    tabsConfig.forEach(tabConfig => {
        const element = document.getElementById(tabConfig.id);
        if (element) {
            element.addEventListener('show.bs.tab', () => {
                console.log(`Tab activated: ${tabConfig.id}`);
                loadTabData(tabConfig);
            });
        } else {
            console.warn(`Tab element not found: ${tabConfig.id}`);
        }
    });

    // Load data for the initially active tab
    const activeTabElement = document.querySelector('#adminTabs .nav-link.active');
    if (activeTabElement) {
        const activeTabConfig = tabsConfig.find(t => t.id === activeTabElement.id);
        if (activeTabConfig) {
            console.log(`Loading initial active tab: ${activeTabConfig.id}`);
            setTimeout(() => loadTabData(activeTabConfig), 100);
        }
    }
}

// Initialize control images
function initializeControlImages() {
    return new Promise((resolve) => {
        let loadedCount = 0;
        const totalImages = 2;
        
        const checkComplete = () => {
            loadedCount++;
            if (loadedCount === totalImages) {
                resolve();
            }
        };
        
        deleteImg = document.createElement('img');
        deleteImg.onload = checkComplete;
        deleteImg.onerror = () => {
            console.warn('Failed to load delete icon, using fallback');
            checkComplete();
        };
        deleteImg.src = deleteIcon;
        
        cloneImg = document.createElement('img');
        cloneImg.onload = checkComplete;
        cloneImg.onerror = () => {
            console.warn('Failed to load clone icon, using fallback');
            checkComplete();
        };
        cloneImg.src = cloneIcon;
    });
}

// Shared utilities
function showAdminStatus(message, type = 'secondary') {
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

// Export shared utilities and variables for modules
window.AdminCore = {
    adminCanvas,
    adminCurrentTool,
    adminSelectedSpace,
    adminCurrentLot,
    adminSpaces,
    adminIsDrawing,
    adminStartPoint,
    adminTempRect,
    isDrawingMode,
    drawingRect,
    startPointer,
    nextSpaceNumber,
    deleteImg,
    cloneImg,
    deleteIcon,
    cloneIcon,
    showAdminStatus,
    loadAdminModule
};

// Export initAdmin function globally for auth system to call
window.initAdmin = initAdmin;

// Do NOT auto-initialize - wait for auth system to call us
console.log('🔧 [AdminMain] Admin main module loaded! Waiting for authenticated admin user...');
