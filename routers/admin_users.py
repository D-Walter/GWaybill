from fastapi import APIRouter, HTTPException, Form, Depends
from auth_dependencies import require_role, User
from passlib.context import CryptContext
from db import get_connection

router = APIRouter(prefix="/admin/users", tags=["用户管理"], dependencies=[Depends(require_role("admin"))])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@router.post("/add")
def add_user(username: str = Form(...), password: str = Form(...), role: str = Form("staff")):
    hashed_password = pwd_context.hash(password)
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
            if cursor.fetchone():
                raise HTTPException(status_code=400, detail="用户名已存在")

            cursor.execute("INSERT INTO users (username, hashed_password, role) VALUES (%s, %s, %s)", (username, hashed_password, role))
            conn.commit()
            return {"message": f"用户 {username} 添加成功"}
    finally:
        conn.close()


@router.post("/delete")
def delete_user(username: str = Form(...), current_admin: User = Depends(require_role("admin"))):
    if username == "root":
        raise HTTPException(status_code=403, detail="禁止删除 root 用户")

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM users WHERE username = %s", (username,))
            conn.commit()
            return {"message": f"用户 {username} 已删除"}
    finally:
        conn.close()


@router.post("/update-role")
def update_user_role(username: str = Form(...), role: str = Form(...)):
    if role not in ["admin", "staff", "manager"]:
        raise HTTPException(status_code=400, detail="无效的角色")

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("UPDATE users SET role = %s WHERE username = %s", (role, username))
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="用户不存在")
            conn.commit()
            return {"message": f"用户 {username} 的角色已更新为 {role}"}
    finally:
        conn.close()
