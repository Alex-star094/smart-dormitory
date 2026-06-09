// pages/visitors/visitors.js
Page({
  data: {
    visitors: [],
    userInfo: null,
    newVisitor: {
      name: '',
      contact: '',
      reason: ''
    },
    visitTime: '',
    isAdding: false,
    message: '',
    messageType: ''
  },
  onLoad: function() {
    this.checkLoginStatus();
    this.loadUserInfo();
    // 延迟加载访客列表，确保用户信息先加载完成
    setTimeout(() => {
      this.loadVisitors();
    }, 300);
  },
  onShow: function() {
    this.checkLoginStatus();
    // 页面显示时强制刷新用户信息和访客列表（解决切换账号缓存问题）
    this.loadUserInfo(true);
  },
  checkLoginStatus: function() {
    const token = wx.getStorageSync('token');
    if (!token) {
      this.showMessage('请先登录', 'error');
      return false;
    }
    getApp().globalData.token = token;
    return true;
  },
  // 新增：forceRefresh参数，强制从API获取最新用户信息
  loadUserInfo: function(forceRefresh = false) {
    if (!this.checkLoginStatus()) return;
    
    // 关键修改1：切换账号时强制清除所有缓存（解决403核心原因）
    wx.removeStorageSync('userInfo');
    getApp().globalData.userInfo = null;
    
    if (!forceRefresh) {
      // 非强制刷新时，尝试从缓存获取（优化性能）
      let userInfo = getApp().globalData.userInfo || wx.getStorageSync('userInfo');
      if (userInfo) {
        this.setData({ userInfo: userInfo });
        return;
      }
    }
    
    // 关键修改2：强制从API重新获取用户信息（确保账号切换后信息准确）
    getApp().request({
      url: '/api/v1/users/profile',
      method: 'GET'
    }).then(res => {
      if (res.code === 200) {
        this.setData({ userInfo: res.data });
        // 保存到全局和本地（覆盖旧缓存）
        getApp().globalData.userInfo = res.data;
        wx.setStorageSync('userInfo', res.data);
        // 用户信息更新后，重新加载访客列表（避免接口调用错误）
        this.loadVisitors();
      } else {
        this.showMessage('获取用户信息失败，请重试', 'error');
      }
    }).catch(err => {
      console.error('获取用户信息失败:', err);
      this.showMessage('获取用户信息失败，请重试', 'error');
    });
  },
  loadVisitors: function() {
    if (!this.checkLoginStatus() || !this.data.userInfo) return;
    
    wx.showLoading({ title: '加载中...' });
    const userInfo = this.data.userInfo;
    // 关键验证：打印用户角色和接口地址（便于调试）
    console.log('当前用户角色:', userInfo.role);
    let url = userInfo.role === 'admin' ? '/api/v1/visitors/list' : '/api/v1/visitors/my';
    console.log('调用接口地址:', url);
    
    getApp().request({
      url: url,
      method: 'GET'
    }).then(res => {
      wx.hideLoading();
      if (res.code === 200) {
        this.setData({ visitors: res.data.visitors || [] });
      } else {
        // 关键修改3：显示后端具体错误（便于排查403原因）
        this.showMessage(res.message || `获取访客列表失败（${res.code}）`, 'error');
      }
    }).catch(err => {
      wx.hideLoading();
      console.error('获取访客列表失败:', err);
      // 区分403错误，给出明确提示
      const errMsg = err.errMsg.includes('403') ? '权限不足，请检查账号角色' : '获取访客列表失败';
      this.showMessage(errMsg, 'error');
    });
  },
  refreshVisitors: function() {
    this.loadVisitors();
  },
  onNameInput: function(e) {
    this.setData({ 'newVisitor.name': e.detail.value });
  },
  onContactInput: function(e) {
    this.setData({ 'newVisitor.contact': e.detail.value });
  },
  onReasonInput: function(e) {
    this.setData({ 'newVisitor.reason': e.detail.value });
  },
  onTimeChange: function(e) {
    this.setData({ visitTime: e.detail.value });
  },
  addVisitor: function() {
    if (!this.checkLoginStatus()) return;
    const { newVisitor, visitTime } = this.data;
    
    if (newVisitor.contact.length !== 18) {
      this.showMessage('请输入18位身份证号', 'error');
      return;
    }
    if (!visitTime) {
      this.showMessage('请选择预约日期', 'error');
      return;
    }
    const dateReg = /^\d{4}-\d{2}-\d{2}$/;
    if (!dateReg.test(visitTime)) {
      this.showMessage('日期格式错误，请选择完整日期（如 2025-12-23）', 'error');
      return;
    }
    
    const visitorData = {
      visitor_name: newVisitor.name,
      id_card: newVisitor.contact,
      visit_date: visitTime,
      visit_reason: newVisitor.reason
    };
    
    // 关键修改4：POST请求改用data字段传递参数（规范格式，避免编码异常）
    this.setData({ isAdding: true });
    wx.showLoading({ title: '添加中...' });
    getApp().request({
      url: '/api/v1/visitors',
      method: 'POST',
      data: visitorData, // 改用data传递，自动处理编码
      header: { 'Content-Type': 'application/json' }, 
    }).then(res => {
      wx.hideLoading();
      this.setData({ isAdding: false });
      if (res.code === 200) {
        this.showMessage('添加访客成功', 'success');
        this.loadVisitors();
        this.setData({
          newVisitor: { name: '', contact: '', reason: '' },
          visitTime: ''
        });
      } else {
        this.showMessage(res.message || '添加失败', 'error');
      }
    }).catch(err => {
      wx.hideLoading();
      this.setData({ isAdding: false });
      console.error('添加访客失败:', err);
      this.showMessage('添加失败', 'error');
    });
  },
  approveVisitor: function(e) {
    const visitorId = e.currentTarget.dataset.id;
    this.updateVisitorStatus(visitorId, 'approved');
  },
  rejectVisitor: function(e) {
    const visitorId = e.currentTarget.dataset.id;
    this.updateVisitorStatus(visitorId, 'rejected');
  },
  updateVisitorStatus: function(visitorId, status) {
    console.log('接收的status参数:', status);
    if (!this.checkLoginStatus()) return;
    const { userInfo } = this.data;
    
    if (!userInfo || userInfo.role !== 'admin') {
      this.showMessage('仅管理员可审核', 'error');
      return;
    }
    
    const validStatus = status.toLowerCase();
  if (!['approved', 'rejected'].includes(validStatus)) {
    this.showMessage('状态值错误', 'error');
    return;
  }

    const requestData = {
      approval_status: validStatus,
      approve_note: ""
    };
    getApp().request({
      url: `/api/v1/visitors/${visitorId}/approve`,
      method: 'PUT',
      header: { 'Content-Type': 'application/json' },
      data: requestData
    }).then(res => {
      if (res.code === 200) {
        this.showMessage(validStatus === 'approved' ? '已批准' : '已拒绝', 'success');
        this.loadVisitors();
      } else {
        this.showMessage(res.message || '操作失败', 'error');
      }
    }).catch(err => {
      console.error('更新访客状态失败:', err);
      this.showMessage('操作失败', 'error');
    });
  },
  showMessage: function(message, type = 'info') {
    this.setData({
      message: message,
      messageType: type
    });
    setTimeout(() => {
      this.setData({ message: '', messageType: '' });
    }, 3000);
  }
});