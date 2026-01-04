"""API dependencies."""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# For now, simplified authentication
# In production, implement proper JWT authentication
security = HTTPBearer()


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> int:
    """
    Get current user ID from token.
    
    TODO: Implement proper JWT verification
    For now, returns a mock user ID for development.
    """
    # Mock implementation - replace with actual JWT verification
    token = credentials.credentials
    
    # In production:
    # 1. Verify JWT token
    # 2. Extract user_id from payload
    # 3. Return user_id
    
    # For development, accept any token and return user_id=1
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    # Mock user ID
    return 1

