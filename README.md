# 🏫 智安校园 — 宿舍智能管理系统（后端服务）

基于 **FastAPI + SQLAlchemy + MySQL + Redis** 的宿舍智能管理后端，支持：
- 🔐 学号密码 + 人脸识别双模式认证
- 🚶 宿舍通行管理（人脸识别通行）
- 👥 访客预约与审核
- ⚡ 能耗（水/电）管理与告警
- 🔧 报修管理系统
- 🚫 黑名单管理
- 📱 微信小程序前后端分离架构

## 🛠 技术栈

| 类别     | 技术                                      |
| -------- | ----------------------------------------- |
| Web框架  | FastAPI 0.110                             |
| ORM      | SQLAlchemy 2.0                            |
| 数据库   | MySQL 8.0                                |
| 缓存     | Redis 5.0                                |
| 认证     | JWT (python-jose) + bcrypt 密码哈希       |
| 人脸识别 | InsightFace (buffalo_l) + OpenCV          |
| 运行环境 | Python 3.10+                              |

## 📂 项目结构

```
smart_dorm_backend/
├── api/                    # API 路由层
│   ├── auth.py             # 认证（登录/Token）
│   ├── user.py             # 用户管理
│   ├── access.py           # 通行管理
│   ├── visitor.py          # 访客管理
│   ├── energy_consumption.py # 能耗管理
│   ├── repair_record.py    # 报修管理
│   ├── blacklist.py        # 黑名单管理
│   └── face.py             # 人脸管理
├── crud/                   # 数据库操作层
│   ├── base.py             # 基础CRUD类
│   ├── user.py             # 用户CRUD
│   ├── access.py           # 通行记录CRUD
│   ├── ...                 # 其他CRUD
├── models/                 # SQLAlchemy 模型
│   ├── user.py
│   ├── access.py
│   └── ...
├── utils/                  # 工具模块
│   ├── auth_utils.py       # JWT Token 工具
│   ├── db.py               # 数据库连接
│   ├── exception.py        # 全局异常处理
│   ├── face_utils.py       # 人脸识别工具
│   ├── id_card_utils.py    # 身份证校验
│   ├── logger.py           # 日志配置
│   ├── redis_utils.py      # Redis 工具
│   └── security_monitor.py # 安全监控
├── wxapp/                  # 微信小程序前端
├── config.py               # 应用配置
├── main.py                 # 应用入口
├── requirements.txt        # Python 依赖
├── .env.example            # 环境变量模板
└── .gitignore
```

## 🚀 快速开始

### 前置条件

- Python 3.10+
- MySQL 8.0+
- Redis 6.0+
- （可选）InsightFace + ONNX Runtime（人脸识别功能需要）

### 1. 克隆项目

```bash
git clone <your-repo-url>
cd smart_dorm_backend
```

### 2. 创建虚拟环境

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

> **注意**：InsightFace 在某些环境下安装可能较复杂。如果不需要人脸识别功能，可暂时注释掉 `insightface` 和 `onnxruntime`，系统会自动降级为模拟模式。

### 4. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件，填写你的数据库密码、JWT密钥等配置：

```env
DB_PASS=your-real-password
SECRET_KEY=your-strong-random-secret-key
WX_APPID=your-wx-appid
WX_SECRET=your-wx-secret
```

### 5. 创建数据库

```sql
CREATE DATABASE smart_dorm CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 6. 启动服务

```bash
python main.py
```

服务将在 `http://localhost:8000` 启动。

### 7. 访问 API 文档

- Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)

## 📡 API 概览

| 模块     | 前缀          | 说明               |
| -------- | ------------- | ------------------ |
| 认证     | `/api/v1/auth`    | 登录、Token 获取   |
| 用户管理 | `/api/v1/users`   | 个人信息、用户列表 |
| 通行管理 | `/api/v1/access`  | 人脸通行、通行记录 |
| 访客管理 | `/api/v1/visitors` | 访客预约与审核     |
| 能耗管理 | `/api/v1/energy`  | 水电记录、告警     |
| 维修管理 | `/api/v1/repair`  | 报修申请与处理     |
| 黑名单   | `/api/v1/blacklist` | 黑名单管理        |
| 人脸管理 | `/api/v1/face`    | 人脸录入与绑定     |

## 🔐 安全特性

- **密码哈希**：使用 bcrypt 算法存储密码，非明文
- **JWT 认证**：支持密码登录和人脸登录两种方式获取 Token
- **权限控制**：学生/管理员角色分离，API 级别权限校验
- **身份证校验**：符合 GB 11643-1999 标准的身份证号校验
- **黑名单机制**：自动检测异常行为并加入黑名单
- **敏感信息保护**：`.env` 文件不纳入版本控制

## ⚙️ 配置说明

所有配置项通过 `.env` 文件管理，详见 `.env.example`：

| 配置项                        | 说明             | 默认值    |
| ----------------------------- | ---------------- | --------- |
| `DB_HOST`                     | 数据库主机       | localhost |
| `DB_POOL_SIZE`                | 连接池大小       | 20        |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | Token过期时间 | 120       |
| `FACE_MATCH_THRESHOLD`        | 人脸匹配阈值     | 0.6       |
| `ELECTRICITY_ALARM_THRESHOLD` | 用电告警阈值(度) | 50.0      |
| `WATER_ALARM_THRESHOLD`       | 用水告警阈值(吨) | 10.0      |

## 🔧 开发说明

### 数据库迁移

当前使用 `Base.metadata.create_all()` 自动建表。生产环境建议使用 [Alembic](https://alembic.sqlalchemy.org/) 管理数据库迁移。

### 日志

日志默认输出到控制台，使用 Python 标准 `logging` 模块。在 `utils/logger.py` 中配置。

### 人脸识别

- 默认使用 InsightFace 的 `buffalo_l` 模型
- 模型加载失败时自动降级为模拟模式（无真实人脸比对）
- 人脸特征以 Base64 编码存储在数据库中

## 📄 License

本项目仅供学习交流使用。

---

**⚠️ 重要提醒**：上传到 GitHub 前，请确保：
1. `.env` 文件不包含真实密码（已加入 `.gitignore`）
2. 数据库密码不硬编码在源代码中
3. `SECRET_KEY` 已更换为生产环境的强随机密钥
