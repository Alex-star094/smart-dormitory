from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index  # 新增Index导入
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum
from datetime import datetime
from utils.db import Base
from models.user import User

class VisitorStatus(str, enum.Enum):
    """访客状态枚举（不变）"""
    PENDING = "pending"    # 待审核
    APPROVED = "approved"  # 已批准
    REJECTED = "rejected"  # 已拒绝
    

class Visitor(Base):
    """访客表模型（修改id_card字段约束）"""
    __tablename__ = "visitors"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, comment="预约人ID（学生）")
    visitor_name = Column(String(50), nullable=False, comment="访客姓名")
    
    # 关键修改1：id_card长度限制为18位（兼容15/18位身份证）
    id_card = Column(String(18), nullable=False, comment="访客身份证号（15位纯数字或18位数字+X/x）")
    
    visit_date = Column(DateTime, nullable=False, comment="预约访问时间")
    visit_reason = Column(String(200), nullable=False, comment="访问原因")
    status = Column(String(20), default=VisitorStatus.PENDING.value, comment="状态")
    approver_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, comment="审核人ID（管理员）")
    approve_note = Column(String(200), nullable=True, comment="审核备注")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    # 关联预约人和审核人（不变）
    booker = relationship("User", foreign_keys=[user_id], backref="booked_visitors")
    approver = relationship("User", foreign_keys=[approver_id], backref="approved_visitors")

    # 关键修改2：添加id_card索引（加快黑名单查询、重复校验速度）
    __table_args__ = (
        Index("idx_visitor_id_card", "id_card"),  # 普通索引（优化查询）
        # 若需禁止同一身份证重复预约，可添加唯一索引（根据业务需求选择）
        # UniqueConstraint("id_card", "visit_date", name="uq_visitor_id_card_date"),
    )

    def __repr__(self):
        return f"<Visitor(name={self.visitor_name}, id_card={self.id_card}, status={self.status})>"