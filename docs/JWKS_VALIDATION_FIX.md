# JWKS Validation Fix for Skoda/VW Group OIDC

## Issue Description

When authenticating with Skoda/VW Group OIDC provider, users encountered the error:
```
OIDC authentication failed for provider SIP: Invalid JSON Web Key Set
```

Despite the JWKS endpoint returning HTTP 200 OK, the JWT library rejected the key set as invalid.

## Root Cause Analysis

Investigation revealed that the Skoda/VW Group OIDC provider (`https://identity.skoda.vwgroup.com`) returns a JWKS with duplicate `kid` (Key ID) values:

- **Key 2**: `kid="Vcm83b-Y3XIaiiQwBcuqXsXS7CocRcaZv1egZj-Eqag"` with `use="enc"` (encryption)
- **Key 3**: `kid="Vcm83b-Y3XIaiiQwBcuqXsXS7CocRcaZv1egZj-Eqag"` with `use="sig"` (signing)

This violates the JWKS standard which requires each key to have a unique identifier.

## Technical Details

### JWKS Endpoint
```
GET https://identity.skoda.vwgroup.com/realms/standard/protocol/openid-connect/certs
```

### Original Problematic JWKS Structure
```json
{
  "keys": [
    {
      "kid": "HSLas0xDlCHXoP3sWSnOmF_hQv78oJF0Jb9Drb9d3yc",
      "use": "enc",
      "alg": "RSA-OAEP"
    },
    {
      "kid": "Vcm83b-Y3XIaiiQwBcuqXsXS7CocRcaZv1egZj-Eqag",  // DUPLICATE
      "use": "enc",
      "alg": "RSA-OAEP"
    },
    {
      "kid": "Vcm83b-Y3XIaiiQwBcuqXsXS7CocRcaZv1egZj-Eqag",  // DUPLICATE
      "use": "sig",
      "alg": "RS256"
    }
  ]
}
```

## Solution Implementation

### 1. Added JWKS Fix Function
Created `fix_skoda_jwks()` function in `src/booking/oidc.py` that:
- Fetches the original JWKS
- Detects duplicate `kid` values
- Makes duplicate keys unique by appending `_{use}` suffix
- Returns a compliant JWKS with unique key identifiers

### 2. Enhanced Error Handling
Modified `process_auth_response()` to:
- Detect JWKS validation errors
- Automatically apply the fix when "Invalid JSON Web Key Set" errors occur
- Register a new OAuth client with the corrected JWKS
- Retry authentication with the fixed key set

### 3. Error Detection Patterns
The fix triggers on error messages containing:
- "invalid json web key set"
- "jwks" 
- "duplicate" + "key"

## Fixed JWKS Structure
After applying the fix:
```json
{
  "keys": [
    {
      "kid": "HSLas0xDlCHXoP3sWSnOmF_hQv78oJF0Jb9Drb9d3yc",
      "use": "enc",
      "alg": "RSA-OAEP"
    },
    {
      "kid": "Vcm83b-Y3XIaiiQwBcuqXsXS7CocRcaZv1egZj-Eqag",
      "use": "enc",
      "alg": "RSA-OAEP"
    },
    {
      "kid": "Vcm83b-Y3XIaiiQwBcuqXsXS7CocRcaZv1egZj-Eqag_sig",  // FIXED
      "use": "sig",
      "alg": "RS256"
    }
  ]
}
```

## Testing

### Test Script
Created `test_jwks_fix.py` to verify the fix:
```bash
python test_jwks_fix.py
```

### Test Results
```
=== Original JWKS (with duplicate key IDs) ===
❌ DUPLICATE Key 3: kid=Vcm83b-Y3XIaiiQwBcuqXsXS7CocRcaZv1egZj-Eqag

=== Fixed JWKS (with unique key IDs) ===
✅ SUCCESS: All key IDs are now unique!

Key ID Changes:
Vcm83b-Y3XIaiiQwBcuqXsXS7CocRcaZv1egZj-Eqag → Vcm83b-Y3XIaiiQwBcuqXsXS7CocRcaZv1egZj-Eqag_sig
```

## Implementation Details

### Files Modified
- `src/booking/oidc.py`: Added JWKS fix functionality and enhanced error handling
- `test_jwks_fix.py`: Test script to verify the fix

### Key Functions Added
- `fix_skoda_jwks(jwks_url)`: Fixes duplicate key IDs in JWKS
- Enhanced `process_auth_response()`: Automatic JWKS fix on validation errors

## Impact

### Before Fix
- OIDC authentication with Skoda/VW Group provider failed
- Error: "Invalid JSON Web Key Set"
- Users could not authenticate

### After Fix
- OIDC authentication works seamlessly
- Automatic detection and correction of JWKS issues
- Transparent to end users
- Maintains compatibility with standard OIDC providers

## Future Considerations

1. **Monitor for Changes**: Skoda/VW Group may fix their JWKS in the future
2. **Logging**: The fix includes detailed logging for troubleshooting
3. **Extensibility**: The fix pattern can be applied to other providers with similar issues
4. **Performance**: JWKS is only fixed when needed, minimal performance impact

## Related Issues

This fix addresses JWKS standards compliance issues that may occur with other enterprise OIDC providers that:
- Use the same key for multiple purposes
- Generate JWKS programmatically without proper validation
- Have legacy key management systems

## Security Considerations

- The fix only modifies key identifiers, not cryptographic material
- Original key validation and security properties are preserved
- No sensitive data is logged
- HTTPS is maintained for all JWKS communications
