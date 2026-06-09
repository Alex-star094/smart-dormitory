// app.js
App({
  onLaunch: function () {
    this.globalData = {
      userInfo: null,
      // API 基础地址（修改此处指向你的后端服务器）
      apiBaseUrl: 'http://127.0.0.1:8000',
      token: wx.getStorageSync('token') || null
    };

    // 自动登录（若有token）
    if (this.globalData.token) {
      this.checkUserInfo();
    } else {
      wx.redirectTo({ url: '/pages/login/login' });
    }
  },

  // 检查用户信息
  checkUserInfo: function() {
    const that = this;
    this.request({
      url: '/api/v1/users/profile',
      method: 'GET'
    }).then(res => {
      if (res.code === 200) {
        that.globalData.userInfo = res.data;
        wx.setStorageSync('userInfo', res.data);
        wx.switchTab({ url: '/pages/index/index' });
      } else {
        wx.removeStorageSync('token');
        that.globalData.token = null;
        wx.redirectTo({ url: '/pages/login/login' });
      }
    }).catch(err => {
      console.error('检查用户信息失败:', err);
      wx.removeStorageSync('token');
      that.globalData.token = null;
      wx.redirectTo({ url: '/pages/login/login' });
    });
  },

  // 统一请求方法
  request: function(options) {
    const token = this.globalData.token;
    // 默认 JSON 格式请求头
    const baseHeader = {
      'Content-Type': 'application/json'
    };
    // 添加 token（若存在）
    if (token) {
      baseHeader['Authorization'] = `Bearer ${token}`;
    }
    options.header = { ...baseHeader, ...(options.header || {}) };

    // 拼接完整 URL
    if (!options.url.startsWith('http')) {
      options.url = this.globalData.apiBaseUrl + options.url;
    }

    return new Promise((resolve, reject) => {
      wx.request({
        ...options,
        success: (res) => {
          // Token 过期处理
          if (res.statusCode === 401) {
            wx.removeStorageSync('token');
            this.globalData.token = null;
            wx.redirectTo({ url: '/pages/login/login' });
            reject(new Error('Token 过期，请重新登录'));
            return;
          }
          resolve(res.data || {});
        },
        fail: (err) => {
          reject(new Error(`请求失败：${err.errMsg}`));
        }
      });
    });
  }
});
