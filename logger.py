from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from jose import JWTError, jwt
from db import get_connection
import os

SECRET_KEY = os.getenv("KEZIG_SECRET_KEY")
ALGORITHM = "HS256"


class OperationLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        method = request.method
        ip_address = request.client.host
        body = await request.body()
        payload = body.decode("utf-8", errors="ignore")

        # 默认身份
        username = "anonymous"
        role = "guest"

        # 尝试从 Cookie 中获取身份信息
        token = request.cookies.get("access_token")
        if token:
            try:
                decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
                username = decoded.get("sub", "anonymous")
                role = decoded.get("role", "guest")
            except JWTError:
                pass  # 如果 token 有误，就保留匿名身份

        # 写入数据库
        try:
            conn = get_connection()
            with conn.cursor() as cursor:
                sql = """
                    INSERT INTO operation_logs (username, role, path, method, ip_address, payload)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """
                cursor.execute(sql, (username, role, path, method, ip_address, payload))
            conn.commit()
        except Exception as e:
            print(f"[日志写入失败] {e}")
        finally:
            if "conn" in locals():
                conn.close()

        response = await call_next(request)
        return response
