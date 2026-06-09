# 智能宿舍管理系统微信小程序

## 项目简介

智能宿舍管理系统是一个基于微信小程序的综合宿舍管理平台，集成了人脸识别、访问控制、能耗管理、维修申请、访客预约等功能，为宿舍管理员和学生提供便捷的管理和服务。

## 功能特性

### 🔐 身份认证
- 人脸登录：通过摄像头进行人脸识别登录
- 密码登录：传统用户名密码登录方式
- JWT令牌认证：安全的身份验证机制

### 🏠 访问控制
- 实时通行记录查询
- 人脸识别通行验证
- 黑名单管理（管理员功能）

### ⚡ 能耗管理
- 当月能耗统计查看
- 能耗记录录入（管理员）
- 电费和水费监控

### 🔧 维修管理
- 维修申请提交
- 个人维修记录查询
- 维修进度跟踪

### 👥 访客管理
- 访客预约申请
- 预约审核（管理员）
- 访客进入记录

### 👤 用户管理
- 个人信息查看
- 宿舍信息更新
- 人脸信息录入

## 文件结构

```
wxapp/
├── app.js                    # 小程序全局逻辑和API封装
├── app.json                  # 小程序页面和权限配置
├── app.wxss                  # 全局样式文件
├── project.config.json       # 开发者工具配置
├── README.md                 # 项目说明文档
└── pages/                    # 页面目录
    ├── index/                # 首页 - 功能导航
    ├── login/                # 登录页面 - 支持人脸和密码登录
    ├── register/             # 注册页面 - 用户注册
    ├── profile/              # 个人中心 - 个人信息管理
    ├── access/               # 通行记录 - 查看出入记录
    ├── energy/               # 能耗管理 - 统计和录入
    ├── repair/               # 维修申请 - 提交和查询
    ├── visitors/             # 访客管理 - 预约和审核
    ├── manage/               # 系统管理 - 管理员功能
    └── more/                 # 更多功能 - 扩展页面
```

## 🚀 运行和测试步骤

