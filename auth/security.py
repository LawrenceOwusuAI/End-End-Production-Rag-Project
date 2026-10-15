import os
from datetime import datetime,timedelta,timezone
import jwt
from dotenv import load_dotenv
from fastapi import Depends,HTTPException,status
from fastapi.security import HTTPBearer,HTTPAuthorizationCredentials
from pwdlib import PasswordHash
from sqlalchemy.orm import Session
from auth.database import get_db
from auth.models import User
load_dotenv(override=True)

# CONFIGURATION
SECRET_KEY = os.getenv( "JWT_SECRET_KEY")
ALGORITHM = os.getenv("JWT_ALGORITHM","HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES","30"))
if not SECRET_KEY:
    raise RuntimeError("JWT_SECRET_KEY was not found in the environment.")

# PASSWORD HASHING
password_hash = PasswordHash.recommended()

def hash_password(password: str) -> str:
    return password_hash.hash(password)

def verify_password(plain_password: str,hashed_password: str) -> bool:
    return password_hash.verify(plain_password,hashed_password )

# JWT
def create_access_token(user_id: int,role: str):
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "role": role,
        "iat": now,
        "exp": (
            now
            + timedelta(
                minutes=
                ACCESS_TOKEN_EXPIRE_MINUTES
            )
        )
    }
    return jwt.encode(payload, SECRET_KEY,algorithm=ALGORITHM)

# BEARER AUTHENTICATION
security = HTTPBearer()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)):

    token = credentials.credentials
    try:
        payload = jwt.decode(token,SECRET_KEY,algorithms=[ALGORITHM])
        user_id = payload.get( "sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token"
            )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token"
        )

    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User does not exist"
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account disabled"
        )
    return user