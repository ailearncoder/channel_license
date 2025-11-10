from fastapi import FastAPI

from .fastapi_app import api_init_routes


# 创建 FastAPI 实例并通过 api_init_routes 注册所有路由
app = FastAPI(title="License Service")
api_init_routes(app)
