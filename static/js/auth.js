/* Authentication module for Parking Booking System */

// Stub for AdminLogs to prevent errors if the admin module is not loaded
if (typeof window.AdminLogs === 'undefined') {
    window.queuedLogs = [];
    window.AdminLogs = {
        log: function(level, message, ...args) {
            window.queuedLogs.push({ level, message, args });
        }
    };
}

let currentUser = null;
let tokenRefreshTimer = null;
let isRefreshing = false;
let currentView = 'booking'; // Track current view: 'booking' or 'admin'

// DOM elements
const header = document.getElementById('header');
const userEmail = document.getElementById('user-email');
const logoutLink = document.getElementById('logout-link');
const loginFormContainer = document.getElementById('login-form-container');
const loginForm = document.getElementById('login-form');
const emailInput = document.getElementById('email');
const passwordInput = document.getElementById('password');
const mainContent = document.getElementById('main-content');

// Initialize authentication
function initAuth() {
    if (loginForm) {
        loginForm.addEventListener('submit', handleLogin);
    }
    
    if (logoutLink) {
        logoutLink.addEventListener('click', handleLogout);
    }

    // Always try to setup UI on page load
    setupUI();
    fetchOidcProvidersForLogin();
}

// Handle login form submission
async function handleLogin(event) {
    event.preventDefault();
    const email = emailInput.value;
    const password = passwordInput.value;

    const response = await fetch('/api/token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: `username=${encodeURIComponent(email)}&password=${encodeURIComponent(password)}`,
    });

    if (response.ok) {
        const data = await response.json();
        localStorage.setItem('access_token', data.access_token);
        if (data.refresh_token) {
            localStorage.setItem('refresh_token', data.refresh_token);
        }
        
        // Start token refresh monitoring
        startTokenRefreshTimer();
        
        // Redirect to main app after successful login
        window.location.href = '/app';
    } else {
        const errorData = await response.json().catch(() => ({}));
        const errorMessage = errorData.detail || 'Login failed';
        
        // Show error message
        const alertDiv = document.createElement('div');
        alertDiv.className = 'alert alert-danger alert-dismissible fade show mt-3';
        alertDiv.innerHTML = `
            <strong>Login Failed:</strong> ${errorMessage}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        if (loginForm) {
            loginForm.parentNode.insertBefore(alertDiv, loginForm.nextSibling);
            
            // Auto-dismiss after 5 seconds
            setTimeout(() => {
                if (alertDiv.parentNode) {
                    alertDiv.remove();
                }
            }, 5000);
        }
    }
}

// Handle logout
async function handleLogout() {
    // Stop token refresh timer
    stopTokenRefreshTimer();
    
    // Stop all admin timers and cleanup
    cleanupAdminTimers();
    
    try {
        // Call the logout endpoint to clear HttpOnly cookies
        const token = localStorage.getItem('access_token');
        const headers = {};
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }
        
        const response = await fetch('/api/logout', {
            method: 'POST',
            headers: headers,
            credentials: 'include' // Important to include cookies
        });
        
        if (response.ok) {
            const data = await response.json();
            
            // Check if this is an OIDC logout with redirect URL
            if (data.redirect_url) {
                AdminLogs.log('INFO', 'OIDC logout detected, redirecting to:', data.redirect_url);
                
                // Clear localStorage tokens before redirecting to OIDC provider
                localStorage.removeItem('access_token');
                localStorage.removeItem('refresh_token');
                currentUser = null;
                
                // Redirect to OIDC provider's logout endpoint
                window.location.href = data.redirect_url;
                return; // Don't execute the rest of the function
            }
        }
    } catch (error) {
        AdminLogs.log('WARNING', 'Logout endpoint call failed, but proceeding with local cleanup');
    }
    
    // Standard local logout cleanup
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    currentUser = null;
    
    // Redirect to root which will handle the appropriate login flow
    window.location.href = '/';
}

// Enhanced setupUI function to work with both localStorage tokens and HttpOnly cookies
async function setupUI() {
    AdminLogs.log('DEBUG', 'setupUI: Starting authentication check');
    
    try {
        // Try to authenticate - the backend will check both Authorization header and cookies
        const token = localStorage.getItem('access_token');
        const headers = {};
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
            AdminLogs.log('DEBUG', 'setupUI: Using localStorage token');
        } else {
            AdminLogs.log('DEBUG', 'setupUI: No localStorage token, relying on cookies');
        }

        const response = await fetch('/api/users/me?include_parking_lots=true', {
            headers: headers,
            credentials: 'include' // IMPORTANT: include cookies in the request
        });

        AdminLogs.log('DEBUG', 'setupUI: Auth response status:', response.status);

        if (!response.ok) {
            // Authentication failed - clear any stored token and show login
            AdminLogs.log('INFO', 'setupUI: Authentication failed, showing login form');
            localStorage.removeItem('access_token');
            header.style.display = 'none';
            mainContent.style.display = 'none';
            loginFormContainer.style.display = 'block';
            return;
        }

        currentUser = await response.json();
        AdminLogs.log('INFO', 'setupUI: Successfully authenticated user:', currentUser.email, 'Admin:', currentUser.is_admin);
        userEmail.textContent = currentUser.email;

        AdminLogs.log('DEBUG', 'setupUI: Switching to authenticated UI');
        loginFormContainer.style.display = 'none';
        mainContent.style.display = 'block';
        header.style.display = 'flex';

        // Start token refresh monitoring if we have a token
        if (localStorage.getItem('access_token')) {
            startTokenRefreshTimer();
        }
        
        // Trigger navigation setup
        setupNavigation();
        
        // Initialize the default view
        if (window.updateView) {
            updateView();
        }
        if (window.setupResponsiveCanvases) {
            setupResponsiveCanvases();
        }
        
        // Load styling settings after successful authentication
        loadStylingSettings();
        
        AdminLogs.log('INFO', 'setupUI: UI setup completed successfully');
    } catch (error) {
        AdminLogs.log('ERROR', 'setupUI: Error during authentication check:', error);
        // On error, show login form
        localStorage.removeItem('access_token');
        header.style.display = 'none';
        mainContent.style.display = 'none';
        loginFormContainer.style.display = 'block';
    }
}

// Setup navigation handlers
function setupNavigation() {
    const userModeLink = document.getElementById('user-mode-link');
    const adminModeLink = document.getElementById('admin-mode-link');
    
    if (userModeLink) {
        userModeLink.addEventListener('click', () => {
            currentView = 'booking';
            document.getElementById('user-view').style.display = 'block';
            document.getElementById('user-booking-view').style.display = 'block';
            document.getElementById('admin-view').style.display = 'none';
            userModeLink.classList.add('active');
            adminModeLink.classList.remove('active');
            updateNavbarVisibility();
        });
    }

    if (adminModeLink) {
        adminModeLink.addEventListener('click', async () => {
            if (currentUser && currentUser.is_admin) {
                AdminLogs.log('INFO', '🔧 [Auth] Admin mode activated, loading admin system...');
                
                currentView = 'admin';
                document.getElementById('user-view').style.display = 'none';
                document.getElementById('user-booking-view').style.display = 'none';
                document.getElementById('admin-view').style.display = 'block';
                userModeLink.classList.remove('active');
                adminModeLink.classList.add('active');
                
                // Update admin view with current user info
                document.getElementById('admin-current-user').textContent = currentUser.email;
                const sessionType = localStorage.getItem('access_token') ? 'Local Storage Token' : 'HttpOnly Cookie';
                document.getElementById('session-type').textContent = sessionType;
                
                updateNavbarVisibility();
                
                // Load and initialize admin system
                await loadAdminSystemIfNeeded();
            }
        });
    }
    
    // Initial navbar setup
    updateNavbarVisibility();
}

// Update navbar visibility based on current view and user role
function updateNavbarVisibility() {
    const userModeLink = document.getElementById('user-mode-link');
    const adminModeLink = document.getElementById('admin-mode-link');
    
    if (!currentUser || !userModeLink || !adminModeLink) return;
    
    if (!currentUser.is_admin) {
        // Regular users: Hide both links (they're automatically on booking page)
        userModeLink.style.display = 'none';
        adminModeLink.style.display = 'none';
    } else {
        // Admin users: Show contextual navigation
        if (currentView === 'booking') {
            // On booking view: Show only "Admin" link
            userModeLink.style.display = 'none';
            adminModeLink.style.display = 'block';
            adminModeLink.textContent = 'Admin';
        } else {
            // On admin view: Show only "Bookings" link
            userModeLink.style.display = 'block';
            adminModeLink.style.display = 'none';
            userModeLink.textContent = 'My Bookings';
        }
    }
}

// Fetch OIDC providers for login page
async function fetchOidcProvidersForLogin() {
    const buttonsContainer = document.getElementById('oidc-login-buttons');
    if (!buttonsContainer) return;
    
    // Check if there are already server-side rendered buttons
    const existingButtons = buttonsContainer.querySelectorAll('a[href^="/oidc/login/"]');
    if (existingButtons.length > 0) {
        // Server-side buttons already exist, no need to fetch
        return;
    }
    
    try {
        const response = await fetch('/oidc/providers');
        if (response.ok) {
            const providers = await response.json();
            
            if (providers.length > 0) {
                const divider = document.createElement('hr');
                divider.className = 'my-3';
                buttonsContainer.appendChild(divider);
                
                const title = document.createElement('p');
                title.className = 'text-muted mb-2';
                title.textContent = 'Or login with:';
                buttonsContainer.appendChild(title);
                
                providers.forEach(provider => {
                    const button = document.createElement('a');
                    button.href = `/oidc/login/${provider.id}`;
                    button.className = 'btn btn-primary me-2 mb-2';
                    button.textContent = `${provider.display_name}`;
                    buttonsContainer.appendChild(button);
                });
            }
        }
    } catch (error) {
        AdminLogs.log('ERROR', 'Error fetching OIDC providers:', error);
    }
}

// Token refresh management

/**
 * Decodes a JWT token and checks if it's expiring within a given buffer.
 * @param {string} token - The JWT token.
 * @param {number} bufferMinutes - The buffer in minutes.
 * @returns {boolean} - True if the token is expiring soon or is invalid.
 */
function isTokenExpiringSoonClientSide(token, bufferMinutes = 10) {
    if (!token) return true;

    try {
        const payloadBase64 = token.split('.')[1];
        if (!payloadBase64) return true;

        const decodedPayload = JSON.parse(atob(payloadBase64));
        const exp = decodedPayload.exp;
        if (!exp) return true;

        const expirationTime = new Date(exp * 1000);
        const bufferTime = new Date();
        bufferTime.setMinutes(bufferTime.getMinutes() + bufferMinutes);

        return bufferTime >= expirationTime;
    } catch (error) {
        AdminLogs.log('ERROR', 'Failed to decode or check token expiration on client-side:', error);
        return true; // Assume it needs refresh on error
    }
}

function startTokenRefreshTimer() {
    AdminLogs.log('DEBUG', 'Starting token refresh timer...');
    stopTokenRefreshTimer(); // Clear any existing timer
    
    // Check token status every 2 minutes
    tokenRefreshTimer = setInterval(checkAndRefreshToken, 2 * 60 * 1000);
    
    // Also check immediately
    setTimeout(checkAndRefreshToken, 1000);
}

function stopTokenRefreshTimer() {
    if (tokenRefreshTimer) {
        AdminLogs.log('DEBUG', 'Stopping token refresh timer...');
        clearInterval(tokenRefreshTimer);
        tokenRefreshTimer = null;
    }
}

async function checkAndRefreshToken() {
    if (isRefreshing) {
        AdminLogs.log('DEBUG', 'Token refresh already in progress, skipping...');
        return;
    }

    const token = localStorage.getItem('access_token');
    if (!token) {
        AdminLogs.log('DEBUG', 'No access token found, stopping refresh timer');
        stopTokenRefreshTimer();
        return;
    }

    // **New:** Proactive client-side check with a 10-minute buffer
    if (isTokenExpiringSoonClientSide(token, 10)) {
        AdminLogs.log('INFO', 'Token expiring soon based on client-side check, refreshing proactively.');
        await refreshAccessToken();
        return; // Refresh initiated, no need to call the API endpoint
    }

    // If client-side check passes, still perform the server-side check as a fallback
    try {
        AdminLogs.log('DEBUG', 'Client-side check passed, now checking token status with server...');
        const response = await fetch('/api/check-token', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            credentials: 'include'
        });

        if (response.ok) {
            const data = await response.json();
            AdminLogs.log('DEBUG', 'Server token status:', data);

            if (data.needs_refresh) {
                AdminLogs.log('INFO', `Server indicates token needs refresh: ${data.reason}`);
                await refreshAccessToken();
            } else {
                AdminLogs.log('DEBUG', 'Server confirms token is still valid');
            }
        } else {
            AdminLogs.log('WARNING', 'Failed to check token status with server, attempting refresh as a precaution...');
            await refreshAccessToken();
        }
    } catch (error) {
        AdminLogs.log('ERROR', 'Error during server-side token status check:', error);
        // Attempt to refresh token on error as a fallback
        await refreshAccessToken();
    }
}

async function refreshAccessToken() {
    if (isRefreshing) {
        AdminLogs.log('DEBUG', 'Token refresh already in progress');
        return;
    }
    
    isRefreshing = true;
    AdminLogs.log('INFO', 'Attempting to refresh access token...');
    
    try {
        const refreshToken = localStorage.getItem('refresh_token');
        if (!refreshToken) {
            AdminLogs.log('WARNING', 'No refresh token available, redirecting to login');
            await handleSessionExpired();
            return;
        }
        
        const response = await fetch('/api/refresh', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${refreshToken}`
            },
            credentials: 'include'
        });
        
        if (response.ok) {
            const data = await response.json();
            AdminLogs.log('INFO', 'Token refreshed successfully');
            
            // Update stored access token
            localStorage.setItem('access_token', data.access_token);
            
            // Continue monitoring
            AdminLogs.log('DEBUG', 'Token refresh completed, continuing monitoring...');
        } else {
            AdminLogs.log('WARNING', 'Token refresh failed, session expired');
            await handleSessionExpired();
        }
    } catch (error) {
        AdminLogs.log('ERROR', 'Error refreshing token:', error);
        await handleSessionExpired();
    } finally {
        isRefreshing = false;
    }
}

