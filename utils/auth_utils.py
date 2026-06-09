from datetime import datetime, timezone, timedelta
from jose import jwt
from config import settings


def create_access_token(subject: str, token_type: str = "password") -> str:
    """
    生成JWT访问Token
    :param subject: 用户唯一标识（此处用user_id）
    :param token_type: 登录方式（password/face）
    :return: 加密后的JWT字符串
    """
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode = {
        "sub": subject,
        "type": token_type,
        "exp": expire,
    }
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    return encoded_jwt
