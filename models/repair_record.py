from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Float  # 移除Enum导入
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum
from datetime import datetime
from utils.db import Base
from models.user import User

# 枚举类保持原定义（小写成员值），无需修改
class RepairStatus(str, enum.Enum):
    """维修状态枚举"""
    PENDING = "pending"      # 待处理
    PROCESSING = "processing" # 处理中
    COMPLETED = "completed"  # 已完成
    CANCELLED = "cancelled"  # 已取消

class RepairPriority(str, enum.Enum):
    """维修优先级枚举（小写成员值，适配数据库）"""
    LOW = "低"      # 低
    MEDIUM = "中" # 中
    HIGH = "高"    # 高
    URGENT = "紧急" # 紧急

class RepairRecord(Base):
    """维修记录表模型（修改枚举字段为String）"""
    __tablename__ = "repair_records"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    dormitory = Column(String(20), nullable=False, index=True, comment="宿舍号")
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, comment="报修人ID")
    title = Column(String(100), nullable=False, comment="报修标题")
    description = Column(Text, nullable=False, comment="详细描述")
    category = Column(String(50), nullable=False, comment="报修类别（水电/家具/电器等）")
    
    # 关键修改：枚举字段改为String，存小写字符串
    priority = Column(String(20), default="medium", comment="优先级（low/medium/high/urgent）")
    status = Column(String(20), default="pending", comment="状态（pending/processing/completed/cancelled）")
    
    location = Column(String(100), nullable=True, comment="具体位置")
    contact_phone = Column(String(20), nullable=True, comment="联系电话")
    images = Column(Text, nullable=True, comment="图片列表（JSON字符串）")
    
    # 维修信息（不变）
    assigned_to = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, comment="指派给（维修人员ID）")
    repair_notes = Column(Text, nullable=True, comment="维修说明")
    repair_result = Column(Text, nullable=True, comment="维修结果")
    cost = Column(Float, nullable=True, comment="维修费用")
    
    # 时间信息（不变）
    expected_time = Column(DateTime, nullable=True, comment="预计维修时间")
    repair_time = Column(DateTime, nullable=True, comment="实际维修时间")
    completed_time = Column(DateTime, nullable=True, comment="完成时间")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
    
    # 关联用户（不变）
    reporter = relationship("User", foreign_keys=[user_id], backref="reported_repairs")
    repairer = relationship("User", foreign_keys=[assigned_to], backref="assigned_repairs")

    def __repr__(self):
        return f"<RepairRecord(dormitory={self.dormitory}, title={self.title}, status={self.status})>"
