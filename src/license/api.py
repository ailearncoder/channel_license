"""API 封装：为 HTTP 服务提供可直接调用的函数，返回 JSON-serializable 的 dict。

这些函数都接受一个 SQLAlchemy Session（db）作为第一个参数，方便在 web 框架中把会话注入进来。
部分函数会在成功时执行 commit/refresh，以便调用者能获得最新状态；出错时会返回带错误信息的 dict。
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from . import database, exceptions, logic, models


def _iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt is not None else None


def _channel_to_dict(ch: models.Channel) -> Dict[str, Any]:
    return {
        "id": ch.id,
        "name": ch.name,
        "max_devices": ch.max_devices,
        "license_duration_days": ch.license_duration_days,
        "description": ch.description,
        "created_at": _iso(ch.created_at),
    }


def _license_to_dict(lic: models.License) -> Dict[str, Any]:
    return {
        "id": lic.id,
        "license_key": lic.license_key,
        "version": lic.version,
        "request_ip": lic.request_ip,
        "status": lic.status,
        "created_at": _iso(lic.created_at),
        "expires_at": _iso(lic.expires_at),
        "device_id": lic.device_id,
    }


def _device_to_dict(dev: models.Device, latest_license: Optional[models.License]) -> Dict[str, Any]:
    return {
        "id": dev.id,
        "device_id": dev.device_id_str,
        "channel": _channel_to_dict(dev.channel) if dev.channel is not None else None,
        "created_at": _iso(dev.created_at),
        "latest_license": _license_to_dict(latest_license) if latest_license is not None else None,
    }


def get_all_device_licenses(db: Session, include_expired: bool = False) -> Dict[str, Any]:
    """返回所有设备及其（最新）许可证信息。

    Args:
        db: SQLAlchemy Session
        include_expired: 如果为 True，则 latest_license 不过滤过期/非 active；否则使用 logic.find_latest_active_license_for_device

    返回:
        dict: {"devices": [...]}，每个元素包含 device 信息和 latest_license（或 null）
    """
    devices: List[models.Device] = db.query(models.Device).all()
    result: List[Dict[str, Any]] = []

    now = datetime.now()
    for d in devices:
        if include_expired:
            latest = (
                db.query(models.License)
                .filter(models.License.device_id == d.id)
                .order_by(models.License.expires_at.desc())
                .first()
            )
        else:
            latest = logic.find_latest_active_license_for_device(db, d)

        result.append(_device_to_dict(d, latest))

    return {"devices": result}


def add_channel(
    db: Session,
    name: str,
    max_devices: int = 1000,
    license_duration_days: int = 30,
    description: Optional[str] = None,
) -> Dict[str, Any]:
    """添加一个新的 Channel。

    在成功时会 commit 并返回新 channel 的字典表示；如果 name 已存在则返回错误信息。
    """
    existing = db.query(models.Channel).filter(models.Channel.name == name).one_or_none()
    if existing is not None:
        return {"success": False, "message": f"channel already exists: {name}"}

    ch = models.Channel(
        name=name,
        max_devices=max_devices,
        license_duration_days=license_duration_days,
        description=description,
    )
    db.add(ch)
    db.commit()
    db.refresh(ch)
    return {"success": True, "channel": _channel_to_dict(ch)}


def delete_channel(db: Session, channel_id: Optional[int] = None, channel_name: Optional[str] = None) -> Dict[str, Any]:
    """删除 channel。接受 channel_id 或 channel_name 中的一个。

    若 channel 下存在设备，则不允许删除，返回错误信息。
    成功时 commit 并返回 success=True。
    """
    q = db.query(models.Channel)
    if channel_id is not None:
        ch = q.filter(models.Channel.id == channel_id).one_or_none()
    elif channel_name is not None:
        ch = q.filter(models.Channel.name == channel_name).one_or_none()
    else:
        return {"success": False, "message": "channel_id or channel_name required"}

    if ch is None:
        return {"success": False, "message": "channel not found"}

    device_count = db.query(models.Device).filter(models.Device.channel_id == ch.id).count()
    if device_count > 0:
        return {"success": False, "message": "channel has devices and cannot be deleted"}

    db.delete(ch)
    db.commit()
    return {"success": True}


def edit_channel(
    db: Session,
    channel_id: Optional[int] = None,
    channel_name: Optional[str] = None,
    *,
    name: Optional[str] = None,
    max_devices: Optional[int] = None,
    license_duration_days: Optional[int] = None,
    description: Optional[str] = None,
) -> Dict[str, Any]:
    """编辑 channel 的字段。接受 channel_id 或 channel_name 定位 channel。

    成功时 commit 并返回更新后的 channel。
    """
    q = db.query(models.Channel)
    if channel_id is not None:
        ch = q.filter(models.Channel.id == channel_id).one_or_none()
    elif channel_name is not None:
        ch = q.filter(models.Channel.name == channel_name).one_or_none()
    else:
        return {"success": False, "message": "channel_id or channel_name required"}

    if ch is None:
        return {"success": False, "message": "channel not found"}

    if name is not None:
        ch.name = name
    if max_devices is not None:
        ch.max_devices = max_devices
    if license_duration_days is not None:
        ch.license_duration_days = license_duration_days
    if description is not None:
        ch.description = description

    db.commit()
    db.refresh(ch)
    return {"success": True, "channel": _channel_to_dict(ch)}


def edit_license_status(db: Session, license_id: int, new_status: str) -> Dict[str, Any]:
    """修改指定 license 的状态（例如 'active', 'revoked', 'expired' 等）。

    成功时 commit 并返回更新后的 license 字典。
    """
    lic = db.query(models.License).filter(models.License.id == license_id).one_or_none()
    if lic is None:
        return {"success": False, "message": "license not found"}

    lic.status = new_status
    db.commit()
    db.refresh(lic)
    return {"success": True, "license": _license_to_dict(lic)}


# 便捷的带会话管理的封装：如果应用希望直接调用而无需手动管理 session，可用这些函数
def get_all_device_licenses_with_session(include_expired: bool = False) -> Dict[str, Any]:
    with database.get_db_session() as db:
        return get_all_device_licenses(db, include_expired=include_expired)


def add_channel_with_session(
    name: str, max_devices: int = 1000, license_duration_days: int = 30, description: Optional[str] = None
) -> Dict[str, Any]:
    with database.get_db_session() as db:
        return add_channel(db, name, max_devices, license_duration_days, description)


def get_all_channels(db: Session) -> Dict[str, Any]:
    """返回所有 channel 的列表（字典格式）。"""
    channels = db.query(models.Channel).order_by(models.Channel.id.asc()).all()
    return {"channels": [_channel_to_dict(ch) for ch in channels]}


def get_all_channels_with_session() -> Dict[str, Any]:
    with database.get_db_session() as db:
        return get_all_channels(db)
