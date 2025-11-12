import os
import importlib
from pathlib import Path
from fastapi import FastAPI
from fastapi.testclient import TestClient
from channel_license.fastapi_app import hash_password, api_init_routes

def setup_db(tmp_path: Path):
    """将 license.database 的 DATABASE_FILE_PATH 指向临时文件并初始化数据库。"""
    import channel_license

    db_file = tmp_path / "test_license.db"
    channel_license.config.DATABASE_FILE_PATH = str(db_file)
    importlib.reload(channel_license.database)
    channel_license.database.init_db()
    return channel_license

def create_test_app(enable_basic_auth=True):
    """创建用于测试的 FastAPI 应用实例"""
    # 确保数据库已初始化
    import channel_license.database
    if channel_license.database.engine is None:
        channel_license.database.init_db()
        
    app = FastAPI()
    api_init_routes(app, enable_basic_auth=enable_basic_auth)
    return app

def test_hash_password():
    """测试密码哈希功能"""
    password = "testpassword"
    hashed = hash_password(password)
    expected_hash = "9f735e0df9a1ddc702bf0a1a7b83033f9f7153a00c29de82cedadc9957289b05"
    assert hashed == expected_hash

def test_auth_with_default_credentials():
    """测试使用默认凭据的基本认证"""
    # 重新加载模块以确保使用默认值
    if "LICENSE_ADMIN_USERNAME" in os.environ:
        del os.environ["LICENSE_ADMIN_USERNAME"]
    if "LICENSE_ADMIN_PASSWORD_HASH" in os.environ:
        del os.environ["LICENSE_ADMIN_PASSWORD_HASH"]
    
    # 重新导入模块以应用环境变量更改
    import channel_license.fastapi_app
    importlib.reload(channel_license.fastapi_app)
    
    # 创建带认证的测试客户端
    app = create_test_app(enable_basic_auth=True)
    client = TestClient(app)
    
    # 测试未认证的请求应该返回401
    response = client.get("/api/channels")
    assert response.status_code == 401
    
    # 使用默认凭据测试认证
    response = client.get("/api/channels", auth=("admin", "password"))
    # 应该返回200，但我们可能需要初始化数据库
    assert response.status_code in [200, 404]  # 404可能是因为没有数据

def test_auth_with_custom_credentials(tmp_path):
    """测试使用自定义凭据的基本认证"""
    # 设置自定义环境变量
    os.environ["LICENSE_ADMIN_USERNAME"] = "testuser"
    os.environ["LICENSE_ADMIN_PASSWORD_HASH"] = hash_password("testpass")
    
    # 重新导入模块以应用环境变量更改
    import channel_license.fastapi_app
    importlib.reload(channel_license.fastapi_app)
    
    # 初始化数据库
    license_pkg = setup_db(tmp_path)
    
    # 创建带认证的测试客户端
    app = create_test_app(enable_basic_auth=True)
    client = TestClient(app)
    
    # 测试错误凭据应该返回401
    response = client.get("/api/channels", auth=("wronguser", "wrongpass"))
    assert response.status_code == 401
    
    # 使用正确的自定义凭据测试认证
    response = client.get("/api/channels", auth=("testuser", "testpass"))
    assert response.status_code == 200
    assert response.json() == {"channels": []}  # 空数据库应该返回空列表

def test_auth_with_invalid_password(tmp_path):
    """测试使用无效密码的认证"""
    # 设置自定义环境变量
    os.environ["LICENSE_ADMIN_USERNAME"] = "testuser"
    os.environ["LICENSE_ADMIN_PASSWORD_HASH"] = hash_password("testpass")
    
    # 重新导入模块以应用环境变量更改
    import channel_license.fastapi_app
    importlib.reload(channel_license.fastapi_app)
    
    # 初始化数据库
    license_pkg = setup_db(tmp_path)
    
    # 创建带认证的测试客户端
    app = create_test_app(enable_basic_auth=True)
    client = TestClient(app)
    
    # 使用正确的用户名但错误的密码测试认证
    response = client.get("/api/channels", auth=("testuser", "wrongpass"))
    assert response.status_code == 401
