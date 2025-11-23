import asyncio
import sys
import os
from unittest.mock import MagicMock, patch
from fastapi import HTTPException

# Ensure app is in path
sys.path.append('c:/Users/ksank/Master-Chatbot')

from app.middleware.auth import verify_token, HTTPAuthorizationCredentials

def test_auth_integration():
    print("Running Auth Integration Tests...")
    
    # Test 1: Local Dev Mode (No Auth0 Env Vars)
    print("\nTest 1: Local Dev Mode (Fallback)")
    with patch.dict(os.environ, {}, clear=True):
        # Ensure REQUIRE_AUTH is True for this test
        with patch('app.middleware.auth.REQUIRE_AUTH', True):
            # Mock JWT decode for local mode
            with patch('jose.jwt.decode') as mock_decode:
                mock_decode.return_value = {"sub": "local_user", "role": "admin", "school_id": "School 1"}
                
                creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="fake_local_token")
                user = verify_token(creds)
                
                if user["user_id"] == "local_user" and user["school_id"] == "School 1":
                    print("PASS: Local token accepted")
                else:
                    print(f"FAIL: Unexpected user data: {user}")

    # Test 2: Auth0 Mode (With Env Vars)
    print("\nTest 2: Auth0 Mode (Mocked)")
    with patch.dict(os.environ, {"AUTH0_DOMAIN": "dev-test.auth0.com", "AUTH0_AUDIENCE": "api"}, clear=True):
        # Reload module to pick up env vars? No, they are read at module level.
        # We need to patch the module-level variables directly
        with patch('app.middleware.auth.AUTH0_DOMAIN', "dev-test.auth0.com"), \
             patch('app.middleware.auth.AUTH0_AUDIENCE', "api"), \
             patch('app.middleware.auth.REQUIRE_AUTH', True):
            
            # Mock requests.get for JWKS
            with patch('requests.get') as mock_get:
                mock_get.return_value.json.return_value = {
                    "keys": [{"kid": "test_kid", "kty": "RSA", "use": "sig", "n": "...", "e": "AQAB"}]
                }
                
                # Mock jwt.get_unverified_header
                with patch('jose.jwt.get_unverified_header') as mock_header:
                    mock_header.return_value = {"kid": "test_kid"}
                    
                    # Mock jwt.decode for Auth0
                    with patch('jose.jwt.decode') as mock_decode:
                        mock_decode.return_value = {
                            "sub": "auth0|123",
                            "https://tilli.com/role": "educator",
                            "https://tilli.com/school_id": "School 2"
                        }
                        
                        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="fake_auth0_token")
                        user = verify_token(creds)
                        
                        if user["user_id"] == "auth0|123" and user["school_id"] == "School 2" and user["provider"] == "auth0":
                            print("PASS: Auth0 token accepted")
                        else:
                            print(f"FAIL: Unexpected user data: {user}")

if __name__ == "__main__":
    test_auth_integration()
