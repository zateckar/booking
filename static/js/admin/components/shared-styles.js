const AdminSharedStyles = {
    getSharedStyles: () => `
        <style>
            :host {
                display: block;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                --primary-color: #007bff;
                --primary-hover-color: #0056b3;
                --secondary-color: #6c757d;
                --success-color: #28a745;
                --danger-color: #dc3545;
                --warning-color: #ffc107;
                --info-color: #17a2b8;
                --light-gray-color: #f8f9fa;
                --medium-gray-color: #dee2e6;
                --dark-gray-color: #343a40;
                --font-color: #212529;
                --card-bg: #ffffff;
                --card-border-color: #e3e6f0;
                --card-shadow: 0 0.15rem 1.75rem 0 rgba(58, 59, 69, 0.15);
                --border-radius: 0.35rem;
            }

            .card {
                background-color: var(--card-bg);
                border: 1px solid var(--card-border-color);
                border-radius: var(--border-radius);
                box-shadow: var(--card-shadow);
                margin-bottom: 1.5rem;
                height: 100%;
            }

            .card-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 0.75rem 1.25rem;
                background-color: var(--light-gray-color);
                border-bottom: 1px solid var(--card-border-color);
            }

            .card-title {
                margin: 0;
                font-size: 1.2rem;
                font-weight: 500;
                color: var(--font-color);
            }

            .card-body {
                padding: 1.5rem;
            }

            .form-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 1.5rem;
            }

            .form-section {
                display: flex;
                flex-direction: column;
                gap: 1rem;
            }

            .form-label {
                font-weight: 500;
                margin-bottom: 0.5rem;
            }

            .form-control, .form-select {
                width: 100%;
                padding: 0.75rem;
                border: 1px solid var(--medium-gray-color);
                border-radius: var(--border-radius);
                font-size: 1rem;
                transition: border-color 0.15s ease-in-out, box-shadow 0.15s ease-in-out;
            }

            .form-control:focus, .form-select:focus {
                border-color: var(--primary-color);
                box-shadow: 0 0 0 0.2rem rgba(0, 123, 255, 0.25);
                outline: none;
            }
            
            .form-check {
                display: flex;
                align-items: center;
                gap: 0.5rem;
            }

            .btn {
                padding: 0.5rem 1rem;
                border: none;
                border-radius: var(--border-radius);
                cursor: pointer;
                font-size: 0.9rem;
                font-weight: 500;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                transition: background-color 0.2s;
            }

            .btn-primary {
                background-color: var(--primary-color);
                color: white;
            }
            .btn-primary:hover {
                background-color: var(--primary-hover-color);
            }

            .btn-success {
                background-color: var(--success-color);
                color: white;
            }

            .btn-warning {
                background-color: var(--warning-color);
                color: var(--dark-gray-color);
            }

            .btn-info {
                background-color: var(--info-color);
                color: white;
            }

            .status-section, .backup-list-section {
                margin-top: 1.5rem;
                padding: 1rem;
                background-color: var(--light-gray-color);
                border-radius: var(--border-radius);
            }

            .status-item {
                display: flex;
                justify-content: space-between;
                padding: 0.5rem 0;
                border-bottom: 1px solid var(--medium-gray-color);
            }
            .status-item:last-child {
                border-bottom: none;
            }

            .list-item {
                padding: 0.75rem;
                background-color: white;
                border: 1px solid var(--medium-gray-color);
                border-radius: var(--border-radius);
                margin-bottom: 0.5rem;
            }
        </style>
    `
};

// Make it globally available
window.AdminSharedStyles = AdminSharedStyles;
