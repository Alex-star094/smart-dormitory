"""
用户CRUD模块 - 提供用户相关的数据库操作
包括创建用户、密码哈希、人脸编码管理等功能
"""
import re
from typing import List, Optional

from sqlalchemy.orm import Session
from passlib.context import CryptContext

from crud.base import BaseCRUD
from models.user import User

# 密码哈希上下文（使用bcrypt算法）
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """对明文密码进行bcrypt哈希"""
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证明文密码与哈希值是否匹配"""
    return pwd_context.verify(plain_password, hashed_password)


class UserCRUD(BaseCRUD[User, None, None]):
    """用户CRUD类"""

    def __init__(self, model: type[User]):
        super().__init__(model)

    def count_multi(self, db: Session) -> int:
        """统计用户总数"""
        return db.query(self.model).count()

    def get_by_student_id(self, db: Session, student_id: str) -> Optional[User]:
        """根据学号查询用户"""
        if not student_id or len(student_id) > 20:
            return None
        return db.query(User).filter(User.student_id == student_id).first()

    def get_by_openid(self, db: Session, openid: str) -> Optional[User]:
        """根据微信openid查询用户"""
        if not openid or len(openid) > 100:
            return None
        return db.query(User).filter(User.openid == openid).first()

    def get_by_phone(self, db: Session, phone: str) -> Optional[User]:
        """根据手机号查询用户"""
        if phone and not re.match(r'^1[3-9]\d{9}$', phone):
            return None
        return db.query(User).filter(User.phone == phone).first()

    def get_by_role(
        self, db: Session, role: str, skip: int = 0, limit: int = 100
    ) -> List[User]:
        """根据角色查询用户（分页）"""
        valid_roles = ["student", "admin"]
        if role not in valid_roles:
            raise ValueError(f"角色值无效，仅支持{valid_roles}")
        if skip < 0:
            skip = 0
        if limit < 1 or limit > 100:
            limit = 20
        return (
            db.query(User)
            .filter(User.role == role)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def count_by_role(self, db: Session, role: str) -> int:
        """统计指定角色的用户总数"""
        valid_roles = ["student", "admin"]
        if role not in valid_roles:
            raise ValueError(f"角色值无效，仅支持{valid_roles}")
        return db.query(User).filter(User.role == role).count()

    def create_user(
        self,
        db: Session,
        *,
        student_id: str,
        username: str,
        password: str,
        role: str = "student",
    ) -> User:
        """创建用户（密码自动bcrypt哈希）"""
        # 1. 基础参数校验
        valid_roles = ["student", "admin"]
        if role not in valid_roles:
            raise ValueError(f"角色值无效，仅支持{valid_roles}")
        if not student_id or len(student_id) > 20:
            raise ValueError("学号不能为空且长度不能超过20字符")
        if not username or len(username) > 50:
            raise ValueError("姓名不能为空且长度不能超过50字符")
        if not password or len(password) < 6:
            raise ValueError("密码不能为空且长度不能少于6字符")

        # 2. 学号唯一性校验
        existing_user = self.get_by_student_id(db, student_id=student_id)
        if existing_user:
            raise ValueError(f"学号{student_id}已存在")

        # 3. 密码哈希存储（核心安全改进）
        hashed_password = hash_password(password)

        # 4. 创建数据库记录
        db_user = User(
            student_id=student_id,
            username=username,
            password=hashed_password,
            role=role,
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user

    def update_face_encoding(
        self, db: Session, *, user_id: int, face_encoding: str
    ) -> Optional[User]:
        """更新用户人脸编码"""
        if not face_encoding:
            raise ValueError("人脸编码不能为空")
        user = self.get(db, id=user_id)
        if not user:
            raise ValueError(f"用户ID{user_id}不存在")

        user.face_encoding = face_encoding
        db.commit()
        db.refresh(user)
        return user

    def update_user_info(
        self,
        db: Session,
        *,
        user_id: int,
        dormitory: Optional[str] = None,
        phone: Optional[str] = None,
    ) -> Optional[User]:
        """更新用户宿舍和手机号"""
        user = self.get(db, id=user_id)
        if not user:
            return None

        # 宿舍号校验
        if dormitory is not None:
            if len(dormitory) > 20 or not dormitory.strip():
                raise ValueError("宿舍号长度不能超过20字符且不能为空")
            user.dormitory = dormitory.strip()

        # 手机号校验
        if phone is not None:
            if not re.match(r'^1[3-9]\d{9}$', phone):
                raise ValueError("手机号格式不正确（需为11位有效号码）")
            user.phone = phone

        db.commit()
        db.refresh(user)
        return user

    def change_password(
        self,
        db: Session,
        *,
        user_id: int,
        old_password: str,
        new_password: str,
    ) -> bool:
        """修改密码（需验证旧密码）"""
        user = self.get(db, id=user_id)
        if not user:
            raise ValueError("用户不存在")

        if not verify_password(old_password, user.password):
            raise ValueError("原密码错误")

        if len(new_password) < 6:
            raise ValueError("新密码长度不能少于6字符")

        user.password = hash_password(new_password)
        db.commit()
        return True


# 全局实例
user_crud = UserCRUD(User)
