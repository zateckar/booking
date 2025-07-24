#!/usr/bin/env python3
"""
Test script to verify SessionMiddleware is properly configured
"""

def test_session_middleware_import():
    """Test that SessionMiddleware can be imported and the app can be created"""
    try:
        from starlette.middleware.sessions import SessionMiddleware
        print("✓ SessionMiddleware import successful")
        
        from src.booking import app
        print("✓ FastAPI app creation successful")
        
        # Check if SessionMiddleware is in the middleware stack
        middleware_types = [type(middleware.cls).__name__ for middleware in app.user_middleware]
        print(f"Middleware stack: {middleware_types}")
        
        if 'SessionMiddleware' in middleware_types:
            print("✓ SessionMiddleware is properly configured")
            return True
        else:
            print("✗ SessionMiddleware not found in middleware stack")
            return False
            
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False
    except Exception as e:
        print(f"✗ Other error: {e}")
        return False

if __name__ == "__main__":
    print("Testing SessionMiddleware configuration...")
    success = test_session_middleware_import()
    print(f"Test {'PASSED' if success else 'FAILED'}")