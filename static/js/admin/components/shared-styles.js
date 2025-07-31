/**
 * Shared Styles for Admin Web Components
 * Provides consistent styling that matches the application's Bootstrap theme
 * and ensures responsive design across all components
 */

// Make shared styles available globally for web components
window.AdminSharedStyles = window.AdminSharedStyles || {};

const sharedStyles = `
    <style>
        :host {
            display: block;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, 
                         "Noto Color Emoji", "Apple Color Emoji", "Segoe UI Emoji", 
                         "Segoe UI Symbol", "Noto Emoji", sans-serif;
        }
        
        /* Card Styles - Bootstrap-like */
        .card {
            border: 1px solid #dee2e6;
            border-radius: 0.375rem;
            background: white;
            margin-bottom: 1rem;
            box-shadow: 0 0.125rem 0.25rem rgba(0, 0, 0, 0.075);
        }
        
        .card-header {
            background-color: #f8f9fa;
            border-bottom: 1px solid #dee2e6;
            padding: 1rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-radius: calc(0.375rem - 1px) calc(0.375rem - 1px) 0 0;
        }
        
        .card-body {
            padding: 1rem;
        }
        
        .card-title {
            margin-bottom: 0;
            font-size: 1.25rem;
            font-weight: 500;
        }
        
        /* Form Styles - Bootstrap-like */
        .form-label {
            font-weight: 500;
            margin-bottom: 0.5rem;
            display: block;
            color: #212529;
        }
        
        .form-control, .form-select {
            width: 100%;
            padding: 0.375rem 0.75rem;
            font-size: 1rem;
            font-weight: 400;
            line-height: 1.5;
            color: #212529;
            background-color: #fff;
            background-image: none;
            border: 1px solid #ced4da;
            border-radius: 0.375rem;
            margin-bottom: 1rem;
            transition: border-color 0.15s ease-in-out, box-shadow 0.15s ease-in-out;
        }
        
        .form-control:focus, .form-select:focus {
            color: #212529;
            background-color: #fff;
            border-color: #86b7fe;
            outline: 0;
            box-shadow: 0 0 0 0.25rem rgba(13, 110, 253, 0.25);
        }
        
        .form-control:disabled, .form-select:disabled {
            background-color: #e9ecef;
            opacity: 1;
        }
        
        .form-check-input {
            margin-right: 0.5rem;
            width: 1em;
            height: 1em;
            margin-top: 0.25em;
            vertical-align: top;
            background-color: #fff;
            background-repeat: no-repeat;
            background-position: center;
            background-size: contain;
            border: 1px solid rgba(0, 0, 0, 0.25);
            border-radius: 0.25em;
        }
        
        textarea.form-control {
            resize: vertical;
            min-height: calc(1.5em + 0.75rem + 2px);
        }
        
        /* Button Styles - Bootstrap-like */
        .btn {
            padding: 0.375rem 0.75rem;
            margin-bottom: 0;
            font-size: 1rem;
            font-weight: 400;
            line-height: 1.5;
            text-align: center;
            text-decoration: none;
            vertical-align: middle;
            cursor: pointer;
            border: 1px solid transparent;
            border-radius: 0.375rem;
            transition: color 0.15s ease-in-out, background-color 0.15s ease-in-out, 
                        border-color 0.15s ease-in-out, box-shadow 0.15s ease-in-out;
            display: inline-block;
            margin-right: 0.5rem;
        }
        
        .btn:hover {
            text-decoration: none;
        }
        
        .btn:focus {
            outline: 0;
            box-shadow: 0 0 0 0.25rem rgba(13, 110, 253, 0.25);
        }
        
        .btn:disabled {
            pointer-events: none;
            opacity: 0.65;
        }
        
        .btn-primary {
            color: #fff;
            background-color: #0d6efd;
            border-color: #0d6efd;
        }
        
        .btn-primary:hover {
            color: #fff;
            background-color: #0b5ed7;
            border-color: #0a58ca;
        }
        
        .btn-success {
            color: #fff;
            background-color: #198754;
            border-color: #198754;
        }
        
        .btn-success:hover {
            color: #fff;
            background-color: #157347;
            border-color: #146c43;
        }
        
        .btn-warning {
            color: #000;
            background-color: #ffc107;
            border-color: #ffc107;
        }
        
        .btn-warning:hover {
            color: #000;
            background-color: #ffca2c;
            border-color: #ffc720;
        }
        
        .btn-info {
            color: #000;
            background-color: #0dcaf0;
            border-color: #0dcaf0;
        }
        
        .btn-info:hover {
            color: #000;
            background-color: #31d2f2;
            border-color: #25cff2;
        }
        
        .btn-danger {
            color: #fff;
            background-color: #dc3545;
            border-color: #dc3545;
        }
        
        .btn-danger:hover {
            color: #fff;
            background-color: #bb2d3b;
            border-color: #b02a37;
        }
        
        .btn-sm {
            padding: 0.25rem 0.5rem;
            font-size: 0.875rem;
            border-radius: 0.25rem;
        }
        
        /* Badge Styles */
        .badge {
            padding: 0.35em 0.65em;
            font-size: 0.75em;
            font-weight: 700;
            line-height: 1;
            color: #fff;
            text-align: center;
            white-space: nowrap;
            vertical-align: baseline;
            border-radius: 0.375rem;
        }
        
        .bg-success { background-color: #198754 !important; }
        .bg-danger { background-color: #dc3545 !important; }
        .bg-warning { background-color: #ffc107 !important; color: #000 !important; }
        .bg-secondary { background-color: #6c757d !important; }
        .bg-info { background-color: #0dcaf0 !important; color: #000 !important; }
        
        /* Grid System - Bootstrap-like */
        .row {
            display: flex;
            flex-wrap: wrap;
            margin-right: -0.75rem;
            margin-left: -0.75rem;
        }
        
        .col, .col-md-6, .col-lg-4, .col-lg-6, .col-xl-6 {
            position: relative;
            width: 100%;
            padding-right: 0.75rem;
            padding-left: 0.75rem;
        }
        
        .col {
            flex: 1 0 0%;
        }
        
        .col-md-6 {
            flex: 0 0 auto;
            width: 50%;
        }
        
        .col-lg-4 {
            flex: 0 0 auto;
            width: 33.333333%;
        }
        
        .col-lg-6 {
            flex: 0 0 auto;
            width: 50%;
        }
        
        .col-xl-6 {
            flex: 0 0 auto;
            width: 50%;
        }
        
        /* Utility Classes */
        .loading {
            opacity: 0.6;
            pointer-events: none;
        }
        
        .text-muted {
            color: #6c757d !important;
        }
        
        .text-center {
            text-align: center !important;
        }
        
        .mb-3 {
            margin-bottom: 1rem !important;
        }
        
        .mt-3 {
            margin-top: 1rem !important;
        }
        
        .d-flex {
            display: flex !important;
        }
        
        .justify-content-between {
            justify-content: space-between !important;
        }
        
        .align-items-center {
            align-items: center !important;
        }
        
        .align-items-end {
            align-items: flex-end !important;
        }
        
        .w-100 {
            width: 100% !important;
        }
        
        .h-100 {
            height: 100% !important;
        }
        
        /* Message Styles */
        .error {
            color: #dc3545;
            font-size: 0.875rem;
            margin-top: 0.25rem;
        }
        
        .success {
            color: #198754;
            font-size: 0.875rem;
            margin-top: 0.25rem;
        }
        
        .alert {
            padding: 0.75rem 1.25rem;
            margin-bottom: 1rem;
            border: 1px solid transparent;
            border-radius: 0.375rem;
        }
        
        .alert-success {
            color: #0f5132;
            background-color: #d1e7dd;
            border-color: #badbcc;
        }
        
        .alert-danger {
            color: #842029;
            background-color: #f8d7da;
            border-color: #f5c2c7;
        }
        
        /* Status Section */
        .status-section {
            background-color: #f8f9fa;
            padding: 1rem;
            border-radius: 0.375rem;
            margin-top: 1rem;
        }
        
        .status-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.5rem 0;
            border-bottom: 1px solid #dee2e6;
        }
        
        .status-item:last-child {
            border-bottom: none;
        }
        
        .status-label {
            font-weight: 500;
            color: #495057;
        }
        
        .status-value {
            color: #212529;
        }
        
        /* List Styles */
        .list-section {
            max-height: 300px;
            overflow-y: auto;
            background-color: #f8f9fa;
            padding: 1rem;
            border-radius: 0.375rem;
            border: 1px solid #dee2e6;
        }
        
        .list-item {
            margin-bottom: 0.75rem;
            padding: 0.75rem;
            border: 1px solid #dee2e6;
            border-radius: 0.375rem;
            background-color: #fff;
        }
        
        .list-item:last-child {
            margin-bottom: 0;
        }
        
        .list-item-header {
            font-weight: 600;
            margin-bottom: 0.25rem;
        }
        
        .list-item-meta {
            color: #6c757d;
            font-size: 0.875rem;
        }
        
        /* Table Styles */
        .table {
            width: 100%;
            margin-bottom: 1rem;
            color: #212529;
            border-collapse: collapse;
        }
        
        .table th,
        .table td {
            padding: 0.75rem;
            vertical-align: top;
            border-bottom: 1px solid #dee2e6;
        }
        
        .table th {
            font-weight: 600;
            background-color: #f8f9fa;
            border-bottom: 2px solid #dee2e6;
        }
        
        .table tbody tr:hover {
            background-color: rgba(0, 0, 0, 0.025);
        }
        
        /* Responsive Design */
        @media (max-width: 1200px) {
            .col-xl-6 {
                width: 100%;
            }
        }
        
        @media (max-width: 992px) {
            .col-lg-4, .col-lg-6 {
                width: 100%;
            }
        }
        
        @media (max-width: 768px) {
            .row {
                margin-right: -0.5rem;
                margin-left: -0.5rem;
            }
            
            .col, .col-md-6, .col-lg-4, .col-lg-6, .col-xl-6 {
                padding-right: 0.5rem;
                padding-left: 0.5rem;
            }
            
            .col-md-6 {
                width: 100%;
            }
            
            .col-lg-4, .col-lg-6, .col-xl-6 {
                width: 100%;
            }
            
            .card-header {
                flex-direction: column;
                align-items: flex-start;
                gap: 1rem;
            }
            
            .card-header > div:last-child {
                align-self: stretch;
                display: flex;
                gap: 0.5rem;
            }
            
            .card-header .btn {
                flex: 1;
                margin-right: 0;
            }
            
            .btn {
                min-height: 44px;
                padding: 0.75rem 1rem;
            }
            
            .form-control, .form-select {
                font-size: 16px; /* Prevents zoom on iOS */
            }
            
            .table {
                font-size: 0.875rem;
            }
            
            .table th,
            .table td {
                padding: 0.5rem;
            }
            
            .status-section {
                padding: 0.75rem;
            }
            
            .list-section {
                padding: 0.75rem;
                max-height: 250px;
            }
            
            .list-item {
                padding: 0.5rem;
            }
        }
        
        @media (max-width: 576px) {
            .card-body {
                padding: 0.75rem;
            }
            
            .card-header {
                padding: 0.75rem;
            }
            
            .btn-sm {
                padding: 0.375rem 0.75rem;
                font-size: 0.8rem;
            }
            
            .form-control, .form-select {
                padding: 0.5rem 0.75rem;
            }
        }
        
        /* Dark mode support (if needed in future) */
        @media (prefers-color-scheme: dark) {
            :host {
                color-scheme: dark;
            }
        }
    </style>
`;

/**
 * Get shared styles as a string for use in web components
 * @returns {string} The shared styles CSS
 */
function getSharedStyles() {
    return sharedStyles;
}

/**
 * Create a style element with shared styles
 * @returns {HTMLStyleElement} Style element with shared styles
 */
function createSharedStylesElement() {
    const template = document.createElement('template');
    template.innerHTML = sharedStyles;
    return template.content.cloneNode(true);
}

// Make functions available globally
window.AdminSharedStyles.getSharedStyles = getSharedStyles;
window.AdminSharedStyles.createSharedStylesElement = createSharedStylesElement;

console.log('🎨 AdminSharedStyles loaded and available globally');