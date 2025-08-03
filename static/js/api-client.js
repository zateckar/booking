/* API Client - Centralized API handling for the booking system */

const API = {
    async makeAuthenticatedRequest(url, options = {}) {
        const token = localStorage.getItem('access_token');
        const headers = { ...options.headers };

        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        // Properly handle body and Content-Type
        let body = options.body;
        if (body && typeof body === 'object' && !(body instanceof FormData)) {
            body = JSON.stringify(body);
            if (!headers['Content-Type']) {
                headers['Content-Type'] = 'application/json';
            }
        }

        const response = await fetch(url, {
            ...options,
            headers,
            body,
            credentials: 'include'
        });

        // If we get a 401 (Unauthorized), try to refresh the token and retry
        if (response.status === 401 && !window.auth.isRefreshing()) {
            AdminLogs.log('INFO', `API request to ${url} returned 401, attempting token refresh...`);

            await window.auth.refreshAccessToken();

            // Retry the request with the new token
            const newToken = localStorage.getItem('access_token');
            if (newToken && newToken !== token) {
                AdminLogs.log('INFO', `Retrying API request to ${url} with refreshed token...`);
                headers['Authorization'] = `Bearer ${newToken}`;

                return fetch(url, {
                    ...options,
                    headers,
                    credentials: 'include'
                });
            }
        }

        return response;
    }
};

window.API = API;
