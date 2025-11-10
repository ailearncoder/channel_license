## ChannelLicense（channel-license）

ChannelLicense 是一个用于管理设备许可证的轻量服务示例，包含数据库模型、业务逻辑和一个可嵌入的 FastAPI 接口与简单静态前端。

主要功能：
- 管理渠道（channel）和设备（device）的许可证。
- 通过 API 创建/编辑/删除渠道与设备许可证，支持简单的静态 UI（位于 `src/license/static`）。
- 提供一个演示入口用于在本地初始化数据库并演示许可证请求流程。

## 快速开始


说明：项目包在打包/发布时的分发名为 `channel-license`，包内部 Python 导入路径仍保留为 `license`，以保持向后兼容。

推荐在虚拟环境中运行（macOS / zsh）：

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
# 可安装项目及常用开发依赖（若你的打包工具支持 dev 依赖，可以使用相应命令）
python -m pip install -e .
python -m pip install fastapi uvicorn pytest
```

启动示例演示（会初始化 SQLite 数据库并演示一次许可证请求）：

```bash
# 安装为可执行包后，可运行 entrypoint：
# 分发名: `channel-license`，但包导入仍为 `license`（以兼容现有导入）
channel-license
# 或直接运行演示脚本（在包安装/可导入的前提下）：
python -m license.main
```

启动 FastAPI 服务（用于开发）：

```bash
# 使用 uvicorn 启动，app 在 `src/license/app.py` 中暴露为 `app` 对象
uvicorn license.app:app --reload --host 127.0.0.1 --port 8000
# 打开 http://127.0.0.1:8000/ 可访问静态前端（通过 /static 提供）
```

## 运行测试

项目使用 `pytest`，运行所有测试：

```bash
pytest -q
```

## 代码结构

重要文件/目录：
- `src/license/` - 包含源代码。
  - `api.py` - 业务层对外的函数集合（被 FastAPI 路由调用）。
  - `app.py` - 创建FastAPI `app` 并注册路由的最小入口点。
  - `fastapi_app.py` - 定义路由和与 FastAPI 的集成（`api_init_routes`）。
  - `database.py` - SQLAlchemy 会话与 DB 初始化。
  - `logic.py` - 主要业务逻辑（许可证申请/校验等）。
  - `models.py` - SQLAlchemy ORM 模型定义。
  - `static/` - 一个简单的前端静态页面及 JS（`index.html`, `app.js`）。

测试位于 `tests/`，包含 API 层与业务逻辑的单元测试。

## 配置

默认使用项目内的 SQLite（由 `database.py` 控制）。如需更换数据库，请在 `src/license/config.py` 中或通过环境变量修改相应配置，然后重新初始化数据库。

## 开发指南

- 使用可编辑安装 `pip install -e .` 开发时更改可立即生效（需在虚拟环境中）。
- 代码格式化建议使用 `black`，静态检查/测试请运行 `pytest`。
- 添加新依赖请更新 `pyproject.toml` 中的 `dependencies` 或开发依赖组。

## 注意事项与边界情况

- 本项目为示例性质，默认数据库和错误处理较为简单，线上使用前请加固认证、授权和持久化策略。
- 如果在导入包或运行 entrypoint 时遇到模块不可导入的问题，请先确保已在虚拟环境中运行 `pip install -e .` 或将 `src/` 添加到 `PYTHONPATH`。

## 许可证

请在此处填写项目许可证（例如 MIT、Apache-2.0），当前仓库未强制指定。
