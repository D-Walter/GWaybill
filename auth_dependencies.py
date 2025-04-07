from fastapi import Request, Depends, HTTPException, status
from jose import JWTError, jwt
from pydantic import BaseModel
from dotenv import load_dotenv
from routers.login import get_current_user_from_cookie
import os

# 加载环境变量
load_dotenv()
SECRET_KEY = os.getenv("KEZIG_SECRET_KEY")
ALGORITHM = "HS256"


# 用户模型
class User(BaseModel):
    username: str
    role: str = "staff"


# 获取当前用户
def get_current_user(request: Request) -> User:
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录")
    try:
        d = get_current_user_from_cookie(request)
        return User(username=d["username"], role=d["role"])
    except JWTError:
        raise HTTPException(status_code=401, detail="Token 验证失败")


# 权限检查器工厂
def require_role(*roles: str):
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="权限不足")
        return user

    return checker
