# OIDC Claims Mapping Implementation

## Overview

This implementation adds dynamic OIDC claims mapping functionality to the booking application, allowing administrators to:

1. **Map OIDC claims to internal user profiles** - Configure how claims from OIDC tokens are mapped to application data
2. **Role-based authorization** - Map OIDC roles to admin privileges 
3. **Enhanced reporting** - Generate reports with rich user context from mapped claims
4. **Flexible configuration** - Generic system that works with any OIDC provider

## Key Features

### 1. Dynamic Claims Discovery
- Automatically discover available claims from OIDC tokens
- Compare with existing mappings to identify unmapped claims
- Support for complex claim structures (arrays, nested objects)

### 2. Flexible Claims Mapping
- **Generic mapping system** - Map any OIDC claim to any internal field name
- **Multiple data types** - Support for string, number, boolean, array, and role types
- **Required vs Optional** - Configure which claims are required for authentication
- **Default values** - Provide fallback values for missing optional claims

### 3. Role-Based Authorization
- Map OIDC role claims to admin privileges
- Support for exact string matching (e.g., "EAI-TEST.ADMINS")
- Configurable admin role values
- Fallback to database `is_admin` if OIDC roles unavailable

### 4. Enhanced User Profiles
- Store mapped claims data in JSON format
- Automatic profile updates on OIDC authentication
- Preserve existing user data while adding new claims
- Track last OIDC update timestamp

### 5. Dynamic Reporting System
- **Configurable columns** - Choose any combination of static and mapped data
- **Auto-discovery** - Automatically detect available claim fields
- **Report templates** - Save and reuse column configurations
- **Multiple formats** - JSON data and Excel export
- **Comprehensive data** - Include booking statistics with user profile data

## Database Schema

### New Tables

```sql
-- Claims mapping configuration
CREATE TABLE oidc_claim_mappings (
    id INTEGER PRIMARY KEY,
    claim_name STRING,           -- OIDC claim key
    mapped_field_name STRING,    -- Internal field name
    mapping_type STRING,         -- "role", "string", "array", "number", "boolean"
    is_required BOOLEAN,         -- Required for authentication
    role_admin_values STRING,    -- JSON array of admin role values
    default_value STRING,        -- Default if claim missing
    display_label STRING,        -- Human-readable label
    description STRING,          -- Admin notes
    created_at DATETIME,
    updated_at DATETIME
);

-- User profile data storage
CREATE TABLE user_profiles (
    id INTEGER PRIMARY KEY,
    user_id INTEGER UNIQUE,      -- FK to users table
    profile_data STRING,         -- JSON storage for mapped claims
    last_oidc_update DATETIME
);

-- Report column configuration
CREATE TABLE report_columns (
    id INTEGER PRIMARY KEY,
    column_name STRING UNIQUE,   -- Field name
    display_label STRING,        -- Human-readable label
    column_type STRING,          -- "static", "mapped", "calculated"
    data_type STRING,           -- "string", "number", "array", "boolean"
    is_available BOOLEAN,        -- Available for selection
    sort_order INTEGER           -- Display order
);

-- Report templates
CREATE TABLE report_templates (
    id INTEGER PRIMARY KEY,
    name STRING,
    description STRING,
    selected_columns STRING,     -- JSON array of column configs
    created_by INTEGER,          -- FK to users
    is_default BOOLEAN,
    created_at DATETIME,
    updated_at DATETIME
);
```

## API Endpoints

### Claims Mapping Management
- `GET /admin/claims/claims-mappings` - List all claim mappings
- `POST /admin/claims/claims-mappings` - Create new mapping
- `PUT /admin/claims/claims-mappings/{id}` - Update mapping
- `DELETE /admin/claims/claims-mappings/{id}` - Delete mapping
- `POST /admin/claims/claims-discovery` - Discover claims from sample token
- `POST /admin/claims/test-mapping` - Test mappings with sample data

