from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from auth_dependencies import require_role
from db import get_connection

router = APIRouter(prefix="/admin_waybills", tags=["用户管理"], dependencies=[Depends(require_role("manager", "staff", "admin"))])


class Waybill(BaseModel):
    waybill_number: str
    sender_name: Optional[str] = None
    sender_phone: Optional[str] = None
    receiver_name: Optional[str] = None
    receiver_phone: Optional[str] = None
    origin: Optional[str] = None
    origin_city: Optional[str] = None
    destination: Optional[str] = None
    destination_city: Optional[str] = None
    status: Optional[str] = None
    is_insured: Optional[bool] = None
    insured_amount: Optional[float] = None
    value_added_services: Optional[str] = None
    image_urls: Optional[str] = None
    media_attachments: Optional[str] = None
    weight: Optional[float] = None
    length: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None
    volume: Optional[float] = None
    goods_type: Optional[str] = None
    package_type: Optional[str] = None
    description: Optional[str] = None
    reserved1: Optional[str] = None
    reserved2: Optional[str] = None
    reserved3: Optional[str] = None


@router.post("/")
def create_waybill(waybill: Waybill):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
            INSERT INTO waybills (
                waybill_number, sender_name, sender_phone, receiver_name, receiver_phone,
                origin, origin_city, destination, destination_city, status,
                is_insured, insured_amount, value_added_services, image_urls, media_attachments,
                weight, length, width, height, volume,
                goods_type, package_type, description,
                reserved1, reserved2, reserved3
            ) VALUES (
                %(waybill_number)s, %(sender_name)s, %(sender_phone)s, %(receiver_name)s, %(receiver_phone)s,
                %(origin)s, %(origin_city)s, %(destination)s, %(destination_city)s, %(status)s,
                %(is_insured)s, %(insured_amount)s, %(value_added_services)s, %(image_urls)s, %(media_attachments)s,
                %(weight)s, %(length)s, %(width)s, %(height)s, %(volume)s,
                %(goods_type)s, %(package_type)s, %(description)s,
                %(reserved1)s, %(reserved2)s, %(reserved3)s
            )
            """
            cursor.execute(sql, waybill.dict())
        conn.commit()
        return {"message": "运单创建成功", "waybill_number": waybill.waybill_number}
    finally:
        conn.close()


@router.put("/{waybill_number}")
def update_waybill(waybill_number: str, waybill: Waybill):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            fields = ", ".join([f"{key}=%({key})s" for key in waybill.dict().keys()])
            sql = f"UPDATE waybills SET {fields} WHERE waybill_number=%(waybill_number)s AND is_deleted = FALSE"
            values = waybill.dict()
            values["waybill_number"] = waybill_number
            affected = cursor.execute(sql, values)
        conn.commit()
        if affected == 0:
            raise HTTPException(status_code=404, detail="Waybill not found or deleted.")
        return {"message": "运单更新成功", "waybill_number": waybill.waybill_number}
    finally:
        conn.close()


@router.delete("/{waybill_number}")
def delete_waybill(waybill_number: str):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
            UPDATE waybills SET is_deleted = TRUE, deleted_at = %s
            WHERE waybill_number = %s AND is_deleted = FALSE
            """
            affected = cursor.execute(sql, (datetime.now(), waybill_number))
        conn.commit()
        if affected == 0:
            raise HTTPException(status_code=404, detail="Waybill not found or already deleted.")
        return {"message": "运单删除成功", "waybill_number": waybill_number}
    finally:
        conn.close()
