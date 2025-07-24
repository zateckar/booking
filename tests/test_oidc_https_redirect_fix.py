"""
Test suite for OIDC HTTPS redirect URI security fix.

This test verifies that OIDC redirect URIs are correctly converted to HTTPS
in production environments while remaining HTTP in development.
"""

import pytest
import os
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import Request
from starlette.datastructures import Headers, URL

# Import the functions we're testing
from src.booking import _get_secure_redirect_uri
from src.booking.routers.auth import _get_secure_logout_redirect_uri


def create_mock_request(base_url: str = "http://app:8000", headers: dict = None):
    """Create a mock request object for testing."""
    request = MagicMock(spec=Request)
    request.base_url = URL(base_url)
    request.url_for = MagicMock(return_value=f"{base_url}/api/auth/oidc/test_provider")
    request.headers = Headers(headers or {})
    return request


class TestSecureRedirectURI:
    """Test the _get_secure_redirect_uri function."""
    
    def test_no_https_in_development_environment(self):
        """Test that HTTPS is not forced in development environments."""
        request = create_mock_request()
        
        with patch.dict(os.environ, {'ENVIRONMENT': 'development'}, clear=False):
            with patch('os.path.exists', return_value=True):  # Simulate container
                redirect_uri = _get_secure_redirect_uri(request, "auth_oidc", provider_name="test")
                assert redirect_uri.startswith("http://")
                assert not redirect_uri.startswith("https://")
    
    def test_explicit_https_forcing(self):
        """Test explicit HTTPS forcing via environment variable."""
        request = create_mock_request()
        
        with patch.dict(os.environ, {'FORCE_HTTPS_REDIRECTS': 'true'}, clear=False):
            redirect_uri = _get_secure_redirect_uri(request, "auth_oidc", provider_name="test")
            assert redirect_uri.startswith("https://")
            assert "https://app:8000/api/auth/oidc/test_provider" == redirect_uri
    
    def test_https_detection_via_forwarded_proto_header(self):
        """Test HTTPS detection via X-Forwarded-Proto header."""
        request = create_mock_request(headers={"x-forwarded-proto": "https"})
        
        with patch.dict(os.environ, {}, clear=True):  # Clear all env vars
            redirect_uri = _get_secure_redirect_uri(request, "auth_oidc", provider_name="test")
            assert redirect_uri.startswith("https://")
    
    def test_https_detection_via_forwarded_ssl_header(self):
        """Test HTTPS detection via X-Forwarded-Ssl header."""
        request = create_mock_request(headers={"x-forwarded-ssl": "on"})
        
        with patch.dict(os.environ, {}, clear=True):  # Clear all env vars
            redirect_uri = _get_secure_redirect_uri(request, "auth_oidc", provider_name="test")
            assert redirect_uri.startswith("https://")
    
    def test_container_environment_detection(self):
        """Test HTTPS forcing in containerized environments."""
        request = create_mock_request()
        
        with patch.dict(os.environ, {}, clear=True):  # Clear all env vars
            with patch('os.path.exists', return_value=True):  # Simulate /.dockerenv exists
                redirect_uri = _get_secure_redirect_uri(request, "auth_oidc", provider_name="test")
                assert redirect_uri.startswith("https://")
    
    def test_docker_container_env_var_detection(self):
        """Test HTTPS forcing via DOCKER_CONTAINER environment variable."""
        request = create_mock_request()
        
        with patch.dict(os.environ, {'DOCKER_CONTAINER': 'true'}, clear=False):
            with patch('os.path.exists', return_value=False):  # No /.dockerenv file
                redirect_uri = _get_secure_redirect_uri(request, "auth_oidc", provider_name="test")
                assert redirect_uri.startswith("https://")
    
    def test_no_https_forcing_in_local_environment(self):
        """Test that HTTPS is not forced in local development."""
        request = create_mock_request()
        
        with patch.dict(os.environ, {}, clear=True):  # Clear all env vars
            with patch('os.path.exists', return_value=False):  # No container indicators
                redirect_uri = _get_secure_redirect_uri(request, "auth_oidc", provider_name="test")
                assert redirect_uri.startswith("http://")
    
    def test_precedence_of_explicit_forcing(self):
        """Test that explicit FORCE_HTTPS_REDIRECTS takes precedence."""
        request = create_mock_request()
        
        # Set development environment but explicitly force HTTPS
        with patch.dict(os.environ, {
            'FORCE_HTTPS_REDIRECTS': 'true',
            'ENVIRONMENT': 'development'
        }, clear=False):
            redirect_uri = _get_secure_redirect_uri(request, "auth_oidc", provider_name="test")
            assert redirect_uri.startswith("https://")


