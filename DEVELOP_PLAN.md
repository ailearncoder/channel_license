---

### **开发计划：服务端许可证核心模块**

**目标**: 构建一个独立的、基于SQLAlchemy的Python模块，用于处理许可证的全部核心业务逻辑。该模块将与数据库交互，并向上层（如HTTP服务）提供清晰的接口和业务异常。

**技术选型**:
*   **ORM**: SQLAlchemy
*   - **数据库**: SQLite (文件存储)

---

### **第一步：项目结构与环境配置**

此步骤旨在建立一个清晰、可维护的项目骨架。

1.  **目录结构**:
    *   `license_service/`
        *   `config.py`: 存放配置信息，如数据库文件路径和许可证版本号。
        *   `database.py`: 负责数据库连接、Session管理和表初始化。
        *   `models.py`: 定义所有SQLAlchemy ORM模型（Channel, Device, License）。
        *   `logic.py`: 实现所有核心业务逻辑的函数。
        *   `exceptions.py`: 定义自定义的业务逻辑异常。
        *   `main.py`: (可选) 一个用于演示和测试模块功能的主入口文件。

2.  **环境设置**:
    *   创建并激活Python虚拟环境。
    *   安装必要的库: `pip install sqlalchemy`。

3.  **配置文件 (`config.py`)**:
    *   定义 `DATABASE_FILE_PATH = "license_server.db"`。
    *   定义 `CURRENT_LICENSE_VERSION = "1.0.1"`。

---

### **第二步：数据库模型定义 (ORM)**

此步骤将我们讨论的数据库结构转化为SQLAlchemy代码。

**文件**: `models.py`

1.  **创建基类**: 定义一个所有模型都将继承的 `DeclarativeBase`。

2.  **定义 `Channel` 模型**:
    *   **表名**: `channels`
    *   **字段**:
        *   `id` (Integer, 主键)
        *   `name` (String, 唯一, 非空, 索引)
        *   `max_devices` (Integer, 非空, 默认值如 1000)
        *   `license_duration_days` (Integer, 非空, 默认值 30)
        *   `description` (Text, 可空)
        *   `created_at` (DateTime, 默认当前时间)
    *   **关系**: 定义一个到 `Device` 模型的一对多关系 (`relationship`)。

3.  **定义 `Device` 模型**:
    *   **表名**: `devices`
    *   **字段**:
        *   `id` (Integer, 主键)
        *   `device_id_str` (String, 唯一, 非空, 索引)
        *   `channel_id` (Integer, 外键关联到 `channels.id`, 非空)
        *   `created_at` (DateTime, 默认当前时间)
    *   **外键约束**: 在定义 `ForeignKey` 时，明确设置 `ondelete="RESTRICT"`，以防止关联着设备的渠道被意外删除。
    *   **关系**: 定义到 `Channel` 的多对一关系和到 `License` 的一对多关系。

4.  **定义 `License` 模型**:
    *   **表名**: `licenses`
    *   **字段**:
        *   `id` (Integer, 主键)
        *   `license_key` (Text, 非空)
        *   `version` (String, 非空)
        *   `request_ip` (String)
        *   `status` (String, 非空, 默认 'active', 索引)
        *   `created_at` (DateTime, 默认当前时间)
        *   `expires_at` (DateTime, 非空)
        *   `device_id` (Integer, 外键关联到 `devices.id`, 非空)
    *   **关系**: 定义到 `Device` 的多对一关系。

---

### **第三步：数据库会话管理**

此步骤负责建立与SQLite数据库的连接，并提供可靠的会话管理机制。

**文件**: `database.py`

1.  **创建数据库引擎**:
    *   使用 `create_engine` 函数，并从 `config.py` 中读取SQLite文件的路径。
    *   伪代码: `engine = create_engine("sqlite:///" + DATABASE_FILE_PATH)`

2.  **创建Session工厂**:
    *   使用 `sessionmaker` 创建一个 `SessionLocal` 类，绑定到 `engine`。

3.  **提供会话上下文管理器**:
    *   定义一个名为 `get_db_session` 的函数，它是一个上下文管理器 (`@contextmanager`)。
    *   这个函数将 `yield` 一个新的数据库会话实例，并在 `finally` 块中确保会话被 `close()`，以释放连接资源。这是保证数据库连接被正确管理的关键。

