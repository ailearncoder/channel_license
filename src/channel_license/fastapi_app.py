from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import api as license_api
from . import database

import os


# NOTE: 不要在模块导入时创建 FastAPI 实例。
# 提供 api_init_routes(app: FastAPI) 函数以在外部创建的 app 上注册路由。


def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()


class ChannelCreate(BaseModel):
    name: str
    max_devices: Optional[int] = 1000
    license_duration_days: Optional[int] = 30
    description: Optional[str] = None


class ChannelEdit(BaseModel):
    name: Optional[str] = None
    max_devices: Optional[int] = None
    license_duration_days: Optional[int] = None
    description: Optional[str] = None


class LicenseStatusUpdate(BaseModel):
    new_status: str


def index():
    return FileResponse("src/license/static/index.html")


def api_list_devices(include_expired: bool = Query(False), db=Depends(get_db)):
    res = license_api.get_all_device_licenses(db, include_expired=include_expired)
    return JSONResponse(content=res)


def api_add_channel(payload: ChannelCreate, db=Depends(get_db)):
    res = license_api.add_channel(
        db,
        name=payload.name,
        max_devices=payload.max_devices,
        license_duration_days=payload.license_duration_days,
        description=payload.description,
    )
    if not res.get("success", False):
        raise HTTPException(status_code=400, detail=res.get("message", "add failed"))
    return JSONResponse(content=res)


def api_get_channels(db=Depends(get_db)):
    """返回所有渠道的列表（JSON）。"""
    res = license_api.get_all_channels(db)
    return JSONResponse(content=res)


def api_delete_channel(
    channel_id: Optional[int] = None,
    channel_name: Optional[str] = None,
    db=Depends(get_db),
):
    res = license_api.delete_channel(
        db, channel_id=channel_id, channel_name=channel_name
    )
    if not res.get("success", False):
        raise HTTPException(status_code=400, detail=res.get("message", "delete failed"))
    return JSONResponse(content=res)


def api_delete_device(
    device_id: Optional[int] = None,
    device_id_str: Optional[str] = None,
    force: bool = Query(False),
    db=Depends(get_db),
):
    res = license_api.delete_device(
        db, device_id=device_id, device_id_str=device_id_str, force=force
    )
    if not res.get("success", False):
        raise HTTPException(status_code=400, detail=res.get("message", "delete failed"))
    return JSONResponse(content=res)


def api_edit_channel(channel_id: int, payload: ChannelEdit, db=Depends(get_db)):
    res = license_api.edit_channel(
        db,
        channel_id=channel_id,
        name=payload.name,
        max_devices=payload.max_devices,
        license_duration_days=payload.license_duration_days,
        description=payload.description,
    )
    if not res.get("success", False):
        raise HTTPException(status_code=400, detail=res.get("message", "edit failed"))
    return JSONResponse(content=res)


def api_edit_license_status(
    license_id: int, payload: LicenseStatusUpdate, db=Depends(get_db)
):
    res = license_api.edit_license_status(
        db, license_id=license_id, new_status=payload.new_status
    )
    if not res.get("success", False):
        raise HTTPException(status_code=400, detail=res.get("message", "update failed"))
    return JSONResponse(content=res)


def api_init_db():
    # helper for local dev to create tables
    database.init_db()
    return {"success": True}


def api_init_routes(app: FastAPI, prefix: str = ""):
    """在给定的 FastAPI 实例上注册所有路由和静态挂载。

    设计契约：
    - 输入: app: FastAPI
    - 输出: None（通过修改 app 注册路由）
    - 错误模式: 若重复注册相同路由会抛出异常
    """

    # serve static web UI
    app.mount(f"{prefix}/static", StaticFiles(directory=f"{os.path.dirname(__file__)}/static"), name="static")

    # register routes
    app.get(f"{prefix}/", include_in_schema=False)(index)
    app.get(f"{prefix}/api/devices")(api_list_devices)
    app.post(f"{prefix}/api/channels")(api_add_channel)
    app.get(f"{prefix}/api/channels")(api_get_channels)
    app.delete(f"{prefix}/api/channels")(api_delete_channel)
    app.delete(f"{prefix}/api/devices")(api_delete_device)
    app.put(f"{prefix}/api/channels/{{channel_id}}")(api_edit_channel)
    app.patch(f"{prefix}/api/licenses/{{license_id}}/status")(api_edit_license_status)
    app.post(f"{prefix}/api/init_db", include_in_schema=False)(api_init_db)
