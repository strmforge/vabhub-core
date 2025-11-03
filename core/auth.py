"""
Authentication module for VabHub Core
"""

import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any


class AuthManager:
    """Authentication manager for VabHub"""

    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        self.secret_key = secret_key
        self.algorithm = algorithm

    def create_token(
        self, user_id: str, expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create JWT token"""
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(hours=24)

        payload = {"user_id": user_id, "exp": expire, "iat": datetime.utcnow()}

        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.PyJWTError:
            return None

    def get_user_id_from_token(self, token: str) -> Optional[str]:
        """Extract user ID from token"""
        payload = self.verify_token(token)
        if payload:
            return payload.get("user_id")
        return None

    def authenticate_user(
        self, username: str, password: str
    ) -> Optional[Dict[str, Any]]:
        """Authenticate user (simplified implementation)"""
        # Simplified authentication - in production, this should query a database
        if username == "admin" and password == "admin":
            return {"id": "1", "username": "admin"}
        return None


def get_current_user(token: str) -> Optional[str]:
    """Get current user from token (simplified implementation)"""
    auth_manager = AuthManager("your-secret-key-change-in-production")
    return auth_manager.get_user_id_from_token(token)
