// pages/login/login.js
Page({
  data: {
    loginMethod: 'password',  // 当前登录方式：'password'（密码）/'face'（人脸）
    studentId: '',            // 学号（密码登录用）
    password: '',             // 密码（密码登录用）
    isLoggingIn: false,       // 是否正在登录中（防止重复点击）
    message: '',              // 提示消息
    messageType: 'info',      // 消息类型：'info'/'success'/'error'
    countdown: 0,             // 人脸登录倒计时（拍照准备）
    showCamera: false,        // 是否显示相机（人脸登录时显示）
    cameraContext: null, // 缓存相机上下文，避免重复创建
    isCameraReady: false, // 标记相机是否初始化完成
    faceImagePath: ''         // 拍摄的人脸照片路径
  },
  onLoad: function () {
    console.log('登录页面加载完成');
    // 页面加载时检查本地是否有Token（自动登录）
    const token = wx.getStorageSync('token');
    if (token) {
      this.loadUserInfoAndNavigate(); // 自动登录逻辑
    }
  },
  // 切换登录方式（密码 ↔ 人脸）
  switchLoginMethod(e) {
    const method = e.currentTarget.dataset.method;
    this.setData({
      loginMethod: method,
      message: '',          // 清空之前的提示
      messageType: 'info',
      isLoggingIn: false,   // 重置登录状态
      countdown: 0,         // 重置倒计时
      faceImagePath: '',    // 清空人脸照片
      showCamera: method === 'face'  // 人脸登录时显示相机
    });
    // 切换到人脸登录时，检查相机权限
    if (method === 'face') {
      this.checkCameraPermission();
    }
  },
  // 学号输入框绑定
  onStudentIdInput(e) {
    this.setData({ studentId: e.detail.value.trim() });
  },
  // 密码输入框绑定
  onPasswordInput(e) {
    this.setData({ password: e.detail.value.trim() });
  },
  // 检查相机权限（人脸登录用）
  checkCameraPermission() {
    const that = this;
    wx.authorize({
      scope: 'scope.camera',
      success() {
        console.log('相机权限已授权');
        that.setData({ showCamera: true });
      },
      fail() {
        // 权限未授权，提示用户去设置开启
        wx.showModal({
          title: '权限提示',
          content: '人脸登录需要相机权限，请在设置中开启',
          showCancel: true,
          confirmText: '去设置',
          success(res) {
            if (res.confirm) {
              wx.openSetting();  // 打开微信设置页
            }
          }
        });
      }
    });
  },
  // 密码登录：调用/auth/token接口（修复this指向问题）
  passwordLogin() {
    const { studentId, password, isLoggingIn } = this.data;
    const app = getApp();
    const that = this;
    // 1. 基础校验：防止重复点击和空输入
    if (isLoggingIn) return;
    if (!studentId.trim()) {
      this.showMessage('请输入学号', 'error');
      return;
    }
    if (!password.trim()) {
      this.showMessage('请输入密码', 'error');
      return;
    }
    // 2. URL 合法性校验（解决 Invalid URL 核心步骤）
    const baseUrl = app.globalData.apiBaseUrl;
    // 检查 baseUrl 是否存在且包含 http/https 前缀
    if (!baseUrl || !/^https?:\/\/.+/.test(baseUrl)) {
      this.showMessage('后端地址配置错误，请联系管理员', 'error');
      this.setData({ isLoggingIn: false });
      return;
    }
    // 拼接完整接口地址（确保格式正确）
    const requestUrl = `${baseUrl}/api/v1/auth/token`;
    console.log('密码登录请求地址：', requestUrl);
    // 3. 初始化登录状态
    this.setData({
      isLoggingIn: true,
      message: '正在登录...',
      messageType: 'info'
    });
    // 4. 原生 wx.request 发送请求（避免封装函数问题）
    wx.request({
      url: requestUrl,
      method: 'POST',
      // 表单格式请求头（与后端 OAuth2PasswordRequestForm 匹配）
      header: {
        'Content-Type': 'application/x-www-form-urlencoded'
      },
      // 表单格式数据（手动拼接字符串，避免小程序自动转义问题）
      data: `username=${encodeURIComponent(studentId)}&password=${encodeURIComponent(password)}&grant_type=password`,
      // 超时时间（10秒，防止无限等待）
      timeout: 10000,
      // 5. 成功回调（严格匹配后端返回格式）
      success(res) {
        console.log('密码登录后端响应：', res);
        // 后端返回 200 表示请求本身成功（业务是否成功需看响应内容）
        if (res.statusCode === 200) {
          const responseData = res.data || {};
          // 检查是否包含 access_token（业务成功标识）
          if (responseData.access_token) {
            // 存储 Token 并跳转
            try {
              // 关键修改1：登录成功前清除旧的用户信息缓存（解决缓存残留）
              wx.removeStorageSync('userInfo');
              // 存储新Token
              wx.setStorageSync('token', responseData.access_token);
              app.globalData.token = responseData.access_token;
            } catch (e) {
              that.showMessage('本地存储Token失败，请检查存储空间', 'error');
              that.setData({ isLoggingIn: false });
              return;
            }
            // 显示成功消息并跳转
            that.setData({
              message: '密码登录成功！即将跳转...',
              messageType: 'success'
            });
            setTimeout(() => {
              // 直接调用 wx.switchTab，跳过中间函数
              wx.switchTab({
                url: '/pages/index/index',
                fail(err) {
                  console.error('跳转失败原因：', err);
                  that.showMessage('跳转失败，请检查首页路径配置', 'error');
                }
              });
            }, 1500);
          } else {
            // 业务失败（如学号密码错误）
            const errorMsg = responseData.detail || responseData.message || '学号或密码错误';
            that.showMessage(errorMsg, 'error');
          }
        } else {
          // HTTP 状态码非 200（如 404 接口不存在、500 后端异常）
          that.showMessage(`登录失败：后端返回${res.statusCode}错误`, 'error');
        }
      },
      // 6. 失败回调（网络错误、超时等）
      fail(err) {
        console.error('密码登录请求失败：', err);
        // 根据错误类型显示不同提示
        if (err.errMsg.includes('timeout')) {
          that.showMessage('登录超时，请检查网络', 'error');
        } else if (err.errMsg.includes('Invalid URL')) {
          that.showMessage('请求地址无效，请检查后端配置', 'error');
        } else {
          that.showMessage('网络错误，请检查网络后重试', 'error');
        }
      },
      // 7. 完成回调（无论成功失败，重置登录状态）
      complete() {
        that.setData({ isLoggingIn: false });
      }
    });
  },
  // 人脸登录：开始倒计时并拍照
  startFaceLogin() {
    const { isLoggingIn, showCamera } = this.data;
    if (isLoggingIn) return;
    if (!showCamera) {
      this.checkCameraPermission();
      return;
    }
    this.setData({
      isLoggingIn: true,
      countdown: 3,
      message: '即将拍照，请面对镜头...'
    });
    this.startCountdown();
  },
  // 人脸登录倒计时逻辑
  startCountdown() {
    const that = this;
    let currentCount = this.data.countdown;
    const timer = setInterval(() => {
      currentCount--;
      if (currentCount > 0) {
        that.setData({ countdown: currentCount });
      } else {
        clearInterval(timer);
        that.takeFacePhoto();  // 倒计时结束，拍摄人脸照片
      }
    }, 1000);
  },
  // 拍摄人脸照片（人脸登录用）
  takeFacePhoto() {
    const that = this;
    const ctx = wx.createCameraContext();
    ctx.takePhoto({
      quality: 'high',  // 高质量照片（提高识别成功率）
      success(res) {
        console.log('人脸照片拍摄成功：', res.tempImagePath);
        that.setData({ faceImagePath: res.tempImagePath });
        that.uploadFaceImage(res.tempImagePath);  // 上传照片到后端验证
      },
      fail(err) {
        console.error('拍照失败：', err);
        that.showMessage('拍照失败，请确保相机正常工作', 'error');
        that.setData({ isLoggingIn: false, countdown: 0 });
      }
    });
  },
  // 上传人脸照片到后端：调用/access/face/verify接口（修复this指向+语法闭合）
  uploadFaceImage(imagePath) {
    const that = this;
    const app = getApp();
    this.setData({ message: '正在验证人脸...' });
    wx.uploadFile({
      url: app.globalData.apiBaseUrl + '/api/v1/access/face/verify',
      filePath: imagePath,
      name: 'file',  // 与后端File参数名对应
      formData: {},  // 登录场景：不传dormitory
      header: { 'Accept': 'application/json' },
      success(uploadRes) {
        // 修复4：处理uploadFile的响应（可能是字符串，需转JSON）
        let res;
        try {
          res = JSON.parse(uploadRes.data);
        } catch (e) {
          that.showMessage('后端响应格式错误，请联系管理员', 'error');
          return;
        }
        console.log('人脸验证后端响应：', res);
        // 修复5：从res中获取similarity（之前引用未定义的responseData）
        const similarity = res.data?.similarity || 0;
        
        if (res.code === 200) {
          // 校验Token存储（兼容res.data为空的情况）
          const accessToken = res.data?.access_token || '';
          try {
            // 关键修改2：人脸登录成功前清除旧的用户信息缓存
            wx.removeStorageSync('userInfo');
            // 存储新Token
            wx.setStorageSync('token', accessToken);
            app.globalData.token = accessToken;
          } catch (e) {
            that.showMessage('本地存储Token失败，请检查存储空间', 'error');
            that.setData({ isLoggingIn: false });
            return;
          }
          // 显示成功消息（含相似度）
          const similarityPercent = Math.round(similarity * 100);
          that.setData({
            message: `人脸登录成功！相似度：${similarityPercent}%，即将跳转...`,
            messageType: 'success'
          });
          // 延迟1500ms跳转
          setTimeout(() => {
            wx.switchTab({
              url: '/pages/index/index',
              fail(err) {
                console.error('跳转失败：', err);
                wx.redirectTo({ url: '/pages/index/index' });
              }
            });
          }, 1500);
        } else {
          that.showMessage(res.msg || '人脸识别失败', 'error');
        }
      },
      // 补全：wx.uploadFile的fail回调（之前缺失）
      fail(uploadErr) {
        console.error('人脸验证请求失败：', uploadErr);
        that.showMessage('网络错误，请检查网络后重试', 'error');
        that.setData({ isLoggingIn: false });
      },
      // 补全：wx.uploadFile的complete回调（之前缺失）
      complete() {
        that.setData({ isLoggingIn: false, countdown: 0 });
      }
    });
  },  // 补全：uploadFaceImage函数的闭合 }
  // 加载用户信息并跳转到首页（增强容错）
  loadUserInfoAndNavigate() {
    const that = this;
    const app = getApp();
    const token = wx.getStorageSync('token');
    // 容错：若Token不存在，不发起请求直接提示
    if (!token) {
      that.showMessage('登录状态失效，请重新登录', 'error');
      return;
    }
    app.request({
      url: '/api/v1/users/profile',
      method: 'GET',
      success(res) {
        console.log('获取用户信息响应：', res);
        const responseData = res.data || res;
        if (responseData.code === 200 && responseData.data) {
          // 存储用户信息
          app.globalData.userInfo = responseData.data;
          // 关键修改3：自动登录时覆盖旧用户信息缓存
          wx.setStorageSync('userInfo', responseData.data);
          // 修复5：使用wx.switchTab跳转（确保跳转到tabBar页面）
          wx.switchTab({
            url: '/pages/index/index',
            // 跳转失败的容错处理
            fail(err) {
              console.error('跳转首页失败：', err);
              // 若switchTab失败，尝试用redirectTo（兼容非tabBar页面场景）
              wx.redirectTo({
                url: '/pages/index/index',
                fail(err2) {
                  console.error('redirectTo首页也失败：', err2);
                  that.showMessage('跳转首页失败，请手动进入', 'error');
                }
              });
            }
          });
        } else {
          // 获取用户信息失败，清除Token重新登录
          wx.removeStorageSync('token');
          app.globalData.token = null;
          that.showMessage('获取用户信息失败，请重新登录', 'error');
        }
      },
      fail(err) {
        console.error('获取用户信息请求失败：', err);
        wx.removeStorageSync('token');
        app.globalData.token = null;
        that.showMessage('网络错误，无法获取用户信息', 'error');
      }
    });
  },
  // 显示提示消息
  showMessage(message, type = 'info') {
    this.setData({
      message: message,
      messageType: type
    });
    // 3秒后自动清空消息
    setTimeout(() => {
      this.setData({ message: '' });
    }, 3000);
  },
  // 相机错误处理（如权限被拒、设备无相机）
  cameraError(e) {
    console.error('相机初始化错误：', e);
    this.showMessage('相机初始化失败，请检查设备或权限', 'error');
    this.setData({ showCamera: false });
  }
});