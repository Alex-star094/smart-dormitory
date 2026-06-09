"""通行记录CRUD模块"""
from datetime import datetime
from typing import List

from sqlalchemy.orm import Session

from crud.base import BaseCRUD
from models.access import AccessRecord

VALID_STATUSES = ["allowed", "denied", "error"]
VALID_ACCESS_TYPES = ["face"]

class AccessCRUD(BaseCRUD[AccessRecord, None, None]):
    """通行记录CRUD类"""
    def __init__(self, model: AccessRecord):
        super().__init__(model)

    def create(
        self, db: Session, *, obj_in: dict
    ) -> AccessRecord:
        """创建通行记录（重写父类方法，支持字典参数）"""
        # 1. 状态参数处理：默认error，转为小写并校验
        status = obj_in.get("status", "error").lower()
        if status not in VALID_STATUSES:
            raise ValueError(f"无效的status！可选值：{VALID_STATUSES}")
        
        # 2. 通行类型处理：默认face，转为小写并校验
        access_type = obj_in.get("access_type", "face").lower()
        if access_type not in VALID_ACCESS_TYPES:
            raise ValueError(f"无效的access_type！可选值：{VALID_ACCESS_TYPES}")

        db_obj = AccessRecord(
            user_id=obj_in.get("user_id"),
            username=obj_in.get("username"),
            dormitory=obj_in.get("dormitory"),
            status=status,
            access_type=access_type,
            access_time=obj_in.get("access_time", datetime.now()),
            alarm=obj_in.get("alarm", False),
            notes=obj_in.get("notes")
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get_by_user_id(
        self, db: Session, user_id: int, skip: int = 0, limit: int = 100
    ) -> List[AccessRecord]:
        """根据用户ID查询通行记录"""
        return db.query(AccessRecord).filter(AccessRecord.user_id == user_id).offset(skip).limit(limit).all()

    def get_by_dormitory(
        self, db: Session, dormitory: str, skip: int = 0, limit: int = 100
    ) -> List[AccessRecord]:
        """根据宿舍号查询通行记录"""
        return db.query(AccessRecord).filter(AccessRecord.dormitory == dormitory).offset(skip).limit(limit).all()

# 实例化通行记录CRUD
access_crud = AccessCRUD(AccessRecord)