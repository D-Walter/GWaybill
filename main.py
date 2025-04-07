from fastapi import FastAPI
from routers import login, admin_users, waybills
from routers.login import initialize_root_password
from dotenv import load_dotenv
from logger import OperationLogMiddleware
import os

load_dotenv()
# 为root用户生成随机密码并输出
initialize_root_password()
app = FastAPI(title="物流系统", description="含JWT认证与签名校验", version="1.1")
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],  # 或限定某些前端地址
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )
app.add_middleware(OperationLogMiddleware)
app.include_router(login.router)
app.include_router(admin_users.router)
app.include_router(waybills.router)
