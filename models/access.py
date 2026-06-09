from sqlalchemy import Column, Integer, String, Enum, Boolean, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum
from datetime import datetime
from utils.db import Base
from models.user import User

class AccessStatus(str, enum.Enum):
    """通行状态枚举"""
    ALLOWED = "allowed"  # 允许通行
    DENIED = "denied"    # 拒绝通行
    ERROR = "error"      # 系统错误

class AccessType(str, enum.Enum):
    """通行方式枚举"""
    FACE = "face"        # 人脸识别

class AccessRecord(Base):
    """通行记录表模型"""
    __tablename__ = "access_records"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, comment="关联用户ID")
    username = Column(String(50), nullable=False, comment="通行人姓名")
    dormitory = Column(String(20), nullable=False, comment="目标宿舍")
    status = Column(String(10), nullable=False, default="error", comment="通行状态")
    access_type = Column(String(10), nullable=False, default="face", comment="通行方式")
    access_time = Column(DateTime, default=datetime.now, comment="通行时间")
    alarm = Column(Boolean, default=False, comment="是否触发告警")
    notes = Column(String(200), nullable=True, comment="备注（如未授权原因）")

    # 关联用户（可选）
    user = relationship("User", backref="access_records")

    def __repr__(self):
        return f"<AccessRecord(username={self.username}, status={self.status}, time={self.access_time})>"