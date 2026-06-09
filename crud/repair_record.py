"""维修记录CRUD模块"""
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from crud.base import BaseCRUD
from models.repair_record import RepairRecord, RepairStatus

class RepairRecordCRUD(BaseCRUD[RepairRecord, None, None]):
    """维修记录CRUD类"""
    def __init__(self, model: RepairRecord):
        super().__init__(model)

    def create(self, db: Session, *, obj_in: dict) -> RepairRecord:
        """创建维修记录"""
        priority = obj_in.get("priority", "中")
        valid_priorities = ["低", "中", "高", "紧急"]
        status = obj_in.get("status", "pending").lower()
        valid_statuses = ["pending", "processing", "completed", "cancelled"]
        if status not in valid_statuses:
            raise ValueError(f"无效的状态，可选值：{valid_statuses}")
        db_obj = RepairRecord(
            dormitory=obj_in.get("dormitory"),
            user_id=obj_in.get("user_id"),
            title=obj_in.get("title"),
            description=obj_in.get("description"),
            category=obj_in.get("category"),
            priority=priority,  
            status=status,     
            location=obj_in.get("location"),
            contact_phone=obj_in.get("contact_phone"),
            images=obj_in.get("images")
        )
        db.add(db_obj)
        db.commit()
        # db.refresh(db_obj)
        return db_obj

    def get_by_dormitory(
        self, db: Session, dormitory: str, 
        status: Optional[RepairStatus] = None,
        skip: int = 0, limit: int = 100
    ) -> List[RepairRecord]:
        """根据宿舍号查询维修记录"""
        query = db.query(RepairRecord).filter(RepairRecord.dormitory == dormitory)
        if status:
            query = query.filter(RepairRecord.status == status.lower())
        return query.order_by(RepairRecord.created_at.desc()).offset(skip).limit(limit).all()

    def get_by_user_id(
        self, db: Session, user_id: int,
        status: Optional[RepairStatus] = None,
        skip: int = 0, limit: int = 100
    ) -> List[RepairRecord]:
        """根据用户ID查询维修记录"""
        query = db.query(RepairRecord).filter(RepairRecord.user_id == user_id)
        if status:
            query = query.filter(RepairRecord.status == status)
        return query.order_by(RepairRecord.created_at.desc()).offset(skip).limit(limit).all()

    def get_by_status(
        self, db: Session, status: str,
        skip: int = 0, limit: int = 100
    ) -> List[RepairRecord]:
        """根据状态查询维修记录"""
        return db.query(RepairRecord)\
            .filter(RepairRecord.status == status)\
            .order_by(RepairRecord.created_at.desc())\
            .offset(skip).limit(limit).all()

    def assign_repairer(
        self, db: Session, *, repair_id: int, repairer_id: int, 
        expected_time: Optional[str] = None
    ) -> Optional[RepairRecord]:
        """指派维修人员"""
        repair = self.get(db, id=repair_id)
        if not repair:
            return None
        
        repair.assigned_to = repairer_id
        repair.status = "processing"
        if expected_time:
            repair.expected_time = expected_time
        
        db.commit()
        # db.refresh(repair)
        return repair

    def update_repair_result(
        self, db: Session, *, repair_id: int,
        repair_notes: Optional[str] = None,
        repair_result: Optional[str] = None,
        cost: Optional[float] = None,
        completed: bool = False
    ) -> Optional[RepairRecord]:
        """更新维修结果"""
        repair = self.get(db, id=repair_id)
        if not repair:
            return None
        
        if repair_notes:
            repair.repair_notes = repair_notes
        if repair_result:
            repair.repair_result = repair_result
        if cost is not None:
            repair.cost = cost
        
        if completed:
            repair.status = "completed"
            repair.completed_time = datetime.now()
        
        db.commit()
        # db.refresh(repair)
        return repair

    def update_status(
        self, db: Session, *, repair_id: int, status: RepairStatus
    ) -> Optional[RepairRecord]:
        """更新维修状态"""
        repair = self.get(db, id=repair_id)
        if not repair:
            return None
        
        valid_statuses = ["pending", "processing", "completed", "cancelled"]
        status_lower = status.lower()
        if status_lower not in valid_statuses:
            raise ValueError(f"无效的状态，可选值：{valid_statuses}")
        
        repair.status = status_lower
        if status_lower == "completed":
            repair.completed_time = datetime.now()
        
        db.commit()
        # db.refresh(repair)
        return repair

# 实例化维修记录CRUD
repair_crud = RepairRecordCRUD(RepairRecord)
