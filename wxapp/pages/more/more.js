// pages/more/more.js - 系统菜单
Page({
  data: {
    isLoggedIn: false,
    isAdmin: false,
    userInfo: null,
    systemInfo: {
      version: '2.0.0',
      modules: 7,
    },
  },

  onLoad: function () {
    this.refresh();
  },

  onShow: function () {
    this.refresh();
  },

  refresh: function () {
    const token = wx.getStorageSync('token');
    const ui = getApp().globalData.userInfo || wx.getStorageSync('userInfo') || {};
    this.setData({
      isLoggedIn: !!token,
      isAdmin: ui.role === 'admin',
      userInfo: ui,
    });
  },

  // ---- 导航（仅保留非首页/非Tab页面入口）----
  goToRepair: function () {
    wx.navigateTo({ url: '/pages/repair/repair' });
  },
  goToEnergy: function () {
    wx.navigateTo({ url: '/pages/energy/energy' });
  },
  goToManage: function () {
    wx.navigateTo({ url: '/pages/manage/manage' });
  },
  goToRegister: function () {
    wx.navigateTo({ url: '/pages/register/register' });
  },
  goToLogin: function () {
    wx.redirectTo({ url: '/pages/login/login' });
  },

  // ---- 关于 ----
  goToAbout: function () {
    wx.showModal({
      title: '关于智安校园',
      content: '宿舍智能管理系统 v2.0\n\n功能模块：\n- 人脸识别通行\n- 访客预约审核\n- 能耗监控告警\n- 维修申报处理\n- 黑名单安全管理',
      showCancel: false,
    });
  },

  // ---- 缓存 ----
  clearCache: function () {
    const that = this;
    wx.showModal({
      title: '清除缓存',
      content: '将清除本地登录信息，需要重新登录',
      success: (res) => {
        if (res.confirm) {
          const app = getApp();
          app.globalData.userInfo = null;
          app.globalData.token = null;
          wx.clearStorageSync();
          that.setData({ isLoggedIn: false, isAdmin: false, userInfo: null });
          wx.showToast({ title: '已清除', icon: 'success' });
        }
      },
    });
  },

  // ---- 退出登录 ----
  logout: function () {
    const that = this;
    wx.showModal({
      title: '退出登录',
      content: '确定要退出当前账号吗？',
      success: (res) => {
        if (res.confirm) {
          wx.removeStorageSync('token');
          getApp().globalData.token = null;
          getApp().globalData.userInfo = null;
          that.setData({ isLoggedIn: false, isAdmin: false, userInfo: null });
          wx.showToast({ title: '已退出', icon: 'success' });
        }
      },
    });
  },
});
