"""数据库连接与会话管理。"""
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .config import DATABASE_FILE_PATH


# SQLite 文件数据库
engine = create_engine(f"sqlite:///{DATABASE_FILE_PATH}", echo=False, future=True)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


@contextmanager
def get_db_session():
    """会话上下文管理器：yield 一个 Session 并在退出时关闭。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """创建所有模型对应的表（若不存在）。"""
    # 延迟导入 models，避免循环导入问题
    from .models import Base

    Base.metadata.create_all(bind=engine)
