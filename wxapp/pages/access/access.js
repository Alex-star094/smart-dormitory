// pages/access/access.js
Page({
  data: {
    records: [],
    message: '',
    messageType: ''
  },

  onLoad: function() {
    this.checkLoginStatus();
    this.loadAccessRecords();
  },

  onShow: function() {
    this.checkLoginStatus();
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

  loadAccessRecords: function() {
    if (!this.checkLoginStatus()) return;
    wx.showLoading({
      title: '加载中...'
    });
    // 获取用户信息以确定角色
    getApp().request({
      url: '/api/v1/users/profile',
      method: 'GET'
    }).then(profileRes => {
      if (profileRes.code === 200) {
        const userRole = profileRes.data.role;
        let url = '/api/v1/access/records';
        let params = {};
        if (userRole === 'student') {
          // 学生查看自己的记录，后端会根据用户ID筛选
          params = {};
        }
        // 管理员可以查看所有记录，可选择按宿舍筛选
        getApp().request({
          url: url,
          method: 'GET',
          data: params
        }).then(res => {
          wx.hideLoading();
          if (res.code === 200) {
            // 核心修改：正确解析 records（取 res.data.records 而非 res.data）
            this.setData({
              records: res.data.records || []
            });
          } else {
            this.showMessage(res.message || '获取记录失败', 'error');
          }
        }).catch(err => {
          wx.hideLoading();
          console.error('获取通行记录失败:', err);
          this.showMessage('获取记录失败', 'error');
        });
      } else {
        wx.hideLoading();
        this.showMessage('获取用户信息失败', 'error');
      }
    }).catch(err => {
      wx.hideLoading();
      console.error('获取用户信息失败:', err);
      this.showMessage('获取用户信息失败', 'error');
    });
  }, // 修复1：闭合 loadAccessRecords 函数

  // 修复2：补充缺失的 showMessage 函数（原代码完全缺失，导致消息无法显示）
  showMessage: function(message, type = 'info') {
    this.setData({
      message: message,
      messageType: type
    });
    // 3秒后自动清空消息
    setTimeout(() => {
      this.setData({
        message: '',
        messageType: ''
      });
    }, 3000);
  },

  // 修复3：补充刷新记录的方法（原代码可能遗漏，确保刷新功能可用）
  refreshRecords: function() {
    this.loadAccessRecords();
  }
}); // 修复4：闭合 Page() 实例，确保页面正确注册