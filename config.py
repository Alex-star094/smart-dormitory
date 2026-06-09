from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """应用配置类，自动从 .env 文件加载环境变量"""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ======================== 数据库配置 ========================
    DATABASE_TYPE: str = Field(
        default="sqlite", description="数据库类型：sqlite（本地开发）或 mysql（生产）"
    )
    DB_HOST: str = Field(default="localhost", description="数据库主机地址（仅MySQL）")
    DB_PORT: int = Field(default=3306, description="数据库端口（仅MySQL）")
    DB_USER: str = Field(default="root", description="数据库用户名（仅MySQL）")
    DB_PASS: str = Field(default="", description="数据库密码（仅MySQL）")
    DB_NAME: str = Field(default="smart_dorm", description="数据库名称")

    # 数据库连接池配置
    DB_POOL_SIZE: int = Field(default=20, description="常驻连接数")
    DB_MAX_OVERFLOW: int = Field(default=10, description="最大溢出连接数")
    DB_POOL_RECYCLE: int = Field(default=300, description="连接回收时间（秒）")
    DB_POOL_PRE_PING: bool = Field(default=True, description="连接有效性检测")

    # ======================== Redis配置 ========================
    REDIS_HOST: str = Field(default="localhost", description="Redis主机地址")
    REDIS_PORT: int = Field(default=6379, description="Redis端口")
    REDIS_DB: int = Field(default=0, description="Redis数据库编号")
    REDIS_PASSWORD: str = Field(default="", description="Redis密码")

    # ======================== JWT配置 ========================
    SECRET_KEY: str = Field(
        default="change-me-in-production-use-secrets-token-urlsafe",
        description="JWT签名密钥（生产环境必须修改！）"
    )
    ALGORITHM: str = Field(default="HS256", description="JWT签名算法")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=120, description="JWT Token过期时间（分钟）"
    )

    # ======================== 微信小程序配置 ========================
    WX_APPID: str = Field(default="", description="微信小程序AppID")
    WX_SECRET: str = Field(default="", description="微信小程序Secret")

    # ======================== 业务配置 ========================
    ELECTRICITY_ALARM_THRESHOLD: float = Field(
        default=50.0, description="电力消耗告警阈值（度）"
    )
    WATER_ALARM_THRESHOLD: float = Field(
        default=10.0, description="用水告警阈值（吨）"
    )
    FACE_MATCH_THRESHOLD: float = Field(
        default=0.6, description="人脸匹配阈值（值越小越严格）"
    )
    ELECTRICITY_PRICE: float = Field(
        default=0.667, description="电费单价（元/度）"
    )
    WATER_PRICE: float = Field(
        default=4.05, description="水费单价（元/吨）"
    )

    # 文件上传限制
    MAX_UPLOAD_SIZE_MB: int = Field(
        default=5, description="最大上传文件大小（MB）"
    )
    # 安全配置
    RATE_LIMIT_REQUESTS: int = Field(
        default=100, description="每分钟最大请求数"
    )

    @property
    def DATABASE_URL(self) -> str:
        """构建数据库连接URL（支持 SQLite 和 MySQL）"""
        if self.DATABASE_TYPE == "sqlite":
            return f"sqlite:///./{self.DB_NAME}.db"
        else:
            return (
                f"mysql+mysqlconnector://{self.DB_USER}:{self.DB_PASS}"
                f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
                f"?charset=utf8mb4"
            )


# 全局配置实例
settings = Settings()
