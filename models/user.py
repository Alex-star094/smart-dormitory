from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text  # 移除Enum导入
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from utils.db import Base

# 1. 删除原有的UserRole枚举类（不再依赖枚举）

class User(Base):
    """用户表模型（role字段改为字符串类型）"""
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    student_id = Column(String(20), unique=True, index=True, nullable=False, comment="学号（唯一标识）")
    username = Column(String(50), nullable=False, comment="姓名")
    password = Column(String(100), nullable=False, comment="密码")
    phone = Column(String(20), nullable=True, comment="手机号")
    dormitory = Column(String(20), nullable=True, comment="宿舍号（如3-201）")
    role = Column(String(20), nullable=False, default="student", comment="角色（student：学生，admin：管理员）")
    face_encoding = Column(Text, nullable=True, comment="人脸特征编码（Base64存储）")
    openid = Column(String(100), unique=True, nullable=True, comment="微信小程序openid")
    is_active = Column(Boolean, default=True, comment="账号是否激活")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    def __repr__(self):
        return f"<User(student_id={self.student_id}, username={self.username}, role={self.role})>"