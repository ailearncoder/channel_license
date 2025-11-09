import importlib
import tempfile
from pathlib import Path
from datetime import datetime, timedelta, timezone

import pytest


def setup_db(tmp_path: Path):
    """将 license.database 的 DATABASE_FILE_PATH 指向临时文件并初始化数据库。"""
    import license

    db_file = tmp_path / "test_license.db"
    # 修改配置并重新加载 database 模块以创建基于该文件的 engine
    license.config.DATABASE_FILE_PATH = str(db_file)
    importlib.reload(license.database)
    # 初始化表
    license.database.init_db()
    return license


def test_new_device_creates_device_and_license(tmp_path):
    license_pkg = setup_db(tmp_path)

    with license_pkg.database.get_db_session() as db:
        # create a channel
        ch = license_pkg.models.Channel(name="default", max_devices=10, license_duration_days=7)
        db.add(ch)
        db.commit()
        db.refresh(ch)

    with license_pkg.database.get_db_session() as db:
        lic = license_pkg.logic.process_license_request(db, "dev-new-1", "default", "1.1.1.1")
        db.commit()
        db.refresh(lic)

        assert lic.id is not None
        assert lic.device_id is not None
        assert lic.version == license_pkg.config.CURRENT_LICENSE_VERSION
        assert lic.expires_at > datetime.now()


def test_existing_device_returns_unexpired_license(tmp_path):
    license_pkg = setup_db(tmp_path)

    with license_pkg.database.get_db_session() as db:
        ch = license_pkg.models.Channel(name="default", max_devices=10, license_duration_days=7)
        db.add(ch)
        db.commit()
        db.refresh(ch)

    with license_pkg.database.get_db_session() as db:
        first = license_pkg.logic.process_license_request(db, "dev-2", "default", "1.1.1.2")
        db.commit()
        db.refresh(first)

    with license_pkg.database.get_db_session() as db:
        before_count = db.query(license_pkg.models.License).count()
        returned = license_pkg.logic.process_license_request(db, "dev-2", "default", "1.1.1.2")
        db.commit()
        after_count = db.query(license_pkg.models.License).count()

        assert after_count == before_count
        assert returned.id == first.id


def test_existing_device_with_expired_license_creates_new(tmp_path):
    license_pkg = setup_db(tmp_path)

    with license_pkg.database.get_db_session() as db:
        ch = license_pkg.models.Channel(name="default", max_devices=10, license_duration_days=1)
        db.add(ch)
        db.commit()
        db.refresh(ch)

        # create device
        dev = license_pkg.models.Device(device_id_str="dev-expired-1", channel_id=ch.id)
        db.add(dev)
        db.commit()
        db.refresh(dev)
        dev_id = dev.id

        # create an expired license
        expired = license_pkg.models.License(
            license_key="OLD",
            version=license_pkg.config.CURRENT_LICENSE_VERSION,
            request_ip="1.2.3.4",
            status="active",
            created_at=datetime.now() - timedelta(days=10),
            expires_at=datetime.now() - timedelta(days=5),
            device_id=dev.id,
        )
        db.add(expired)
        db.commit()
        db.refresh(expired)

    with license_pkg.database.get_db_session() as db:
        before_count = db.query(license_pkg.models.License).filter(license_pkg.models.License.device_id == dev_id).count()
        new_lic = license_pkg.logic.process_license_request(db, "dev-expired-1", "default", "5.5.5.5")
        db.commit()
        db.refresh(new_lic)

        after_count = db.query(license_pkg.models.License).filter(license_pkg.models.License.device_id == dev_id).count()

        assert after_count == before_count + 1
        assert new_lic.expires_at > datetime.now()


def test_channel_device_limit_exceeded(tmp_path):
    license_pkg = setup_db(tmp_path)

    with license_pkg.database.get_db_session() as db:
        ch = license_pkg.models.Channel(name="limited", max_devices=1, license_duration_days=7)
        db.add(ch)
        db.commit()
        db.refresh(ch)

        # create one device to reach the limit
        dev = license_pkg.models.Device(device_id_str="dev-limit-1", channel_id=ch.id)
        db.add(dev)
        db.commit()

    with license_pkg.database.get_db_session() as db:
        with pytest.raises(license_pkg.exceptions.DeviceLimitExceeded):
            license_pkg.logic.process_license_request(db, "dev-limit-2", "limited", "9.9.9.9")


def test_channel_not_found_raises(tmp_path):
    license_pkg = setup_db(tmp_path)

    with license_pkg.database.get_db_session() as db:
        with pytest.raises(license_pkg.exceptions.ChannelNotFound):
            license_pkg.logic.process_license_request(db, "dev-nochan", "no-such-channel", "8.8.8.8")
