"""数据库连接与会话管理。"""
from contextlib import contextmanager
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import sessionmaker
from .config import DATABASE_FILE_PATH

# SQLite 文件数据库
engine: Engine = None

SessionLocal = None

@contextmanager
def get_db_session():
    if SessionLocal is None:
        raise Exception("Database not initialized")
    """会话上下文管理器：yield 一个 Session 并在退出时关闭。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db(database_file_path: str = DATABASE_FILE_PATH):
    """创建所有模型对应的表（若不存在）。"""
    global engine
    global SessionLocal
    if engine is not None:
        return
    engine = create_engine(f"sqlite:///{database_file_path}", echo=False, future=True)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    # 延迟导入 models，避免循环导入问题
    from .models import Base
    Base.metadata.create_all(bind=engine)
