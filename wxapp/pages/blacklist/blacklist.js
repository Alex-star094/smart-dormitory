// pages/manage/manage.js
Page({
  data: {
    blacklist: [],
    users: [],
    newUserId: '',
    idCard: '', // 新增：身份证号输入（适配后端二选一必填）
    reason: '',
    effectiveTo: '', // 新增：生效截止时间
    isAdding: false,
    isLoading: false,
    message: '',
    messageType: 'info',
    // 同步后端完整枚举值
    validReasons: ['discipline', 'security_risk', 'multiple_failure', 'admin_manual', 'other'],
    reasonLabels: ['违纪行为', '安全风险', '多次验证失败', '管理员手动添加', '其他原因'],
    statusMap: { 'active': '生效中', 'removed': '已移除', 'expired': '已过期' }
  },
  onLoad: function () {
    console.log('管理页面加载');
    // 1. 检查token（确保已登录）
    const token = getApp().globalData.token;
    if (!token) {
      wx.redirectTo({ url: '/pages/login/login' });
      return;
    }
    // 2. 检查管理员权限
    const userInfo = getApp().globalData.userInfo;
    if (userInfo && userInfo.role !== 'admin') {
      wx.showModal({
        title: '权限不足',
        content: '只有管理员才能访问管理页面',
        showCancel: false,
        confirmText: '确定',
        success: () => wx.navigateBack()
      });
      return;
    }
    this.loadData();
  },
  onShow: function () {
    if (!this.data.isLoading) this.loadData();
  },
  // 加载数据（适配后端表单接口）
  loadData: function () {
    if (this.data.isLoading) return;
    this.setData({ isLoading: true });
    Promise.all([this.loadBlacklist(), this.loadUsers()])
      .finally(() => {
        this.setData({ isLoading: false });
      });
  },
  // 加载黑名单（适配后端返回格式）
  loadBlacklist: function () {
    const that = this;
    return new Promise((resolve) => {
      getApp().request({
        url: '/api/v1/blacklist/active',
        method: 'GET',
        data: { skip: 0, limit: 20 } // 表单格式传递查询参数
      }).then((response) => {
        if (response.code === 200) {
          const blacklist = (response.data.records || []).map(record => ({
            id: record.id || '',
            userId: record.student_id || '未知学号',
            idCard: record.id_card || '未填写',
            reason: record.reason || '无原因',
            reasonCn: that.getReasonCn(record.reason),
            status: that.getStatusCn(record.status),
            addTime: record.created_at ? that.formatTime(record.created_at) : '未知时间',
            effectiveTo: record.effective_to ? that.formatTime(record.effective_to) : '永久生效'
          }));
          that.setData({ blacklist: blacklist });
        } else {
          that.showMessage(`加载黑名单失败：${response.message || '服务器异常'}`, 'error');
        }
        resolve();
      }).catch((error) => {
        console.error('加载黑名单失败:', error);
        that.showMessage('网络错误，无法加载黑名单', 'error');
        resolve();
      });
    });
  },
  // 加载用户列表
  loadUsers: function () {
    const that = this;
    return new Promise((resolve) => {
      getApp().request({
        url: '/api/v1/users/list',
        method: 'GET',
        data: { skip: 0, limit: 50 } // 表单格式传递查询参数
      }).then((response) => {
        if (response.code === 200) {
          const formattedUsers = (response.data.users || []).map(user => ({
            id: user.id || '',
            student_id: user.student_id || '',
            username: user.username || '未知用户',
            dormitory: user.dormitory || '未绑定宿舍',
            id_card: user.id_card || '未填写'
          }));
          that.setData({ users: formattedUsers });
        } else {
          that.showMessage(`用户列表加载失败：${response.message || '服务器异常'}`, 'warning');
          that.setData({ users: [] });
        }
        resolve();
      }).catch((error) => {
        console.error('加载用户列表失败:', error);
        that.showMessage('网络错误，用户列表无法加载', 'warning');
        that.setData({ users: [] });
        resolve();
      });
    });
  },
  // 【修改1：添加黑名单 - 适配JSON格式】
  addToBlacklist: function () {
    const { newUserId, idCard, reason, effectiveTo, isAdding, validReasons } = this.data;
    const userInfo = getApp().globalData.userInfo;
    if (isAdding) return;
    // 1. 校验：学号/身份证号二选一（原有逻辑不变）
    const trimmedUserId = newUserId.trim();
    const trimmedIdCard = idCard.trim();
    if (!trimmedUserId && !trimmedIdCard) {
      this.showMessage('请填写学号或身份证号中的至少一项', 'error');
      return;
    }
    // 2. 校验原因（原有逻辑不变）
    const trimmedReason = reason.trim();
    if (!trimmedReason || !validReasons.includes(trimmedReason)) {
      this.showMessage(`请选择有效原因：${this.data.reasonLabels.join('、')}`, 'error');
      return;
    }
    this.setData({ isAdding: true });
    const userName = this.getUserNameByStudentId(trimmedUserId) || trimmedUserId || trimmedIdCard;
    // 3. 核心修改：改为JSON格式传递参数
    getApp().request({
      url: '/api/v1/blacklist',
      method: 'POST',
      header: { 'Content-Type': 'application/json' }, // 改为JSON格式头
      data: { // 保持参数名不变，直接传递JSON对象
        name: userName,
        blacklist_type: 'student',
        reason: trimmedReason,
        student_id: trimmedUserId,
        id_card: trimmedIdCard,
        effective_to: effectiveTo,
        description: `${userInfo?.username || '管理员'}添加黑名单`
      }
    }).then((response) => {
      this.setData({ isAdding: false });
      if (response.code === 200) {
        this.showMessage('添加黑名单成功', 'success');
        this.setData({ newUserId: '', idCard: '', reason: '', effectiveTo: '' });
        this.loadBlacklist();
      } else {
        this.showMessage(`添加失败：${response.message || '参数错误'}`, 'error');
      }
    }).catch((error) => {
      console.error('添加黑名单失败:', error);
      this.setData({ isAdding: false });
      this.showMessage(`网络错误：${error.message || '请求失败'}`, 'error');
    });
  },
  // 【修改2：移除黑名单 - 修复JSON格式错误+注释错误】
  removeFromBlacklist: function (e) {
    const recordId = parseInt(e.currentTarget.dataset.record);
    if (isNaN(recordId) || recordId <= 0) {
      this.showMessage('请选择有效的黑名单记录', 'error');
      return;
    }
    const that = this;
    const adminName = getApp().globalData.userInfo?.username || '管理员';
    wx.showModal({
      title: '确认移除',
      content: '移除后该用户将恢复正常权限，是否继续？',
      confirmColor: '#f4333c',
      success: (res) => {
        if (res.confirm) {
          getApp().request({
            url: `/api/v1/blacklist/${recordId}/status`,
            method: 'PUT',
            header: { 'Content-Type': 'application/json' }, // 修正注释错误（删除“表单格式”）
            data: { // 保持参数名不变，直接传递JSON对象
              status: "removed",
              removal_reason: `${adminName}于${new Date().toLocaleString()}手动移除`
            }
          }).then((response) => {
            if (response.code === 200) {
              that.showMessage('移除黑名单成功', 'success');
              that.loadBlacklist();
            } else {
              that.showMessage(`移除失败：${response.message || '记录不存在'}`, 'error');
            }
          }).catch((error) => {
            console.error('移除黑名单失败:', error);
            that.showMessage(`网络错误：${error.message || '请求失败'}`, 'error');
          });
        }
      }
    });
  },
  // 辅助函数：通过学号查用户名
  getUserNameByStudentId: function (studentId) {
    const user = this.data.users.find(u => u.student_id === studentId);
    return user ? user.username : '';
  },
  // 辅助函数：枚举值转中文
  getReasonCn: function (reason) {
    const { validReasons, reasonLabels } = this.data;
    const index = validReasons.indexOf(reason);
    return index !== -1 ? reasonLabels[index] : reason;
  },
  // 辅助函数：状态转中文
  getStatusCn: function (status) {
    return this.data.statusMap[status] || status;
  },
  // 辅助函数：格式化时间
  formatTime: function (isoTime) {
    if (!isoTime) return '未知时间';
    const date = new Date(isoTime);
    return `${date.getFullYear()}-${(date.getMonth() + 1).toString().padStart(2, '0')}-${date.getDate().toString().padStart(2, '0')} ${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`;
  },
  // 输入处理
  onUserIdInput: function (e) { this.setData({ newUserId: e.detail.value.trim() }); },
  onIdCardInput: function (e) { this.setData({ idCard: e.detail.value.trim() }); },
  onReasonInput: function (e) { this.setData({ reason: e.detail.value.trim() }); },
  onEffectiveToInput: function (e) { 
    const inputDate = e.detail.value.trim();
    if (!inputDate) {
      this.setData({ effectiveTo: '' });
      return;
    }
    // 将 "2025-12-31" 转为 "2025-12-31T23:59:59"（后端支持的ISO格式）
    const isoDate = `${inputDate}T23:59:59`;
    this.setData({ effectiveTo: isoDate });
  },
  // 刷新数据
  refreshData: function () {
    this.showMessage('正在刷新数据...', 'info');
    this.loadData();
  },
  // 消息提示
  showMessage: function (message, type = 'info') {
    this.setData({ message: message, messageType: type });
    setTimeout(() => {
      this.setData({ message: '', messageType: 'info' });
    }, 3000);
  }
});