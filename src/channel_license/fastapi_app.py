from typing import Optional, List

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel

from . import api as license_api
from . import database

import os
import secrets
import hashlib


# NOTE: 不要在模块导入时创建 FastAPI 实例。
# 提供 api_init_routes(app: FastAPI) 函数以在外部创建的 app 上注册路由。

# Basic Auth 配置
security = HTTPBasic()

# 从环境变量读取用户名和密码，如果环境变量未设置，则使用默认值
USERNAME = os.environ.get("LICENSE_ADMIN_USERNAME", "admin")
PASSWORD_HASH = os.environ.get("LICENSE_ADMIN_PASSWORD_HASH")

# 如果没有设置密码哈希，则使用默认密码"password"的哈希值
if PASSWORD_HASH is None:
    # "password" 的 SHA256 哈希值
    DEFAULT_PASSWORD_HASH = "5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8"
    PASSWORD_HASH = DEFAULT_PASSWORD_HASH


def hash_password(password: str) -> str:
    """计算密码的SHA256哈希值"""
    return hashlib.sha256(password.encode()).hexdigest()


def get_current_username(credentials: HTTPBasicCredentials = Depends(security)):
    """验证 Basic Auth 凭据"""
    # 确保 USERNAME 和 PASSWORD_HASH 不为 None，满足类型检查要求
    username = USERNAME or "admin"
    password_hash = PASSWORD_HASH or "5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8"
    
    correct_username = secrets.compare_digest(credentials.username, username)
    
    # 验证密码哈希而不是明文密码
    hashed_input_password = hash_password(credentials.password)
    correct_password = secrets.compare_digest(hashed_input_password, password_hash)
    
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


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
    return FileResponse(f"{os.path.dirname(__file__)}/static/index.html")


def api_list_devices(include_expired: bool = Query(False), db=Depends(get_db)):
    res = license_api.get_all_device_licenses(db, include_expired=include_expired)
    return JSONResponse(content=res)


def api_add_channel(payload: ChannelCreate, db=Depends(get_db)):
    res = license_api.add_channel(
        db,
        name=payload.name,
        max_devices=payload.max_devices if payload.max_devices is not None else 1000,
        license_duration_days=payload.license_duration_days if payload.license_duration_days is not None else 30,
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
        max_devices=payload.max_devices if payload.max_devices is not None else None,
        license_duration_days=payload.license_duration_days if payload.license_duration_days is not None else None,
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


def api_init_routes(app: FastAPI, prefix: str = "", enable_basic_auth: bool = False):
    """在给定的 FastAPI 实例上注册所有路由和静态挂载。

    设计契约：
    - 输入: app: FastAPI
    - 输出: None（通过修改 app 注册路由）
    - 错误模式: 若重复注册相同路由会抛出异常
    """

    # serve static web UI
    app.mount(f"{prefix}/static", StaticFiles(directory=f"{os.path.dirname(__file__)}/static"), name="static")

    # 构建依赖项列表
    dependencies: List = [Depends(get_current_username)] if enable_basic_auth else []

    # register routes
    app.get(f"{prefix}/", include_in_schema=False)(index)
    app.get(f"{prefix}/api/devices", dependencies=dependencies)(api_list_devices)
    app.post(f"{prefix}/api/channels", dependencies=dependencies)(api_add_channel)
    app.get(f"{prefix}/api/channels", dependencies=dependencies)(api_get_channels)
    app.delete(f"{prefix}/api/channels", dependencies=dependencies)(api_delete_channel)
    app.delete(f"{prefix}/api/devices", dependencies=dependencies)(api_delete_device)
    app.put(f"{prefix}/api/channels/{{channel_id}}", dependencies=dependencies)(api_edit_channel)
    app.patch(f"{prefix}/api/licenses/{{license_id}}/status", dependencies=dependencies)(api_edit_license_status)
    app.post(f"{prefix}/api/init_db", include_in_schema=False)(api_init_db)