4.  **创建表函数**:
    *   定义一个名为 `init_db` 的函数。
    *   该函数导入 `Base` 和所有模型，然后调用 `Base.metadata.create_all(bind=engine)`。
    *   这个函数只在首次部署或需要重建数据库时手动运行一次。

---

### **第四步：核心业务逻辑实现**

此步骤是整个系统的核心，将所有规则和流程代码化。

**文件**: `logic.py`

1.  **定义自定义异常 (`exceptions.py`)**:
    *   `ChannelNotFound(Exception)`: 当请求的渠道不存在时抛出。
    *   `DeviceLimitExceeded(Exception)`: 当渠道设备数达到上限时抛出。

2.  **实现主业务函数 `process_license_request`**:
    *   **函数签名**: `def process_license_request(db: Session, device_id_str: str, channel_name: str, request_ip: str) -> License:`
    *   **逻辑流程 (伪代码)**:
        ```
        # 1. 查询设备
        device = find_device_by_id(db, device_id_str)

        # 2. 如果设备已存在
        if device is not None:
            # 2.1 查找最新的有效许可证
            latest_license = find_latest_active_license_for_device(db, device)
            if latest_license is not None:
                # 2.2 如果找到，直接返回
                return latest_license
            
            # 2.3 如果没有有效许可证，则获取其渠道信息，准备创建新许可证
            channel = device.channel

        # 3. 如果设备不存在
        else:
            # 3.1 查找渠道
            channel = find_channel_by_name(db, channel_name)
            if channel is None:
                raise ChannelNotFound("渠道不存在")

            # 3.2 检查渠道设备配额
            current_device_count = count_devices_in_channel(db, channel.id)
            if current_device_count >= channel.max_devices:
                raise DeviceLimitExceeded("渠道设备已达上限")

            # 3.3 创建新设备实例并添加到会话
            device = create_new_device(device_id_str, channel.id)
            db.add(device)

        # 4. 创建新许可证 (无论是新设备还是旧设备无有效许可)
        expires_at = calculate_expiry_date(channel.license_duration_days)
        
        # 伪代码调用已实现的加密函数
        license_key_str = generate_license_key(
            device_id=device_id_str, 
            expires_at=expires_at
        )

        new_license = create_new_license(
            device=device,
            key=license_key_str,
            version=CURRENT_LICENSE_VERSION,
            ip=request_ip,
            expires_at=expires_at
        )
        db.add(new_license)

        # 5. 提交事务并返回结果
        db.commit()
        db.refresh(new_license) # 刷新以获取ID等数据库生成的值
        return new_license
        ```

---

### **第五步：集成与测试**

此步骤将所有部分组合起来，并确保其按预期工作。

1.  **初始化数据库**:
    *   在项目根目录运行一个简单的脚本，调用 `database.init_db()` 来创建 `license_server.db` 文件和其中的所有表。

2.  **编写集成入口 (`main.py`)**:
    *   这个文件将模拟HTTP服务的调用。
    *   它会使用 `database.get_db_session` 上下文管理器来获取数据库会话。
    *   在 `with` 块内，它将调用 `logic.process_license_request` 并传入模拟的参数（设备ID，渠道名，IP地址）。
    *   它会捕获 `ChannelNotFound` 和 `DeviceLimitExceeded` 异常并打印相应的错误信息。
    *   如果成功，它会打印出返回的许可证对象的关键信息。

3.  **测试场景**:
    *   **场景1: 新设备首次请求**: 验证设备和许可证是否都已创建。
    *   **场景2: 已有设备再次请求 (许可证未过期)**: 验证是否返回了上一次的许可证，并且数据库中没有新增记录。
    *   **场景3: 已有设备再次请求 (许可证已过期)**: 验证是否创建了一个新的许可证记录。
    *   **场景4: 渠道设备满额**: 验证是否正确抛出 `DeviceLimitExceeded` 异常。
    *   **场景5: 请求不存在的渠道**: 验证是否正确抛出 `ChannelNotFound` 异常。
