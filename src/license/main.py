"""示例入口：演示如何初始化数据库并调用 process_license_request。"""
from pprint import pprint

from . import database
from .database import get_db_session
from . import logic
from . import exceptions
from . import models


def run_demo():
    # 初始化数据库（创建表）
    database.init_db()

    # 先确保有一个示例 channel
    with get_db_session() as db:
        ch = db.query(models.Channel).filter(models.Channel.name == "default").one_or_none()
        if ch is None:
            ch = models.Channel(name="default", max_devices=5, license_duration_days=7, description="示例渠道")
            db.add(ch)
            db.commit()
            db.refresh(ch)

    # 进行一次许可证请求演示
    device_id = "device-001"
    request_ip = "127.0.0.1"

    with get_db_session() as db:
        try:
            new_lic = logic.process_license_request(db, device_id, "default", request_ip)
            db.commit()
            db.refresh(new_lic)
            print("获得许可证:")
            pprint({
                "id": new_lic.id,
                "license_key": new_lic.license_key,
                "version": new_lic.version,
                "expires_at": new_lic.expires_at.isoformat(),
                "device_id": new_lic.device_id,
            })

        except exceptions.ChannelNotFound as e:
            print("错误: 渠道未找到", e)
        except exceptions.DeviceLimitExceeded as e:
            print("错误: 渠道设备已满", e)


if __name__ == "__main__":
    run_demo()
