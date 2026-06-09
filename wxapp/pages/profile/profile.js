// pages/profile/profile.js
Page({
  data: {
    profile: null,
    isLoggedIn: false,
    faceImage: null,
    isUploading: false,
    message: '',
    messageType: ''
  },

  onLoad: function() {
    this.checkLoginStatus();
    this.loadProfile();
  },

  onShow: function() {
    // 页面显示时检查登录状态
    this.checkLoginStatus();
  },

  checkLoginStatus: function() {
    const token = wx.getStorageSync('token');
    const isLoggedIn = !!token;
    this.setData({
      isLoggedIn: isLoggedIn
    });

    if (isLoggedIn) {
      getApp().globalData.token = token;
    }
  },

  loadProfile: function() {
    if (!this.data.isLoggedIn) {
      this.showMessage('请先登录', 'error');
      return;
    }

    wx.showLoading({
      title: '加载中...'
    });

    getApp().request({
      url: '/api/v1/users/profile',
      method: 'GET'
    }).then(res => {
      wx.hideLoading();
      if (res.code === 200) {
        wx.setStorageSync('userInfo', res.data);
        this.setData({
          profile: res.data
        });
      } else {
        this.showMessage(res.message || '获取信息失败', 'error');
      }
    }).catch(err => {
      wx.hideLoading();
      console.error('获取个人信息失败:', err);
      this.showMessage('获取信息失败', 'error');
    });
  },

  refreshProfile: function() {
    this.loadProfile();
  },



  chooseFaceImage: function() {
    wx.chooseImage({
      count: 1,
      sizeType: ['original', 'compressed'],
      sourceType: ['album', 'camera'],
      success: (res) => {
        const tempFilePath = res.tempFilePaths[0];
        this.setData({
          faceImage: tempFilePath
        });
      },
      fail: (err) => {
        console.error('选择图片失败:', err);
        this.showMessage('选择图片失败', 'error');
      }
    });
  },

  uploadFaceImage: function() {
    if (!this.data.isLoggedIn) {
      this.showMessage('请先登录', 'error');
      return;
    }

    if (!this.data.faceImage) {
      this.showMessage('请先选择人脸照片', 'error');
      return;
    }

    this.setData({
      isUploading: true
    });

    wx.showLoading({
      title: '上传中...'
    });

    // 上传文件到后端
    wx.uploadFile({
      url: getApp().globalData.apiBaseUrl + '/api/v1/users/profile/face',
      filePath: this.data.faceImage,
      name: 'face_image',
      header: {
        'Authorization': `Bearer ${getApp().globalData.token}`
      },
      success: (res) => {
        wx.hideLoading();
        this.setData({
          isUploading: false
        });

        try {
          const data = JSON.parse(res.data);
          if (data.code === 200) {
            this.showMessage('人脸上传成功', 'success');
            this.setData({
              faceImage: null
            });
          } else {
            this.showMessage(data.message || '上传失败', 'error');
          }
        } catch (e) {
          this.showMessage('上传失败', 'error');
        }
      },
      fail: (err) => {
        wx.hideLoading();
        this.setData({
          isUploading: false
        });
        console.error('上传人脸失败:', err);
        this.showMessage('上传失败', 'error');
      }
    });
  },

  logout: function() {
    wx.showModal({
      title: '确认退出',
      content: '确定要退出登录吗？',
      success: (res) => {
        if (res.confirm) {
          wx.removeStorageSync('token');
          getApp().globalData.token = null;
          this.setData({
            isLoggedIn: false,
            profile: null
          });
          this.showMessage('已退出登录', 'success');
        }
      }
    });
  },

  goToLogin: function() {
    wx.redirectTo({
      url: '/pages/login/login'
    });
  },

  showMessage: function(message, type = 'info') {
    this.setData({
      message: message,
      messageType: type
    });

    // 3秒后自动隐藏消息
    setTimeout(() => {
      this.setData({
        message: '',
        messageType: ''
      });
    }, 3000);
  }
});