class TestSecureLogoutRedirectURI:
    """Test the _get_secure_logout_redirect_uri function."""
    
    def test_logout_redirect_https_forcing(self):
        """Test that logout redirect URIs are also converted to HTTPS."""
        request = create_mock_request()
        
        with patch.dict(os.environ, {'FORCE_HTTPS_REDIRECTS': 'true'}, clear=False):
            redirect_uri = _get_secure_logout_redirect_uri(request)
            assert redirect_uri.startswith("https://")
            assert redirect_uri.endswith("/logout-complete")
    
    def test_logout_redirect_development(self):
        """Test that logout redirect URIs remain HTTP in development."""
        request = create_mock_request()
        
        with patch.dict(os.environ, {'ENVIRONMENT': 'development'}, clear=False):
            with patch('os.path.exists', return_value=True):  # Simulate container
                redirect_uri = _get_secure_logout_redirect_uri(request)
                assert redirect_uri.startswith("http://")
                assert redirect_uri.endswith("/logout-complete")


class TestEnvironmentVariableValues:
    """Test different environment variable value formats."""
    
    @pytest.mark.parametrize("value", ["true", "True", "TRUE", "1", "yes", "Yes", "YES"])
    def test_force_https_truthy_values(self, value):
        """Test various truthy values for FORCE_HTTPS_REDIRECTS."""
        request = create_mock_request()
        
        with patch.dict(os.environ, {'FORCE_HTTPS_REDIRECTS': value}, clear=False):
            redirect_uri = _get_secure_redirect_uri(request, "auth_oidc", provider_name="test")
            assert redirect_uri.startswith("https://")
    
    @pytest.mark.parametrize("value", ["false", "False", "0", "no", ""])
    def test_force_https_falsy_values(self, value):
        """Test various falsy values for FORCE_HTTPS_REDIRECTS."""
        request = create_mock_request()
        
        with patch.dict(os.environ, {'FORCE_HTTPS_REDIRECTS': value}, clear=False):
            with patch('os.path.exists', return_value=False):  # No container indicators
                redirect_uri = _get_secure_redirect_uri(request, "auth_oidc", provider_name="test")
                assert redirect_uri.startswith("http://")
    
    @pytest.mark.parametrize("env_value", ["development", "dev", "local"])
    def test_development_environment_values(self, env_value):
        """Test various development environment values."""
        request = create_mock_request()
        
        with patch.dict(os.environ, {'ENVIRONMENT': env_value}, clear=False):
            with patch('os.path.exists', return_value=True):  # Simulate container
                redirect_uri = _get_secure_redirect_uri(request, "auth_oidc", provider_name="test")
                assert redirect_uri.startswith("http://")


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_already_https_uri(self):
        """Test that HTTPS URIs are not double-converted."""
        request = create_mock_request(base_url="https://app:8000")
        request.url_for = MagicMock(return_value="https://app:8000/api/auth/oidc/test_provider")
        
        with patch.dict(os.environ, {'FORCE_HTTPS_REDIRECTS': 'true'}, clear=False):
            redirect_uri = _get_secure_redirect_uri(request, "auth_oidc", provider_name="test")
            assert redirect_uri == "https://app:8000/api/auth/oidc/test_provider"
            # Should not become "https://s://app:8000/..."
    
    def test_special_characters_in_provider_name(self):
        """Test handling of special characters in provider names."""
        request = create_mock_request()
        request.url_for = MagicMock(return_value="http://app:8000/api/auth/oidc/test%20provider")
        
        with patch.dict(os.environ, {'FORCE_HTTPS_REDIRECTS': 'true'}, clear=False):
            redirect_uri = _get_secure_redirect_uri(request, "auth_oidc", provider_name="test provider")
            assert redirect_uri.startswith("https://")
            assert "test%20provider" in redirect_uri


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])
