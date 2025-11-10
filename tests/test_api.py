import importlib
from pathlib import Path
from datetime import datetime


def setup_db(tmp_path: Path):
    """将 license.database 的 DATABASE_FILE_PATH 指向临时文件并初始化数据库（与 tests/test_logic.py 保持一致）。"""
    import channel_license

    db_file = tmp_path / "test_license.db"
    channel_license.config.DATABASE_FILE_PATH = str(db_file)
    importlib.reload(channel_license.database)
    channel_license.database.init_db()
    return channel_license


def test_api_add_edit_delete_channel(tmp_path):
    license_pkg = setup_db(tmp_path)

    with license_pkg.database.get_db_session() as db:
        # add
        res = license_pkg.api.add_channel(db, name="api-ch", max_devices=5, license_duration_days=3, description="d")
        assert res["success"] is True
        ch = res["channel"]
        assert ch["name"] == "api-ch"

        ch_id = ch["id"]

        # edit
        res2 = license_pkg.api.edit_channel(db, channel_id=ch_id, name="api-ch-2", max_devices=10)
        assert res2["success"] is True
        assert res2["channel"]["name"] == "api-ch-2"
        assert res2["channel"]["max_devices"] == 10

        # delete
        res3 = license_pkg.api.delete_channel(db, channel_id=ch_id)
        assert res3["success"] is True

        # delete again -> not found
        res4 = license_pkg.api.delete_channel(db, channel_id=ch_id)
        assert res4["success"] is False


def test_api_delete_channel_with_devices(tmp_path):
    license_pkg = setup_db(tmp_path)

    with license_pkg.database.get_db_session() as db:
        ch = license_pkg.models.Channel(name="hasdev", max_devices=5, license_duration_days=7)
        db.add(ch)
        db.commit()
        db.refresh(ch)

        dev = license_pkg.models.Device(device_id_str="dev-1", channel_id=ch.id)
        db.add(dev)
        db.commit()

        res = license_pkg.api.delete_channel(db, channel_id=ch.id)
        assert res["success"] is False
        assert "cannot be deleted" in res["message"] or "has devices" in res["message"]


def test_edit_license_status_and_get_all_device_licenses(tmp_path):
    license_pkg = setup_db(tmp_path)

    with license_pkg.database.get_db_session() as db:
        ch = license_pkg.models.Channel(name="licch", max_devices=5, license_duration_days=7)
        db.add(ch)
        db.commit()
        db.refresh(ch)

        # create license via logic
        lic = license_pkg.logic.process_license_request(db, "dev-lic-1", "licch", "1.2.3.4")
        db.commit()
        db.refresh(lic)

        # get all devices
        all_res = license_pkg.api.get_all_device_licenses(db)
        assert "devices" in all_res
        assert any(d["device_id"] == "dev-lic-1" for d in all_res["devices"])

        # edit license status
        res = license_pkg.api.edit_license_status(db, lic.id, "revoked")
        assert res["success"] is True
        assert res["license"]["status"] == "revoked"

        # ensure get reflects change
        all_res2 = license_pkg.api.get_all_device_licenses(db)
        dev_entries = [d for d in all_res2["devices"] if d["device_id"] == "dev-lic-1"]
        assert dev_entries
        latest = dev_entries[0]["latest_license"]
        # since logic.find_latest_active_license_for_device filters active & not expired,
        # after revoking latest_license may be None; but edit_license_status updated DB
        assert latest is None or latest["status"] == "revoked"
