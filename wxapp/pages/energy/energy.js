// pages/energy/energy.js
Page({
  data: {
    // 用户信息
    userInfo: null,
    
    // 能耗列表相关
    energyList: [],
    isLoading: false,
    hasMore: true,
    pageSkip: 0,
    pageLimit: 10,

    // 搜索相关（管理员）
    searchKeyword: '',
    energyTypeFilter: 0, // 0:全部, 1:电力, 2:用水
    alarmFilter: 0, // 0:全部, 1:仅看告警, 2:只看正常
    monthFilter: '',
    searchParams: {}, // 关键修复：初始化searchParams，解决未定义错误
    
    // 消息提示
    message: '',
    messageType: '',
    
    // 能耗记录表单（学生）
    energyTypes: ['电力', '水'],
    energyTypeIndex: 0,
    recordData: {
      dormitory: '',
      consumption: '',
      unit: '度',
      month: '',
      energy_type: '' // 添加这个字段用于后端
    },
    previewCost: '0.00',
    isRecording: false,
    
    // 告警相关
    showAlarmModal: false,
    selectedRecordId: null,
    alarmReason: '',
    isOperating: false
  },

  onLoad: function() {
    this.checkLoginStatus();
    this.loadUserInfo();
  },

  onShow: function() {
    this.loadUserInfo(true);
    // 页面显示时重新加载数据
    if (this.data.userInfo) {
      this.loadEnergyList(true);
    }
  },

  checkLoginStatus: function() {
    const token = wx.getStorageSync('token');
    if (!token) {
      this.showMessage('请先登录', 'error');
      setTimeout(() => {
        wx.redirectTo({
          url: '/pages/login/login'
        });
      }, 1500);
      return false;
    }
    getApp().globalData.token = token;
    return true;
  },

  loadUserInfo: function(forceRefresh = false) {
    if (!this.checkLoginStatus()) return;
    if (forceRefresh) {
      wx.removeStorageSync('userInfo');
      getApp().globalData.userInfo = null;
    }
    // 尝试从本地存储获取用户信息
    let userInfo = wx.getStorageSync('userInfo');
    if (userInfo) {
      this.setData({
        userInfo: userInfo,
        'recordData.dormitory': userInfo.dormitory || ''
      });
      this.loadEnergyList(true);
    } else {
      // 如果没有，从API获取
      getApp().request({
        url: '/api/v1/users/profile',
        method: 'GET'
      }).then(res => {
        if (res.code === 200) {
          this.setData({
            userInfo: res.data,
            'recordData.dormitory': res.data.dormitory || ''
          });
          // 保存到本地
          wx.setStorageSync('userInfo', res.data);
          this.loadEnergyList(true);
        }
      }).catch(err => {
        console.error('获取用户信息失败:', err);
        this.showMessage('获取用户信息失败', 'error');
      });
    }
  },

  // 加载能耗列表（仅修改map中的cost处理逻辑）
  loadEnergyList: function(isRefresh = false) {
    const { userInfo, pageSkip, pageLimit, searchKeyword, energyTypeFilter, alarmFilter, monthFilter, searchParams } = this.data;
    
    if (!userInfo) {
      console.log('用户信息未加载');
      return;
    }
    
    if (isRefresh) {
      this.setData({
        pageSkip: 0,
        hasMore: true,
        energyList: [],
        isLoading: true
      });
    } else if (!this.data.hasMore) {
      return;
    }
    
    // 构建请求参数
    let url = '';
    let params = {
      skip: isRefresh ? 0 : pageSkip,
      limit: pageLimit
    };
    
    if (userInfo.role === 'admin') {
      // 管理员使用搜索接口
      url = '/api/v1/energy/admin/search';
      if (searchKeyword) params.keyword = searchKeyword;
      if (searchParams.energy_type) params.energy_type = searchParams.energy_type; // 使用初始化后的searchParams
      if (alarmFilter > 0) {
        params.has_alarm = alarmFilter === 1;
      }
      if (monthFilter) params.month = monthFilter;
    } else {
      // 学生使用列表接口
      url = '/api/v1/energy/list';
      // 学生只能查看自己宿舍的能耗
      params.dormitory = userInfo.dormitory;
    }
    
    console.log('请求参数:', { url, params });
    
    getApp().request({
      url: url,
      method: 'GET',
      data: params
    }).then(res => {
      console.log('能耗列表响应:', res);
      if (res.code === 200) {
        const data = res.data;
        const newList = isRefresh ? data.records : [...this.data.energyList, ...data.records];
        const processedList = newList.map(item => {
          // 1. 确保 energy_type 存在（兼容后端返回空的情况）
          const energyType = item.energy_type || (item.energy_type_cn === '电力' ? 'electricity' : 'water');
          // 2. 关键修改：强制将cost转为数字（解决toFixed报错）
          // 先尝试解析后端返回的cost，失败则用0兜底，再计算费用
          let cost = parseFloat(item.cost) || 0;
          // 若cost仍为0或无效，前端兜底计算
          if (cost === 0 || isNaN(cost)) {
            const price = energyType === 'electricity' ? 0.667 : 4.05;
            cost = (parseFloat(item.consumption) || 0) * price;
          }
          // 3. 统一保留2位小数（此时cost必为数字，可安全调用toFixed）
          return { ...item, cost: cost.toFixed(2) };
        });
        this.setData({
          energyList: processedList,
          hasMore: data.page?.has_more || false,
          pageSkip: isRefresh ? data.records.length : this.data.pageSkip + data.records.length,
          isLoading: false
        });
      } else {
        this.showMessage(res.message || '加载能耗列表失败', 'error');
        this.setData({ isLoading: false });
      }
    }).catch(err => {
      console.error('获取能耗列表失败:', err);
      this.showMessage('网络错误，请重试', 'error');
      this.setData({ isLoading: false });
    });
  },

  // 搜索相关函数
  onSearchInput: function(e) {
    this.setData({
      searchKeyword: e.detail.value
    });
  },

  searchEnergy: function() {
    this.loadEnergyList(true);
  },

  onEnergyTypeFilterChange: function(e) {
    const filterValue = e.detail.value;
    let energyType = "";
    // 映射为后端要求的枚举值（如：electricity=电力，water=用水）
    if (filterValue === 1) {
      energyType = "electricity"; // 后端对应“电力”的枚举值
    } else if (filterValue === 2) {
      energyType = "water"; // 后端对应“用水”的枚举值
    }
    // 将筛选值存入searchParams，确保请求时携带
    this.setData({
      energyTypeFilter: filterValue,
      "searchParams.energy_type": energyType
    }, () => {
      this.loadEnergyList(true); // 重新加载列表，携带筛选参数
    });
  },

  onAlarmFilterChange: function(e) {
    this.setData({
      alarmFilter: e.detail.value
    }, () => {
      this.loadEnergyList(true);
    });
  },

  onMonthInput: function(e) {
    this.setData({
      monthFilter: e.detail.value
    });
  },

  // 刷新列表
  refreshEnergyList: function() {
    this.loadEnergyList(true);
  },

  // 加载更多
  loadMore: function() {
    if (!this.data.isLoading && this.data.hasMore) {
      this.loadEnergyList();
    }
  },

  // 管理员触发告警
  triggerAlarmForRecord: function(e) {
    const recordId = e.currentTarget.dataset.recordId;
    this.setData({
      showAlarmModal: true,
      selectedRecordId: recordId,
      alarmReason: ''
    });
  },

  // 能耗记录表单相关函数
  onDormitoryInput: function(e) {
    this.setData({
      'recordData.dormitory': e.detail.value
    });
  },

  onEnergyTypeChange: function(e) {
    const index = e.detail.value;
    const energyTypeCN = this.data.energyTypes[index];
    // 中文转英文，与后端EnergyType枚举值对应
    const energyTypeEN = energyTypeCN === '电力' ? 'electricity' : 'water';
    const unit = energyTypeCN === '电力' ? '度' : '吨';
    
    this.setData({
      energyTypeIndex: index,
      'recordData.energy_type': energyTypeEN,
      'recordData.unit': unit
    });
    
    this.calculateCost();
  },

  onConsumptionInput: function(e) {
    const value = e.detail.value;
    this.setData({
      'recordData.consumption': value
    });
    this.calculateCost();
  },

  onUnitInput: function(e) {
    this.setData({
      'recordData.unit': e.detail.value
    });
  },

  onMonthInputForm: function(e) {
    const month = e.detail.value;
    // 校验月份格式为YYYY-MM
    const monthReg = /^\d{4}-\d{2}$/;
    if (month && !monthReg.test(month)) {
      this.showMessage('月份格式应为YYYY-MM（如2025-01）', 'error');
      return;
    }
    this.setData({
      'recordData.month': month
    });
  },

  calculateCost: function() {
    const { energyTypeIndex, recordData } = this.data;
    const consumption = parseFloat(recordData.consumption) || 0;
    
    // 模拟计算费用
    let price = 0.667; // 电费单价
    if (energyTypeIndex === 1) {
      price = 4.05; // 水费单价
    }
    
    const cost = consumption * price;
    this.setData({
      previewCost: cost.toFixed(2)
    });
  },

  // 学生记录能耗
  recordConsumption: function() {
    if (!this.checkLoginStatus()) return;
    const data = this.data.recordData;
    const userInfo = this.data.userInfo;
    // 校验所有必要字段
    if (!data.dormitory || !data.dormitory.trim()) {
      this.showMessage('请填写宿舍号', 'error');
      return;
    }
    if (!data.energy_type) {
      this.showMessage('请选择能源类型', 'error');
      return;
    }
    if (data.consumption === '' || isNaN(data.consumption) || parseFloat(data.consumption) < 0) {
      this.showMessage('请填写有效的消耗量（不能为负数）', 'error');
      return;
    }
    if (!data.unit || !data.unit.trim()) {
      this.showMessage('请填写单位', 'error');
      return;
    }
    if (!data.month || !data.month.trim()) {
      this.showMessage('请填写月份', 'error');
      return;
    }
    // 学生只能添加自己宿舍的记录
    if (userInfo.role === 'student' && data.dormitory !== userInfo.dormitory) {
      this.showMessage('只能添加自己宿舍的能耗记录', 'error');
      return;
    }
    const dormitory = encodeURIComponent(data.dormitory.trim());
    const energyType = encodeURIComponent(data.energy_type);
    const consumption = encodeURIComponent(parseFloat(data.consumption)); 
    const unit = encodeURIComponent(data.unit.trim()); // 中文单位完整编码
    const month = encodeURIComponent(data.month.trim());
    // 3. 拼接URL（用&分隔，参数名与后端完全一致）
    const requestUrl = `/api/v1/energy/record?dormitory=${dormitory}&energy_type=${energyType}&consumption=${consumption}&unit=${unit}&month=${month}`;
    this.setData({ isRecording: true });
    wx.showLoading({ title: '记录中...' });
    getApp().request({
      url: requestUrl,
      method: 'POST',
      header: {
        'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8'
      }
    }).then(res => {
      wx.hideLoading();
      this.setData({ isRecording: false });
      if (res.code === 200) {
        this.showMessage('记录成功', 'success');
        // 重置表单
        this.setData({
          recordData: {
            dormitory: userInfo.dormitory || '',
            consumption: '',
            unit: '度',
            month: '',
            energy_type: ''
          },
          energyTypeIndex: 0,
          previewCost: '0.00'
        });
        // 刷新列表
        this.loadEnergyList(true);
      } else {
        this.showMessage(res.message || '记录失败', 'error');
      }
    }).catch(err => {
      wx.hideLoading();
      this.setData({ isRecording: false });
      console.error('记录能耗失败:', err);
      this.showMessage('记录失败', 'error');
    });
  },

  // 告警相关函数
  openAlarmModal: function(e) {
    const recordId = e.currentTarget.dataset.recordId;
    this.setData({
      showAlarmModal: true,
      selectedRecordId: recordId,
      alarmReason: ''
    });
  },

  closeAlarmModal: function() {
    this.setData({
      showAlarmModal: false,
      selectedRecordId: null,
      alarmReason: '',
      isOperating: false
    });
  },

  onAlarmReasonInput: function(e) {
    this.setData({
      alarmReason: e.detail.value
    });
  },

  // 管理员手动触发告警
  triggerAlarm: function() {
    if (!this.checkLoginStatus()) return;
    
    const recordId = this.data.selectedRecordId;
    const alarmReason = this.data.alarmReason;
    if (!recordId) {
      this.showMessage('请选择要操作的能耗记录', 'error');
      return;
    }
    this.setData({ isOperating: true });
    wx.showLoading({ title: '提交中...' });
    
    const requestData = {};
    if (alarmReason && alarmReason.trim()) {
      requestData.alarm_reason = alarmReason.trim();
    }
    getApp().request({
      url: `/api/v1/energy/admin/record/${recordId}/alarm`,
      method: 'POST',
      data: requestData
    }).then(res => {
      wx.hideLoading();
      this.setData({
        isOperating: false,
        showAlarmModal: false
      });
      
      if (res.code === 200) {
        this.showMessage('告警触发成功', 'success');
        // 刷新列表
        this.loadEnergyList(true);
      } else {
        this.showMessage(res.message || '告警触发失败', 'error');
      }
    }).catch(err => {
      wx.hideLoading();
      this.setData({
        isOperating: false,
        showAlarmModal: false
      });
      console.error('触发告警失败:', err);
      this.showMessage('告警触发失败', 'error');
    });
  },

  // 显示消息提示
  showMessage: function(message, type = 'info') {
    this.setData({
      message: message,
      messageType: type
    });
    setTimeout(() => {
      this.setData({
        message: '',
        messageType: ''
      });
    }, 3000);
  },

  // 页面卸载时清理
  onUnload: function() {
    // 清理定时器等资源
    if (this.messageTimer) {
      clearTimeout(this.messageTimer);
    }
  }
});