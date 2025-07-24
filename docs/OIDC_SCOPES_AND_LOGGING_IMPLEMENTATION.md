# OIDC Scopes and Token Logging Implementation

## Overview

This implementation extends the OIDC configuration to support custom scopes and provides comprehensive logging of incoming access and ID tokens. The enhancements allow administrators to configure which scopes to request from OIDC providers and provide detailed visibility into the token information received during authentication.

## Features Implemented

### 1. Custom Scopes Configuration

#### Database Schema Updates
- Added `scopes` column to the `oidc_providers` table
- Default value: `"openid email profile"`
- Supports space-separated list of scopes

#### API Enhancements
- **POST** `/admin/oidc/` - Create OIDC provider with custom scopes
- **GET** `/admin/oidc/` - List all OIDC providers with their scopes
- **GET** `/admin/oidc/{provider_id}` - Get specific OIDC provider details
- **PUT** `/admin/oidc/{provider_id}` - Update OIDC provider including scopes
- **DELETE** `/admin/oidc/{provider_id}` - Delete OIDC provider

#### Schema Updates
- `OIDCProviderCreate` - Includes scopes field with default value
- `OIDCProviderUpdate` - Supports partial updates including scopes
- `OIDCProvider` - Response model includes scopes

### 2. Comprehensive Token Logging

#### Access Token Logging
- Logs token length and type
- Attempts JWT decoding for detailed claims inspection
- Falls back to partial token logging for opaque tokens
- Includes all token claims in structured JSON format

#### ID Token Logging
- Similar comprehensive logging as access tokens
- Extracts user identity information
- Logs standard OIDC claims (sub, email, name, etc.)

#### Token Metadata Logging
- Token type (Bearer, etc.)
- Expiration time
- Granted scopes
- Refresh token presence
- Associated user email

#### Userinfo Logging
- Logs userinfo obtained from tokens or userinfo endpoint
- Includes custom claims and attributes
- Supports complex nested structures (groups, permissions, etc.)

## Usage Examples

### Creating OIDC Provider with Custom Scopes

```json
POST /admin/oidc/
{
    "issuer": "https://company-idp.example.com",
    "client_id": "booking-app-client",
    "client_secret": "your-secret-here",
    "well_known_url": "https://company-idp.example.com/.well-known/openid_configuration",
    "scopes": "openid email profile groups department role custom:permissions"
}
```

### Updating Scopes for Existing Provider

```json
PUT /admin/oidc/1
{
    "scopes": "openid email profile groups department role manager custom:read custom:write"
}
```

### Common Scope Configurations

#### Basic Configuration
```
openid email profile
```

#### Enterprise Configuration
```
openid email profile groups department role
```

#### Extended Configuration with Custom Claims
```
openid email profile groups department role manager cost_center custom:permissions admin:tools
```

## Logged Information Examples

### Access Token Claims
```json
{
  "sub": "user123",
  "email": "john.doe@company.com",
  "name": "John Doe",
  "groups": ["employees", "developers"],
  "department": "Engineering",
  "role": "Senior Developer",
  "cost_center": "ENG-001",
  "manager": "jane.smith@company.com",
  "custom:permissions": ["read:projects", "write:code", "admin:dev-tools"],
  "iat": 1706734800,
  "exp": 1706738400
}
```

### ID Token Claims
```json
{
  "sub": "user123",
  "email": "john.doe@company.com",
  "email_verified": true,
  "name": "John Doe",
  "given_name": "John",
  "family_name": "Doe",
  "picture": "https://company.com/avatars/user123.jpg",
  "locale": "en-US",
  "zoneinfo": "America/New_York",
  "iat": 1706734800,
  "exp": 1706738400
}
```

### Token Metadata
```json
{
  "token_type": "Bearer",
  "expires_in": 3600,
  "scope": "openid email profile groups department role custom:permissions",
  "refresh_token_present": true,
  "user_email": "john.doe@company.com"
}
```

## Implementation Details

### Files Modified

1. **src/booking/models.py**
   - Added `scopes` column to `OIDCProvider` model

2. **src/booking/schemas.py**
   - Updated `OIDCProviderBase` to include scopes
   - Added `OIDCProviderUpdate` for partial updates

3. **src/booking/routers/admin/oidc.py**
   - Added GET and PUT endpoints for individual providers
   - Enhanced CRUD operations

4. **src/booking/oidc.py**
   - Added `register_oidc_provider()` function
   - Added `log_token_information()` function
   - Enhanced `process_auth_response()` with comprehensive logging
   - Uses configured scopes during OAuth client registration

### Migration Script

- **migrate_oidc_scopes.py** - Safely adds scopes column to existing database
- Updates existing providers with default scopes
- Provides verification of successful migration

## Security Considerations

### Token Logging Security
- Tokens are logged for debugging/auditing purposes
- Consider log retention policies in production
- Ensure log files are properly secured
- JWT tokens are decoded without verification (for logging only)

### Scope Security
- More scopes = more information accessible
- Review and approve scope configurations carefully
- Different providers may interpret scopes differently
- Test scope configurations in development first

## Best Practices

### Scope Configuration
1. Start with minimal scopes: `openid email profile`
2. Add additional scopes based on application requirements
3. Document what each custom scope provides
4. Test scope changes in development environment

### Token Logging
1. Monitor log volume in production
2. Implement log rotation and retention policies
3. Consider sensitive information in token claims
4. Use structured logging for better analysis

### Provider Management
1. Use descriptive issuer names
2. Keep client secrets secure
3. Regularly rotate client credentials
4. Monitor provider endpoints for availability

## Troubleshooting

### Common Issues
1. **Invalid Scopes**: Provider rejects unknown scopes
2. **Missing Claims**: Requested scope not returning expected claims
3. **Token Decoding Errors**: Non-JWT tokens or malformed JWTs
4. **Registration Failures**: OAuth client registration issues

### Debug Information
- Check application logs for detailed token information
- Verify scope configuration matches provider capabilities
- Test with minimal scopes first, then add incrementally
- Use provider documentation to understand available scopes

## Testing

The implementation includes comprehensive tests:
- **test_oidc_scopes_logging.py** - Demonstrates all functionality
- Tests CRUD operations with scopes
- Shows token logging with various token types
- Simulates complete authentication flows

Run tests with:
```bash
python test_oidc_scopes_logging.py
```

## Future Enhancements

Potential improvements:
1. Scope validation against provider metadata
2. Token claim mapping configuration
3. Custom claim extraction rules
4. Integration with application authorization system
5. Token refresh logging
6. Scope-based access control in the application
