/* Admin.js - Loads the modular admin system ONLY when user is authenticated as admin */

console.log('🚀 [Admin.js] Admin.js loader executed!');

let adminSystemLoaded = false;
let adminInitialized = false;

// Function to load admin system - only called when user is confirmed admin
function loadAdminSystem() {
    if (adminSystemLoaded) {
        console.log('🚀 [Admin.js] Admin system already loaded, skipping...');
        return;
    }
    
    console.log('🚀 [Admin.js] Loading modular admin system for authenticated admin user...');
    adminSystemLoaded = true;
    
    try {
        // Load the main admin module, which handles all admin functionality
        const adminMainScript = document.createElement('script');
        adminMainScript.src = '/static/js/admin/core/admin-main.js';
        adminMainScript.async = false; // Ensure it loads before other potential scripts
        
        adminMainScript.onload = () => {
            console.log('🚀 [Admin.js] ✅ admin-main.js loaded successfully');
        };
        
        adminMainScript.onerror = (error) => {
            console.error('🚀 [Admin.js] ❌ Failed to load admin-main.js:', error);
            adminSystemLoaded = false; // Allow retry
        };
        
        console.log('🚀 [Admin.js] Adding admin-main.js script to head...');
        document.head.appendChild(adminMainScript);
        
        console.log('🚀 [Admin.js] Script element created and added');
    } catch (error) {
        console.error('🚀 [Admin.js] Exception while loading admin system:', error);
        adminSystemLoaded = false; // Allow retry
    }
}

// Function to initialize admin when user switches to admin mode
function initializeAdminForUser() {
    if (!adminInitialized && window.initAdmin) {
        console.log('🚀 [Admin.js] Initializing admin system for authenticated admin user...');
        adminInitialized = true;
        window.initAdmin();
    }
}

// Export functions for auth.js to call
window.AdminLoader = {
    loadAdminSystem,
    initializeAdminForUser,
    isLoaded: () => adminSystemLoaded,
    isInitialized: () => adminInitialized
};
