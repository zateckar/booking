from datetime import datetime, timedelta
from typing import Optional
import logging
import warnings

from jose import JWTError, jwt
from passlib.context import CryptContext

from . import models
from .logging_config import get_logger, log_with_context

# Suppress bcrypt version warnings from passlib
warnings.filterwarnings("ignore", message=".*bcrypt.*", category=UserWarning)
# Also suppress the specific passlib bcrypt warnings
warnings.filterwarnings("ignore", message=".*trapped.*error reading bcrypt version.*")

# Set passlib bcrypt logger to ERROR level to suppress warnings
passlib_logger = logging.getLogger('passlib.handlers.bcrypt')
passlib_logger.setLevel(logging.ERROR)

logger = get_logger("security")

SECRET_KEY = "b34195f2-f1c8-407f-b84e-1102988e0fd8"  # Change this in a real application
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 120  # 2 hours - increased from 30 minutes to reduce frequent logouts
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Create password context with explicit bcrypt configuration
pwd_context = CryptContext(
    schemes=["bcrypt"], 
    deprecated="auto",
    bcrypt__rounds=12  # Explicit rounds to avoid version detection issues
)


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_refresh_token(token: str):
    """Verify and decode a refresh token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        token_type = payload.get("type")
        if token_type != "refresh":
            logger.warning("Token is not a refresh token")
            return None
        email = payload.get("sub")
        if email is None:
            logger.warning("Refresh token missing email subject")
            return None
        return payload
    except JWTError as e:
        logger.warning(f"Refresh token validation failed: {str(e)}")
        return None


def get_token_expiry_time(token: str) -> Optional[datetime]:
    """Get the expiry time of a token without validation"""
    try:
        payload = jwt.get_unverified_claims(token)
        exp_timestamp = payload.get("exp")
        if exp_timestamp:
            return datetime.utcfromtimestamp(exp_timestamp)
    except JWTError:
        pass
    return None


def is_token_expired(token: str) -> bool:
    """Check if a token is expired"""
    expiry_time = get_token_expiry_time(token)
    if expiry_time:
        return datetime.utcnow() >= expiry_time
    return True


def is_token_expiring_soon(token: str, buffer_minutes: int = 5) -> bool:
    """Check if a token will expire within the specified buffer time"""
    expiry_time = get_token_expiry_time(token)
    if expiry_time:
        buffer_time = datetime.utcnow() + timedelta(minutes=buffer_minutes)
        return buffer_time >= expiry_time
    return True


from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2
from sqlalchemy.orm import Session

from .database import get_db


class OAuth2PasswordBearerWithCookie(OAuth2PasswordBearer):
    async def __call__(self, request: Request) -> Optional[str]:
        # First, try to get the token from the Authorization header
        authorization: str = request.headers.get("Authorization")
        if authorization:
            scheme, _, param = authorization.partition(" ")
            if scheme.lower() == "bearer":
                return param

        # If not in header, try to get it from the cookie
        token = request.cookies.get("access_token")
        if token:
            # The cookie value is "Bearer <token>", so we need to strip "Bearer "
            scheme, _, param = token.partition(" ")
            if scheme.lower() == "bearer":
                return param

        if self.auto_error:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
                headers={"WWW-Authenticate": "Bearer"},
            )
        else:
            return None

oauth2_scheme = OAuth2PasswordBearerWithCookie(tokenUrl="/api/token")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            logger.warning("JWT token missing email subject")
            raise credentials_exception
    except JWTError as e:
        logger.warning(f"JWT validation failed: {str(e)}")
        raise credentials_exception
    
    user = db.query(models.User).filter(models.User.email == email).first()
    if user is None:
        logger.warning(f"User not found for email: {email}")
        raise credentials_exception
    
    logger.debug(f"Successfully authenticated user: {email}")
    return user


def get_current_admin_user(current_user: models.User = Depends(get_current_user)):
    if not current_user.is_admin:
        log_with_context(
            logger, logging.WARNING,
            f"Non-admin user {current_user.email} attempted to access admin functionality",
            user_id=current_user.id
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have admin privileges",
        )
    
    logger.debug(f"Admin access granted to user: {current_user.email}")
    return current_user
