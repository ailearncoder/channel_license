"""SQLAlchemy ORM 模型定义：Channel, Device, License"""
from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
)
from sqlalchemy.orm import declarative_base, relationship


Base = declarative_base()


class Channel(Base):
    __tablename__ = "channels"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    max_devices = Column(Integer, nullable=False, default=1000)
    license_duration_days = Column(Integer, nullable=False, default=30)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now())

    devices = relationship("Device", back_populates="channel", cascade="save-update")


class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True)
    device_id_str = Column(String(255), nullable=False, unique=True, index=True)
    channel_id = Column(Integer, ForeignKey("channels.id", ondelete="RESTRICT"), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now())

    channel = relationship("Channel", back_populates="devices")
    licenses = relationship("License", back_populates="device", cascade="save-update, merge")


class License(Base):
    __tablename__ = "licenses"

    id = Column(Integer, primary_key=True)
    license_key = Column(Text, nullable=False)
    version = Column(String(64), nullable=False)
    request_ip = Column(String(64), nullable=True)
    status = Column(String(32), nullable=False, default="active", index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now())
    expires_at = Column(DateTime, nullable=False)
    device_id = Column(Integer, ForeignKey("devices.id", ondelete="RESTRICT"), nullable=False)

    device = relationship("Device", back_populates="licenses")
