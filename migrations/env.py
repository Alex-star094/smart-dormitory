"""
Alembic 迁移环境配置 — 支持自动检测模型变更生成迁移脚本

用法:
  alembic revision --autogenerate -m "描述"   # 自动生成迁移
  alembic upgrade head                          # 升级到最新
  alembic downgrade -1                          # 回退一步
"""
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# 导入所有模型（确保 Alembic 能检测到）
from utils.db import Base
from models import (  # noqa: F401 - 导入确保所有模型注册到 Base.metadata
    User,
    AccessRecord,
    Visitor,
    EnergyConsumption,
    RepairRecord,
    BlacklistRecord,
)
from config import settings

# Alembic Config 对象
config = context.config

# 从配置文件读取数据库 URL，支持通过环境变量覆盖
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# 设置日志
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 模型元数据
target_metadata = Base.metadata


def run_migrations_offline():
    """离线模式 — 生成 SQL 脚本而不连接数据库（适合审查）"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """在线模式 — 直接连接数据库执行迁移"""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
