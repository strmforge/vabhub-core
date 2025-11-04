from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import jwt
from .auth import AuthManager
from .config import Config
import os

router = APIRouter(prefix="/auth", tags=["authentication"])

# JWT配置
JWT_SECRET = getattr(Config, "SECRET_KEY", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 24

# API Key配置
API_KEY_HEADER = "X-API-Key"


# 数据模型
class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: str


class APIKeyCreateRequest(BaseModel):
    name: str
    permissions: List[str] = ["read"]
    expires_at: Optional[datetime] = None


class APIKeyResponse(BaseModel):
    id: str
    name: str
    key: str
    permissions: List[str]
    created_at: datetime
    expires_at: Optional[datetime]


class APIKeyListResponse(BaseModel):
    keys: list[APIKeyResponse]


# JWT Token生成
def create_jwt_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRE_HOURS),
        "iat": datetime.utcnow(),
        "type": "access",
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


# JWT Token验证
def verify_jwt_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None


# API Key验证
def verify_api_key(api_key: str) -> bool:
    # 这里应该查询数据库验证API Key
    # 简化实现，实际应该检查数据库
    return api_key.startswith("vabhub_")


# 依赖注入
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
    token = credentials.credentials
    payload = verify_jwt_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload["sub"]


def get_api_key_user(api_key: str = Header(None, alias=API_KEY_HEADER)):
    if not api_key or not verify_api_key(api_key):
        raise HTTPException(status_code=401, detail="Invalid API Key")
    # 这里应该返回API Key对应的用户信息
    return "api_user"


# 路由
@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    # 验证用户凭据
    auth_manager = AuthManager(JWT_SECRET)
    # 简化认证逻辑，实际应该查询数据库
    if request.username == "admin" and request.password == "admin":
        user = {"id": "1", "username": "admin"}
    else:
        user = None
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # 生成JWT Token
    token = create_jwt_token(user["id"])

    return LoginResponse(
        access_token=token, expires_in=JWT_EXPIRE_HOURS * 3600, user_id=user["id"]
    )


@router.post("/refresh")
async def refresh_token(current_user: str = Depends(get_current_user)):
    # 刷新Token
    new_token = create_jwt_token(current_user)
    return {"access_token": new_token, "token_type": "bearer"}


@router.post("/apikeys", response_model=APIKeyResponse)
async def create_api_key(
    request: APIKeyCreateRequest, current_user: str = Depends(get_current_user)
):
    # 生成API Key
    import secrets

    api_key = f"vabhub_{secrets.token_urlsafe(32)}"

    # 这里应该保存到数据库
    key_info = {
        "id": secrets.token_urlsafe(16),
        "name": request.name,
        "key": api_key,
        "permissions": request.permissions,
        "created_at": datetime.utcnow(),
        "expires_at": request.expires_at,
    }

    return APIKeyResponse(**key_info)


@router.get("/apikeys", response_model=APIKeyListResponse)
async def list_api_keys(current_user: str = Depends(get_current_user)):
    # 这里应该从数据库获取用户的API Keys
    # 简化实现
    return APIKeyListResponse(keys=[])


@router.delete("/apikeys/{key_id}")
async def delete_api_key(key_id: str, current_user: str = Depends(get_current_user)):
    # 这里应该从数据库删除API Key
    return {"message": "API Key deleted"}


# 受保护的路由示例
@router.get("/me")
async def get_current_user_info(current_user: str = Depends(get_current_user)):
    return {"user_id": current_user, "message": "This is a protected endpoint"}


# API Key保护的路由示例
@router.get("/apikey-test")
async def api_key_test(user: str = Depends(get_api_key_user)):
    return {"user": user, "message": "This endpoint requires API Key authentication"}
