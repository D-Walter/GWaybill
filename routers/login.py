from fastapi import APIRouter, Form, HTTPException, Response, Request, status, Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from db import get_connection
from dotenv import load_dotenv
import os, secrets, string

active_tokens = {}
router = APIRouter()

# 配置项
load_dotenv()
SECRET_KEY = os.getenv("KEZIG_SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# 密码加密
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

# --- 工具函数 ---


def authenticate_user(username: str, password: str):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT username, hashed_password, role FROM users WHERE username=%s", (username,))
            user = cursor.fetchone()
            if not user or not pwd_context.verify(password, user["hashed_password"]):
                return None
            return user
    finally:
        conn.close()


def create_access_token(data: dict, expires_delta: timedelta = None):
    if not isinstance(SECRET_KEY, (str, bytes)):
        raise ValueError("SECRET_KEY must be a string or bytes: got {}".format(type(SECRET_KEY)))

    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})

    # Ensure SECRET_KEY is bytes if required by your JWT library
    secret = SECRET_KEY if isinstance(SECRET_KEY, bytes) else SECRET_KEY.encode("utf-8")

    return jwt.encode(to_encode, secret, algorithm=ALGORITHM)


def set_access_cookie(response: Response, token: str):
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=False,
        samesite="Strict",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


def get_current_user_from_cookie(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="未提供身份凭证")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        role = payload.get("role", "staff")
        if not username:
            raise HTTPException(status_code=401, detail="无效令牌")

        # 检查是否是当前有效 token
        if active_tokens.get(username) != token:
            raise HTTPException(status_code=401, detail="该令牌已失效")

        return {"username": username, "role": role}
    except JWTError:
        raise HTTPException(status_code=401, detail="令牌验证失败")


def generate_random_password(length=64):
    chars = string.ascii_letters + string.digits + string.punctuation
    return "".join(secrets.choice(chars) for _ in range(length))


def initialize_root_password():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT username FROM users WHERE username=%s", ("root",))
            exists = cursor.fetchone()

            raw_password = generate_random_password()
            hashed_password = pwd_context.hash(raw_password)

            if exists:
                cursor.execute("UPDATE users SET hashed_password=%s WHERE username=%s", (hashed_password, "root"))
            else:
                cursor.execute("INSERT INTO users (username, hashed_password, role) VALUES (%s, %s, %s)", ("root", hashed_password, "admin"))

            conn.commit()
            print(f"[INFO] 随机生成的 root 密码为：\n{raw_password}\n请妥善保存。")
    finally:
        conn.close()


# --- 登录接口 ---


@router.post("/login")
def login(response: Response, username: str = Form(...), password: str = Form(...)):
    user = authenticate_user(username, password)
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    access_token = create_access_token({"sub": user["username"], "role": user["role"]}, expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    # 存入内存白名单
    active_tokens[user["username"]] = access_token
    set_access_cookie(response, access_token)
    return {"message": "登录成功"}


@router.post("/refresh-token")
def refresh_token(request: Request, response: Response):
    user = get_current_user_from_cookie(request)
    if not user:
        raise HTTPException(status_code=401, detail="未认证用户，无法刷新 token")
    new_token = create_access_token({"sub": user["username"], "role": user["role"]}, expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    # 存入内存白名单
    active_tokens[user["username"]] = new_token
    set_access_cookie(response, new_token)
    return {"message": "Token 已刷新"}


@router.post("/logout")
def logout(request: Request, response: Response):
    token = request.cookies.get("access_token")
    if token:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username = payload.get("sub")
            if username and active_tokens.get(username) == token:
                del active_tokens[username]
        except JWTError:
            pass  # 忽略无效 token
    response.delete_cookie(key="access_token", httponly=True, secure=False, samesite="Strict")
    return {"message": "已登出"}
