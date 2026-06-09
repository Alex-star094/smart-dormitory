// pages/register/register.js
Page({
  data: {
    userId: '',
    countdown: 0,
    isRegistering: false,
    message: '',
    messageType: 'info'
  },

  onLoad: function () {
    console.log('注册页面加载');
    this.checkCameraPermission();
  },

  // 检查摄像头权限
  checkCameraPermission: function () {
    const that = this;
    wx.authorize({
      scope: 'scope.camera',
      success: function () {
        console.log('摄像头权限已授权');
      },
      fail: function () {
        wx.showModal({
          title: '提示',
          content: '需要摄像头权限才能进行人脸注册，请在设置中开启',
          showCancel: true,
          confirmText: '去设置',
          success: function (res) {
            if (res.confirm) {
              wx.openSetting();
            }
          }
        });
      }
    });
  },

  // 输入用户ID
  onUserIdInput: function (e) {
    this.setData({
      userId: e.detail.value
    });
  },

  // 开始注册流程
  startRegister: function () {
    if (!this.data.userId.trim()) {
      this.showMessage('请输入用户ID', 'error');
      return;
    }

    this.setData({
      isRegistering: true,
      countdown: 3,
      message: ''
    });

    // 倒计时开始
    this.startCountdown();
  },

  // 倒计时逻辑
  startCountdown: function () {
    const that = this;
    const timer = setInterval(() => {
      const currentCountdown = that.data.countdown - 1;
      that.setData({
        countdown: currentCountdown
      });

      if (currentCountdown <= 0) {
        clearInterval(timer);
        // 倒计时结束，自动拍照
        that.takePhoto();
      }
    }, 1000);
  },

  // 拍照
  takePhoto: function () {
    const ctx = wx.createCameraContext();
    ctx.takePhoto({
      quality: 'high',
      success: (res) => {
        console.log('拍照成功', res.tempImagePath);
        this.uploadImage(res.tempImagePath);
      },
      fail: (err) => {
        console.error('拍照失败', err);
        this.setData({
          isRegistering: false,
          countdown: 0
        });
        this.showMessage('拍照失败，请重试', 'error');
      }
    });
  },

  // 上传图片到后端
  uploadImage: function (imagePath) {
    const that = this;

    // 使用wx.uploadFile发送文件
    wx.uploadFile({
      url: getApp().globalData.apiBaseUrl + '/api/v1/face/register',
      filePath: imagePath,
      name: 'file',
      formData: {
        student_id: that.data.userId
      },
      header: {
        'Authorization': 'Bearer ' + wx.getStorageSync('token')
      },
      success: (uploadRes) => {
        const response = JSON.parse(uploadRes.data);
        that.setData({
          isRegistering: false,
          countdown: 0
        });

        if (response.code === 200) {
          that.showMessage('注册成功！', 'success');
          // 注册成功后可以自动返回或跳转
          setTimeout(() => {
            wx.navigateBack();
          }, 2000);
        } else {
          that.showMessage(response.msg || response.message || '注册失败', 'error');
        }
      },
      fail: (uploadErr) => {
        console.error('注册请求失败', uploadErr);
        that.setData({
          isRegistering: false,
          countdown: 0
        });
        that.showMessage('网络错误，请重试', 'error');
      }
    });
  },

  // 显示消息
  showMessage: function (message, type = 'info') {
    this.setData({
      message: message,
      messageType: type
    });
  },

  // 相机错误处理
  cameraError: function (e) {
    console.error('相机错误', e);
    this.showMessage('相机初始化失败', 'error');
  },

  // 相机停止
  cameraStop: function (e) {
    console.log('相机停止', e);
  }
});
