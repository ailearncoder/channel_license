"""核心业务逻辑（占位实现）。

文档未指定的低层实现使用占位函数或简单实现以便演示。
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, cast
from sqlalchemy.orm import Session

from . import models
from .config import CURRENT_LICENSE_VERSION
from .exceptions import ChannelNotFound, DeviceLimitExceeded


def find_device_by_id(db: Session, device_id_str: str) -> Optional[models.Device]:
    return db.query(models.Device).filter(models.Device.device_id_str == device_id_str).one_or_none()


def find_channel_by_name(db: Session, channel_name: str) -> Optional[models.Channel]:
    return db.query(models.Channel).filter(models.Channel.name == channel_name).one_or_none()


def count_devices_in_channel(db: Session, channel_id: int) -> int:
    return db.query(models.Device).filter(models.Device.channel_id == channel_id).count()


def find_latest_active_license_for_device(db: Session, device: models.Device) -> Optional[models.License]:
    # 返回按 expires_at 降序的第一个仍为 active 且未过期的许可证
    now = datetime.now()
    return (
        db.query(models.License)
        .filter(models.License.device_id == device.id)
        .filter(models.License.status == "active")
        .filter(models.License.expires_at > now)
        .order_by(models.License.expires_at.desc())
        .first()
    )


def create_new_device(db: Session, device_id_str: str, channel_id: int) -> models.Device:
    device = models.Device(device_id_str=device_id_str, channel_id=channel_id)
    db.add(device)
    # 不在此处 commit，交由上层事务管理
    db.flush()  # 让 SQLAlchemy 生成 ID
    return device


def calculate_expiry_date(license_duration_days: int) -> datetime:
    return datetime.now() + timedelta(days=license_duration_days)


def generate_license_key(device_id: str, expires_at: datetime) -> str:
    """占位的 license key 生成器。

    文档未规定加密/签名方式，当前返回一个可读的占位字符串。
    """
    return f"LIC::{device_id}::{int(expires_at.timestamp())}"


def create_new_license(
    db: Session,
    device: models.Device,
    key: str,
    version: str,
    ip: Optional[str],
    expires_at: datetime,
) -> models.License:
    lic = models.License(
        license_key=key,
        version=version,
        request_ip=ip,
        expires_at=expires_at,
        device_id=device.id,
        status="active",
    )
    db.add(lic)
    db.flush()
    return lic


def process_license_request(db: Session, device_id_str: str, channel_name: str, request_ip: str) -> models.License:
    """处理许可证请求的主函数（遵循 plan.md 中的伪代码流程）。

    对文档未指明的低层细节采用占位实现。
    """
    # 1. 查询设备
    device = find_device_by_id(db, device_id_str)

    # 2. 如果设备已存在
    if device is not None:
        latest_license = find_latest_active_license_for_device(db, device)
        if latest_license is not None:
            return latest_license

        channel = device.channel

    else:
        # 3. 设备不存在：查找渠道
        channel = find_channel_by_name(db, channel_name)
        if channel is None:
            raise ChannelNotFound(f"渠道不存在: {channel_name}")

        # 3.2 检查渠道设备配额
        channel_id_int = cast(int, channel.id)
        current_device_count = count_devices_in_channel(db, channel_id_int)
        channel_max_devices_int = cast(int, channel.max_devices)
        if current_device_count >= channel_max_devices_int:
            raise DeviceLimitExceeded(f"渠道设备已达上限: {channel_name}")

        # 3.3 创建新设备
        device = create_new_device(db, device_id_str, channel_id_int)

    # 4. 创建新许可证
    expires_at = calculate_expiry_date(cast(int, channel.license_duration_days))
    license_key_str = generate_license_key(device_id=device_id_str, expires_at=expires_at)

    new_license = create_new_license(
        db=db,
        device=device,
        key=license_key_str,
        version=CURRENT_LICENSE_VERSION,
        ip=request_ip,
        expires_at=expires_at,
    )

    # 注意：调用者负责 commit/refresh
    return new_license