### 1. 环境准备
1. 下载并安装[微信开发者工具](https://developers.weixin.qq.com/miniprogram/dev/devtools/download.html)
2. 使用微信扫描二维码登录开发者工具
3. 确保开发者工具版本 >= 1.06.2307260

### 2. 导入项目
1. 打开微信开发者工具
2. 点击 **"导入项目"**
3. **项目目录**：选择 `wxapp` 文件夹
4. **AppID**：暂时可以不填（用于体验模式），或申请小程序AppID
5. **项目名称**：`smart_dorm_face_recognition`
6. 点击 **"导入"**

### 3. 编译运行
1. 导入成功后，开发者工具会自动编译
2. 如遇编译错误，尝试：
   - 清除缓存：工具 → 清除缓存 → 清除所有
   - 重启开发者工具
   - 检查文件路径是否正确

### 4. 模拟器测试
1. 在模拟器中可以看到小程序界面
2. 点击不同功能按钮测试页面跳转
3. **注意**：模拟器不支持摄像头功能

### 5. 真机调试（重要）
1. 在开发者工具中点击 **"真机调试"**
2. 扫描二维码在手机上预览
3. 允许摄像头权限申请
4. 测试完整的摄像头和人脸识别功能

### 6. 网络配置
小程序默认连接 `http://localhost:8000`，如果后端运行在其他地址：

1. 修改 `app.js` 中的 `apiBaseUrl`：
```javascript
globalData: {
  // 修改这里为实际的后端地址
  apiBaseUrl: 'https://your-backend-server.com'
}
```

2. 确保后端支持跨域请求（CORS）

## 后端API要求

小程序需要以下后端API支持（基于FastAPI框架）：

### 🔐 认证相关
#### 密码登录
```
POST /api/v1/auth/token
Content-Type: application/x-www-form-urlencoded
参数：username=学号&password=密码
返回：{ access_token: string, token_type: string, user: object }
```

#### 人脸登录
```
POST /api/v1/auth/token/face?student_id=学号
返回：{ access_token: string, token_type: string, user: object }
```

#### 获取用户信息
```
GET /api/v1/users/profile
Authorization: Bearer <token>
返回：{ code: 200, data: { id, student_id, username, role, dormitory, phone, has_face } }
```

### 🏠 访问控制
#### 人脸验证通行
```
POST /api/v1/access/face/verify
Content-Type: multipart/form-data
参数：file=<image_file>&dormitory=宿舍号
返回：{ code: 200, data: { student_id, similarity, ... } }
```

#### 查询通行记录
```
GET /api/v1/access/records?dormitory=宿舍号&status=状态&skip=0&limit=20
Authorization: Bearer <token>
返回：{ code: 200, data: { total, records: [...] } }
```

### 👥 黑名单管理
#### 获取生效黑名单
```
GET /api/v1/blacklist/active
Authorization: Bearer <token>
返回：{ code: 200, data: { total, records: [...] } }
```

#### 添加黑名单
```
POST /api/v1/blacklist
Authorization: Bearer <token>
参数：{ student_id, name, blacklist_type, reason }
返回：{ code: 200, msg: "添加成功" }
```

#### 更新黑名单状态
```
PUT /api/v1/blacklist/{record_id}/status
Authorization: Bearer <token>
参数：{ status: "removed" }
返回：{ code: 200, msg: "更新成功" }
```

### ⚡ 能耗管理
#### 查询当月能耗
```
GET /api/v1/energy/current-month?dormitory=宿舍号
Authorization: Bearer <token>
返回：{ code: 200, data: { month, dormitory, electricity: {...}, water: {...} } }
```

#### 添加能耗记录
```
POST /api/v1/energy/record
Authorization: Bearer <token>
参数：{ dormitory, energy_type, consumption, unit, cost, month }
返回：{ code: 200, msg: "记录成功" }
```

### 🔧 维修管理
#### 提交维修申请
```
POST /api/v1/repair
Authorization: Bearer <token>
参数：{ title, description, category, priority, location, contact }
返回：{ code: 200, msg: "提交成功" }
```

#### 查询个人维修记录
```
GET /api/v1/repair/my
Authorization: Bearer <token>
返回：{ code: 200, data: { repairs: [...] } }
```

### 👤 访客管理
#### 创建访客预约
```
POST /api/v1/visitors
Authorization: Bearer <token>
参数：{ visitor_name, id_card, visit_date, visit_reason }
返回：{ code: 200, msg: "创建成功" }
```

#### 查询个人预约
```
GET /api/v1/visitors/my
Authorization: Bearer <token>
返回：{ code: 200, data: { visitors: [...] } }
```

#### 管理员审核预约
```
PUT /api/v1/visitors/{visitor_id}/approve
Authorization: Bearer <token>
参数：{ status: "approved" | "rejected" }
返回：{ code: 200, msg: "审核成功" }
```

#### 管理员获取所有预约
```
GET /api/v1/visitors/list?status=pending&skip=0&limit=20
Authorization: Bearer <token>
返回：{ code: 200, data: { total, visitors: [...] } }
```

### 👨‍💼 管理员功能
#### 获取用户列表
```
GET /api/v1/users/list?role=student&skip=0&limit=20
Authorization: Bearer <token>
返回：{ code: 200, data: { total, users: [...] } }
```

## 开发调试技巧

### 1. 控制台调试
- 在开发者工具中查看 Console 标签页
- 可以看到网络请求和错误信息

### 2. 网络调试
- 查看 Network 标签页监控API请求
- 检查请求参数和响应数据

### 3. 模拟API响应
在开发者工具中可以模拟API响应进行测试：

1. 打开"工具" -> "构建npm"
2. 在代码中使用 `wx.request` 的 `success` 回调中添加模拟数据

### 4. 常见问题
- **摄像头不工作**：确保在真机上测试，模拟器不支持摄像头
- **网络请求失败**：检查后端是否启动，地址是否正确
- **页面跳转问题**：检查页面路径配置是否正确

## 使用说明

### 学生用户
1. **登录**：选择人脸登录或密码登录进入系统
2. **通行记录**：查看个人的出入记录
3. **能耗查询**：查看宿舍当月电费和水费统计
4. **维修申请**：提交宿舍维修请求，跟踪处理进度
5. **访客预约**：为访客创建预约申请
6. **个人中心**：查看和更新个人信息，录入人脸信息

### 管理员用户
1. **通行管理**：监控所有用户的出入记录，管理黑名单
2. **能耗管理**：录入和管理宿舍能耗数据
3. **维修处理**：查看和处理维修申请，更新维修状态
4. **访客审核**：审核访客预约申请
5. **用户管理**：查看所有用户信息

## 🔧 故障排除

### 编译错误："Cannot read property 'getPreCompileOptions' of undefined"
**原因**：开发者工具版本过高或配置不兼容

**解决方案**：
1. 更新 `project.config.json` 中的 `libVersion` 为 `"2.24.6"`
2. 清除开发者工具缓存：工具 → 清除缓存 → 清除所有
3. 重启开发者工具
4. 如果还有问题，尝试降级开发者工具版本

### 错误："无效的 app.json permission["scope.userInfo"]"
**原因**：权限配置格式错误

**解决方案**：
- 小程序已移除 `permission` 配置中的用户信息权限
- 权限通过 `wx.authorize` 在页面中动态申请
- 参考已修复的 `app.json` 配置

### 摄像头权限问题
**原因**：未获得摄像头使用权限

**解决方案**：
1. 在真机上测试（模拟器不支持摄像头）
2. 允许小程序申请摄像头权限
3. 如被拒绝，可在设置中重新开启

### 网络请求失败
**原因**：后端服务未启动或地址错误

**解决方案**：
1. 确保后端服务正在运行
2. 检查 `app.js` 中的 `apiBaseUrl` 配置
3. 确认后端支持CORS跨域请求
4. 在开发者工具Network标签页查看请求详情

### 页面显示异常
**原因**：样式或布局问题

**解决方案**：
1. 检查rpx单位使用是否正确
2. 确认flex布局兼容性
3. 在不同机型上测试适配

## 注意事项

- **权限要求**：小程序需要摄像头权限进行人脸识别
- **网络要求**：确保网络连接稳定，后端服务正常运行
- **环境要求**：人脸识别需要在光线充足的环境下进行
- **数据安全**：所有API请求使用JWT令牌认证
- **兼容性**：支持微信版本6.6.0及以上
- **测试建议**：建议在真机上进行完整功能测试

## 技术栈

- **前端框架**：微信小程序原生框架
- **后端框架**：FastAPI (Python)
- **数据库**：MySQL
- **认证方式**：JWT (JSON Web Token)
- **人脸识别**：基于深度学习的 face_recognition 库
- **部署方式**：Docker容器化部署

## 版本信息

- 当前版本：v1.0.0
- 最后更新：2024年12月20日
- 兼容后端版本：smart_dorm_backend v1.0.0

## 贡献指南

1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情