async function handleSessionExpired() {
    AdminLogs.log('INFO', 'Session expired, redirecting to login...');
    
    stopTokenRefreshTimer();
    
    // Stop all admin timers and cleanup
    cleanupAdminTimers();
    
    // Clear stored tokens
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    
    // Reset UI state
    currentUser = null;
    
    // Show login form
    if (header) header.style.display = 'none';
    if (mainContent) mainContent.style.display = 'none';
    if (loginFormContainer) loginFormContainer.style.display = 'block';
    
    // Show user-friendly message
    const alertDiv = document.createElement('div');
    alertDiv.className = 'alert alert-warning alert-dismissible fade show';
    alertDiv.innerHTML = `
        <strong>Session Expired</strong> Your session has expired. Please log in again.
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    if (loginFormContainer) {
        loginFormContainer.insertBefore(alertDiv, loginFormContainer.firstChild);
        
        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, 5000);
    }
}

// Check if user is authenticated
function isAuthenticated() {
    return currentUser !== null;
}

// Check if current user is admin
function isAdmin() {
    return currentUser && currentUser.is_admin;
}

// Get current user
function getCurrentUser() {
    return currentUser;
}

// Load and apply styling settings
async function loadStylingSettings() {
    try {
        // Load public styling info that doesn't require authentication
        const response = await fetch('/api/admin/styling-settings/public-info');
        if (response.ok) {
            const settings = await response.json();
            
            // Update navbar brand text
            const navbarBrandText = document.getElementById('navbar-brand-text');
            if (navbarBrandText && settings.navbar_brand_text) {
                navbarBrandText.textContent = settings.navbar_brand_text;
            }
            
            // Update login title
            const loginTitle = document.getElementById('login-title');
            if (loginTitle && settings.navbar_brand_text) {
                loginTitle.textContent = settings.navbar_brand_text;
            }
            
            // Update logos if they exist and styling is enabled
            if (settings.enabled && settings.logo_path) {
                const navbarLogo = document.getElementById('navbar-logo');
                const loginLogo = document.getElementById('login-logo');
                
                if (navbarLogo && settings.show_logo_in_navbar) {
                    navbarLogo.src = settings.logo_path;
                    navbarLogo.alt = settings.logo_alt_text || 'Company Logo';
                    navbarLogo.style.display = 'inline-block';
                    navbarLogo.style.maxHeight = `${settings.logo_max_height || 50}px`;
                }
                
                if (loginLogo && settings.show_logo_on_login) {
                    loginLogo.src = settings.logo_path;
                    loginLogo.alt = settings.logo_alt_text || 'Company Logo';
                    loginLogo.style.display = 'block';
                }
            }
            
            AdminLogs.log('INFO', '✅ Styling settings applied to UI elements');
        } else {
            AdminLogs.log('INFO', 'ℹ️ Could not load public styling info, using defaults');
        }
    } catch (error) {
        AdminLogs.log('WARNING', 'Styling settings not available:', error.message);
    }
}

// Initialize auth when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    initAuth();
    // Load styling settings immediately for login page and other public areas
    loadStylingSettings();
});

// Cleanup admin timers when logging out
function cleanupAdminTimers() {
    AdminLogs.log('DEBUG', 'Cleaning up admin timers...');
    
    // Stop dashboard auto-refresh timer
    if (window.AdminDashboard && typeof window.AdminDashboard.stopAutoRefresh === 'function') {
        window.AdminDashboard.stopAutoRefresh();
    }
    
    // Add cleanup for other admin modules with timers if any
    // This can be extended as more modules with timers are added
    
    AdminLogs.log('DEBUG', 'Admin timers cleanup completed');
}

// Function to load admin system when needed
async function loadAdminSystemIfNeeded() {
    AdminLogs.log('DEBUG', '🔧 [Auth] loadAdminSystemIfNeeded called');
    
    if (!currentUser || !currentUser.is_admin) {
        AdminLogs.log('DEBUG', '🔧 [Auth] User is not admin, skipping admin system load');
        return;
    }
    
    // Check if AdminLoader is available
    if (!window.AdminLoader) {
        AdminLogs.log('DEBUG', '🔧 [Auth] AdminLoader not available, admin system may not be loaded yet');
        return;
    }
    
    // Load admin system if not already loaded
    if (!window.AdminLoader.isLoaded()) {
        AdminLogs.log('INFO', '🔧 [Auth] Loading admin system...');
        window.AdminLoader.loadAdminSystem();
        
        // Wait for the admin system to be loaded
        let attempts = 0;
        while (attempts < 50 && (!window.initAdmin || !window.AdminLoader.isLoaded())) {
            await new Promise(resolve => setTimeout(resolve, 100));
            attempts++;
        }
        
        if (window.initAdmin) {
            AdminLogs.log('INFO', '🔧 [Auth] Admin system loaded successfully');
        } else {
            AdminLogs.log('ERROR', '🔧 [Auth] Failed to load admin system after waiting');
            return;
        }
    }
    
    // Initialize admin system if not already initialized
    if (!window.AdminLoader.isInitialized()) {
        AdminLogs.log('INFO', '🔧 [Auth] Initializing admin system...');
        window.AdminLoader.initializeAdminForUser();
    } else {
        AdminLogs.log('DEBUG', '🔧 [Auth] Admin system already initialized');
    }
}

// Export functions for use in other modules
window.auth = {
    isAuthenticated,
    isAdmin,
    getCurrentUser,
    setupUI,
    cleanupAdminTimers,
    loadAdminSystemIfNeeded,
    loadStylingSettings,
    refreshAccessToken,
    isRefreshing: () => isRefreshing
};

// Also expose loadStylingSettings globally for easy access
window.loadStylingSettings = loadStylingSettings;
