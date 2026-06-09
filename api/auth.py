from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from jose import JWTError, jwt

from config import settings
from crud.user import user_crud, verify_password
from utils.db import get_db
from utils.auth_utils import create_access_token
from models.user import User

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")  # 密码登录地址


def get_current_user(
    db: Session = Depends(get_db), 
    token: str = Depends(oauth2_scheme)
) -> User:
    """获取当前登录用户（依赖注入，两种登录方式通用）"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的认证令牌",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # 解码Token
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        user_id: str = payload.get("sub")  # 从Token中获取user_id
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    # 修复1：查询用户时强制刷新最新信息（确保包含最新绑定的宿舍号）
    user = user_crud.get(db, id=int(user_id))
    if user is None or not user.is_active:
        raise credentials_exception
    
    # 修复2：未绑定宿舍时返回明确提示（便于前端判断）
    if not user.dormitory:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请先在个人中心绑定宿舍"
        )
    
    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """管理员权限校验（依赖注入）"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权限访问，需要管理员权限"
        )
    return current_user


@router.post("/token", summary="学号密码登录（获取Token）")
def login_for_access_token(
    db: Session = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
):
    """
    学号密码登录接口：
    - 前端用表单格式提交（username=学号，password=密码）
    - 返回与人脸登录一致格式的Token
    """
    # 1. 按学号查询用户
    user = user_crud.get_by_student_id(db, student_id=form_data.username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="学号或密码错误"
        )
    
    # 2. 验证密码（依赖crud.user中的verify_password方法）
    if not verify_password(form_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="学号或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 3. 调用公共工具生成Token（标记为密码登录）
    access_token = create_access_token(
        subject=str(user.id),  # 传user_id（与get_current_user逻辑一致）
        token_type="password"
    )
    
    # 4. 返回Token及用户基础信息（无敏感数据）
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "student_id": user.student_id,
            "username": user.username,
            "role": user.role,
            "dormitory": user.dormitory or ""
        }
    }


@router.get("/test-db", summary="测试数据库连接（调试用）")
def test_database_connection(db: Session = Depends(get_db)):
    """测试数据库连接和用户查询，无需认证"""
    try:
        users = db.query(User).limit(5).all()
        user_info = []
        for user in users:
            user_info.append({
                "student_id": user.student_id,
                "username": user.username,
                "role": user.role,
                "is_active": user.is_active,
                "password_length": len(user.password) if user.password else 0
            })
        return {
            "status": "success",
            "message": f"数据库连接成功，查询到{len(users)}个用户",
            "sample_users": user_info
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"数据库连接失败: {str(e)}"
        }