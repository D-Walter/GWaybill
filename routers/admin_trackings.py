from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

import pymysql
from auth_dependencies import require_role
from db import get_connection
import hashlib


router = APIRouter(prefix="/admin_trackings", tags=["运单跟踪"], dependencies=[Depends(require_role("manager", "staff", "admin"))])


def generate_tracking_id(status: str, timestamp: datetime, description: str, suffix: int = 0) -> str:
    base_str = (status or "") + (timestamp.isoformat() if timestamp else "") + (description or "")
    normalized_str = "".join(base_str.split())  # 去除所有空白字符
    base_hash = hashlib.md5(normalized_str.encode("utf-8")).hexdigest()[:16]  # 截取前16位
    return f"{base_hash}_{suffix}" if suffix > 0 else base_hash


class Tracking(BaseModel):
    waybill_number: str
    location: Optional[str] = None
    status: Optional[str] = None
    timestamp: Optional[datetime] = None
    description: Optional[str] = None
    reserved1: Optional[str] = None
    reserved2: Optional[str] = None
    reserved3: Optional[str] = None


@router.post("/")
def create_tracking(tracking: Tracking):
    conn = get_connection()
    try:
        with conn.cursor(cursor=pymysql.cursors.DictCursor) as cursor:
            suffix = 0
            max_attempts = 100
            tracking_id = generate_tracking_id(tracking.status, tracking.timestamp, tracking.description, suffix)

            while suffix < max_attempts:
                # 检查ID是否已存在
                cursor.execute("SELECT * FROM trackings WHERE id = %s", (tracking_id,))
                existing = cursor.fetchone()

                if not existing:
                    break  # 可用ID，跳出循环
                elif existing["status"] == tracking.status and existing["timestamp"] == tracking.timestamp and existing["description"] == tracking.description:
                    return {"message": "该跟踪记录已存在，未重复添加。", "tracking_id": tracking_id}
                else:
                    suffix += 1
                    tracking_id = generate_tracking_id(
                        suffix,
                        tracking.status,
                        tracking.timestamp,
                        tracking.description,
                    )

            if suffix >= max_attempts:
                raise HTTPException(status_code=500, detail="无法生成唯一ID，创建失败。")

            # 插入记录
            sql_insert = """
            INSERT INTO trackings (
                id, waybill_number, location, status, timestamp, description,
                reserved1, reserved2, reserved3
            ) VALUES (
                %(id)s, %(waybill_number)s, %(location)s, %(status)s, %(timestamp)s, %(description)s,
                %(reserved1)s, %(reserved2)s, %(reserved3)s
            )
            """
            tracking_data = tracking.dict()
            tracking_data["id"] = tracking_id
            cursor.execute(sql_insert, tracking_data)
        conn.commit()
        return {"message": "跟踪记录创建成功", "tracking_id": tracking_id}
    finally:
        conn.close()


@router.get("/{waybill_number}", response_model=List[Tracking])
def get_trackings_by_waybill(waybill_number: str):
    conn = get_connection()
    try:
        with conn.cursor(dictionary=True) as cursor:
            sql = "SELECT * FROM trackings WHERE waybill_number = %s ORDER BY timestamp ASC"
            cursor.execute(sql, (waybill_number,))
            result = cursor.fetchall()
        return result
    finally:
        conn.close()


@router.delete("/{tracking_id}")
def delete_tracking(tracking_id: str):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = "DELETE FROM trackings WHERE id = %s"
            affected = cursor.execute(sql, (tracking_id,))
        conn.commit()
        if affected == 0:
            raise HTTPException(status_code=404, detail="Tracking record not found.")
        return {"message": "跟踪记录删除成功", "tracking_id": tracking_id}
    finally:
        conn.close()


@router.put("/{tracking_id}")
def update_tracking(tracking_id: str, tracking: Tracking):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            fields = ", ".join([f"{key}=%({key})s" for key in tracking.dict().keys()])
            sql = f"UPDATE trackings SET {fields} WHERE id=%(id)s"
            values = tracking.dict()
            values["id"] = tracking_id
            affected = cursor.execute(sql, values)
        conn.commit()
        if affected == 0:
            raise HTTPException(status_code=404, detail="Tracking record not found.")
        return {"message": "跟踪记录更新成功", "tracking_id": tracking_id}
    finally:
        conn.close()