### User Profile Management
- `GET /admin/claims/user-profiles` - List all user profiles
- `GET /admin/claims/user-profiles/{id}` - Get specific user profile

### Dynamic Reporting
- `GET /admin/dynamic-reports/columns` - Get available report columns
- `POST /admin/dynamic-reports/generate` - Generate dynamic report
- `POST /admin/dynamic-reports/generate/excel` - Generate Excel report
- `GET /admin/dynamic-reports/templates` - List report templates
- `POST /admin/dynamic-reports/templates` - Create report template
- `POST /admin/dynamic-reports/templates/{id}/generate` - Generate from template

## Configuration Example

### Sample Claim Mappings for Skoda OIDC

```json
[
  {
    "claim_name": "email",
    "mapped_field_name": "email",
    "mapping_type": "string",
    "is_required": true,
    "display_label": "Email",
    "description": "User email address - required for authentication"
  },
  {
    "claim_name": "roles",
    "mapped_field_name": "user_roles",
    "mapping_type": "role",
    "is_required": true,
    "role_admin_values": ["EAI-TEST.ADMINS"],
    "display_label": "User Roles",
    "description": "User roles for authorization"
  },
  {
    "claim_name": "display_name",
    "mapped_field_name": "full_name",
    "mapping_type": "string",
    "is_required": false,
    "display_label": "Full Name",
    "description": "User's full display name"
  },
  {
    "claim_name": "department_number",
    "mapped_field_name": "department",
    "mapping_type": "string",
    "is_required": false,
    "display_label": "Department",
    "description": "User's department"
  },
  {
    "claim_name": "organization",
    "mapped_field_name": "company",
    "mapping_type": "string",
    "is_required": false,
    "display_label": "Company",
    "description": "User's organization"
  },
  {
    "claim_name": "employee_number",
    "mapped_field_name": "employee_id",
    "mapping_type": "string",
    "is_required": false,
    "display_label": "Employee ID",
    "description": "Employee identification number"
  }
]
```

## Usage Workflow

### 1. Initial Setup
1. Run migration: `python migrate_oidc_claims_mapping.py`
2. Configure OIDC provider in admin panel
3. Set up claim mappings for your OIDC provider

### 2. Claims Discovery
1. Use `/admin/claims/claims-discovery` with sample token
2. Review discovered claims and existing mappings
3. Configure mappings for unmapped claims

### 3. Role Configuration
1. Create role mapping for authorization
2. Specify exact role strings that grant admin access
3. Test with sample token data

### 4. Report Configuration
1. Review available columns in `/admin/dynamic-reports/columns`
2. Create report templates with desired column combinations
3. Generate reports with rich user context

## Authentication Flow

```
1. User authenticates via OIDC
2. System extracts claims from ID/access token
3. Claims service processes according to mappings:
   - Validates required claims
   - Applies type conversions
   - Checks role mappings for admin access
   - Stores mapped data in user profile
4. User record updated with admin status
5. Standard JWT token issued for session
```

## Error Handling

- **Missing required claims** - Authentication rejected
- **Invalid claim format** - Type conversion with error logging
- **Missing optional claims** - Use default values or skip
- **Role mapping errors** - Log warnings, continue without admin access

## Security Considerations

- All mapped data is optional for application functionality
- Backward compatibility maintained for existing users
- Admin access requires explicit role mapping configuration
- Claim mappings can be modified without affecting existing data

## Testing

Run the comprehensive test suite:
```bash
python test_oidc_claims_mapping.py
```

This tests:
- Claims discovery and processing
- Mapping creation and configuration
- Role-based authorization
- Dynamic report generation
- Template management

## Key Benefits

1. **Future-proof** - Works with any OIDC provider
2. **Flexible** - Map any claim to any field name
3. **Optional** - All enhanced data is optional
4. **Comprehensive** - Rich reporting with user context
5. **Configurable** - Admin-controlled via UI
6. **Secure** - Proper error handling and fallbacks
