from fastapi import FastAPI

from .fastapi_app import api_init_routes


# 创建 FastAPI 实例并通过 api_init_routes 注册所有路由
# 可以通过 enable_basic_auth 参数启用或禁用 Basic Auth 认证
app = FastAPI(title="License Service")
api_init_routes(app, enable_basic_auth=False)  # 设置为 True 以启用 Basic Auth