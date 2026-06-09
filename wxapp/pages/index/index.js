// pages/index/index.js - 智能仪表盘
Page({
  data: {
    userInfo: null,
    isAdmin: false,
    isLoading: true,

    // 学生视图
    energy: { electricity: {}, water: {} },
    todayAccess: {},
    myRepairs: [],
    myVisitors: [],

    // 管理员视图
    overview: {},
    recentAccess: [],
    todos: [],

    // 公告
    notices: [],

    // 快捷入口
    quickActions: [],
  },

  onLoad: function () {
    this.loadAll();
  },

  onShow: function () {
    // 每次切回来刷新数据
    if (this.data.userInfo) {
      this.loadDashboard();
    } else {
      this.loadAll();
    }
  },

  onPullDownRefresh: function () {
    this.loadDashboard().then(() => wx.stopPullDownRefresh());
  },

  loadAll: function () {
    const token = wx.getStorageSync('token');
    if (!token) {
      this.setData({ isLoading: false });
      return;
    }
    getApp().globalData.token = token;
    this.loadDashboard();
  },

  loadDashboard: function () {
    const that = this;
    this.setData({ isLoading: true });

    return getApp().request({
      url: '/api/v1/dashboard/stats',
      method: 'GET',
    }).then(res => {
      if (res.code !== 200) throw new Error('Failed');

      const d = res.data;
      const isAdmin = d.user.role === 'admin';
      const actions = isAdmin
        ? [
            { icon: '👥', text: '用户管理', key: 'users' },
            { icon: '📋', text: '审核访客', key: 'visitors' },
            { icon: '🔧', text: '维修处理', key: 'repair' },
            { icon: '⚡', text: '能耗总览', key: 'energy' },
            { icon: '🚫', text: '黑名单', key: 'manage' },
          ]
        : [
            { icon: '🚪', text: '人脸通行', key: 'access' },
            { icon: '👤', text: '预约访客', key: 'visitors' },
            { icon: '🔧', text: '报修申请', key: 'repair' },
            { icon: '⚡', text: '能耗查询', key: 'energy' },
          ];

      that.setData({
        userInfo: d.user,
        isAdmin: isAdmin,
        energy: d.energy || {},
        todayAccess: d.today_access || {},
        myRepairs: d.my_repairs || [],
        myVisitors: d.my_visitors || [],
        overview: d.overview || {},
        recentAccess: d.recent_access || [],
        todos: d.todos || [],
        quickActions: actions,
        isLoading: false,
      });

      // 同时拉公告
      return getApp().request({
        url: '/api/v1/dashboard/notices',
        method: 'GET',
      });
    }).then(res => {
      if (res && res.code === 200) {
        that.setData({ notices: res.data || [] });
      }
    }).catch(err => {
      console.error('加载仪表盘失败:', err);
      that.setData({ isLoading: false });
    });
  },

  // ---- 快捷操作 ----
  onQuickAction: function (e) {
    const key = e.currentTarget.dataset.key;
    const routes = {
      users: '/pages/manage/manage',
      visitors: '/pages/visitors/visitors',
      repair: '/pages/repair/repair',
      energy: '/pages/energy/energy',
      access: '/pages/access/access',
      manage: '/pages/manage/manage',
    };
    const url = routes[key];
    if (!url) return;

    const isTab = ['access', 'visitors'].includes(key);
    if (isTab) {
      wx.switchTab({ url });
    } else {
      wx.navigateTo({ url });
    }
  },

  // ---- 跳转 ----
  goToProfile: function () {
    wx.switchTab({ url: '/pages/profile/profile' });
  },
  goToLogin: function () {
    wx.redirectTo({ url: '/pages/login/login' });
  },
  goToMore: function () {
    wx.navigateTo({ url: '/pages/more/more' });
  },

  // 公告点击
  onNoticeTap: function (e) {
    const idx = e.currentTarget.dataset.index;
    const notice = this.data.notices[idx];
    wx.showModal({
      title: notice.title,
      content: notice.content,
      showCancel: false,
    });
  },
});
