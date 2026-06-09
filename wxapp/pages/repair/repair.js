// pages/repair/repair.js
Page({
  data: {
    records: [],
    submitData: {
      title: '',
      description: '',
      category: '',
      priority: '中',
      location: '',
      contact_phone: ''
    },
    priorities: ['低', '中', '高', '紧急'],
    priorityIndex: 1,
    isSubmitting: false,
    message: '',
    messageType: '',
    isAdmin: false,
    repairStatusOptions: [
      { label: '待处理', value: 'pending' },
      { label: '处理中', value: 'processing' },
      { label: '已完成', value: 'completed' },
      { label: '已取消', value: 'cancelled' }
    ],
    repairStatusIndex: 0,
    showOperateModal: false,
    currentRepairId: null,
    operateForm: {
      repairerId: '',
      repairStatus: 'pending',
      expectedTime: '',
      repairNotes: '',
      repairResult: '',
      cost: ''
    },
    isOperating: false
  },
  onLoad: function() {
    this.checkLoginStatus();
    this.loadUserInfo();
    this.loadRepairRecords();
  },
  onShow: function() {
    this.loadUserInfo();
    this.loadRepairRecords();
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
  loadUserInfo: function() {
    if (!this.checkLoginStatus()) return;
    const localUserInfo = wx.getStorageSync('userInfo') || {};
    const globalUserInfo = getApp().globalData.userInfo || {};
    const latestUserInfo = {
      ...globalUserInfo,
      ...localUserInfo
    };
    getApp().globalData.userInfo = latestUserInfo;
    wx.setStorageSync('userInfo', latestUserInfo);
    if (latestUserInfo.dormitory && !this.data.submitData.location) {
      this.setData({
        'submitData.location': latestUserInfo.dormitory
      });
    }
    this.setData({
      isAdmin: latestUserInfo.role === 'admin'
    });
  },
  loadRepairRecords: function() {
    if (!this.checkLoginStatus()) return;
    wx.showLoading({ title: '加载中...' });
    const { isAdmin } = this.data;
    const url = isAdmin ? '/api/v1/repair/list' : '/api/v1/repair/my';
    getApp().request({
      url: url,
      method: 'GET'
    }).then(res => {
      wx.hideLoading();
      if (res.code === 200) {
        const records = isAdmin ? res.data.repairs || [] : res.data.repairs || [];
        this.setData({ records });
      } else {
        this.showMessage(res.message || '获取记录失败', 'error');
      }
    }).catch(err => {
      wx.hideLoading();
      console.error('获取维修记录失败:', err);
      this.showMessage('获取记录失败', 'error');
    });
  },
  refreshRecords: function() {
    this.loadRepairRecords();
  },
  onTitleInput: function(e) {
    this.setData({ 'submitData.title': e.detail.value });
  },
  onDescriptionInput: function(e) {
    this.setData({ 'submitData.description': e.detail.value });
  },
  onCategoryInput: function(e) {
    this.setData({ 'submitData.category': e.detail.value });
  },
  onPriorityChange: function(e) {
    const index = e.detail.value;
    const chinesePriority = this.data.priorities[index];
    this.setData({
      priorityIndex: index,
      'submitData.priority': chinesePriority
    });
  },
  onLocationInput: function(e) {
    this.setData({ 'submitData.location': e.detail.value });
  },
  onContactInput: function(e) {
    this.setData({ 'submitData.contact_phone': e.detail.value });
  },
  submitRepair: function() {
    if (this.data.isAdmin) {
      this.showMessage('管理员无需提交报修申请', 'error');
      return;
    }
    if (!this.checkLoginStatus()) {
      return;
    }
    const submitData = this.data.submitData;
    let userInfo = wx.getStorageSync('userInfo') || {};
    if (!userInfo.dormitory) {
      userInfo = getApp().globalData.userInfo || {};
    }
    if (!userInfo || !userInfo.id) {
      this.showMessage('用户信息不存在，请重新登录', 'error');
      return;
    }
    if (!userInfo.dormitory) {
      this.showMessage('请先在个人中心绑定宿舍', 'error');
      return;
    }
    if (!submitData.title.trim()) {
      this.showMessage('请填写维修标题', 'error');
      return;
    }
    if (!submitData.description.trim()) {
      this.showMessage('请填写维修详情描述', 'error');
      return;
    }
    if (!submitData.category.trim()) {
      this.showMessage('请选择/填写维修类别（如水电、家具）', 'error');
      return;
    }
    if (!submitData.location.trim()) {
      this.showMessage('请填写维修位置（已自动填充宿舍号，可补充详细位置）', 'error');
      return;
    }
    if (!submitData.contact_phone.trim()) {
      this.showMessage('请填写联系电话', 'error');
      return;
    }
    if (this.data.isSubmitting) {
      return;
    }
    this.setData({ isSubmitting: true });
    wx.showLoading({ title: '提交中...' });
    function formatFormData(data) {
      let arr = [];
      for (let key in data) {
        if (data.hasOwnProperty(key) && data[key] !== undefined && data[key] !== null) {
          arr.push(`${encodeURIComponent(key)}=${encodeURIComponent(data[key])}`);
        }
      }
      return arr.join('&');
    }
    const formData = {
      title: submitData.title.trim(),
      description: submitData.description.trim(),
      category: submitData.category.trim(),
      priority: submitData.priority,
      location: submitData.location.trim(),
      contact_phone: submitData.contact_phone.trim(),
      user_id: userInfo.id
    };
    console.log('提交报修参数：', formData);
    getApp().request({
      url: '/api/v1/repair',
      method: 'POST',
      header: {
        'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8',
        'Authorization': `Bearer ${wx.getStorageSync('token')}`
      },
      data: formatFormData(formData)
    }).then(res => {
      wx.hideLoading();
      this.setData({ isSubmitting: false });
      console.log('报修提交返回结果：', res);
      if (res.code === 200) {
        this.showMessage('提交成功，等待管理员处理', 'success');
        this.setData({
          submitData: {
            title: '',
            description: '',
            category: '',
            priority: '中',
            location: userInfo.dormitory || '',
            contact_phone: ''
          },
          priorityIndex: 1
        });
        this.loadRepairRecords();
      } else {
        this.showMessage(`提交失败：${res.message || '未知错误'}`, 'error');
      }
    }).catch(err => {
      wx.hideLoading();
      this.setData({ isSubmitting: false });
      console.error('报修提交异常：', err);
      if (err.errMsg && err.errMsg.includes('request:fail')) {
        this.showMessage('网络异常，请检查网络连接后重试', 'error');
      } else {
        this.showMessage(`提交失败：${err.message || '服务器异常，请稍后重试'}`, 'error');
      }
    });
  },
  openOperateModal: function(e) {
    const repairId = e.currentTarget.dataset.repairId;
    const repair = this.data.records.find(item => item.id === repairId) || {};
    const statusIndex = this.data.repairStatusOptions.findIndex(
      item => item.value === (repair.status || 'pending')
    );
    this.setData({
      showOperateModal: true,
      currentRepairId: repairId,
      repairStatusIndex: statusIndex > -1 ? statusIndex : 0,
      operateForm: {
        repairerId: '',
        repairStatus: repair.status || 'pending',
        expectedTime: '',
        repairNotes: '',
        repairResult: '',
        cost: ''
      }
    });
  },
  closeOperateModal: function() {
    this.setData({
      showOperateModal: false,
      currentRepairId: null,
      operateForm: {
        repairerId: '',
        repairStatus: 'pending',
        expectedTime: '',
        repairNotes: '',
        repairResult: '',
        cost: ''
      },
      repairStatusIndex: 0
    });
  },
  onOperateFormInput: function(e) {
    const { key } = e.currentTarget.dataset;
    this.setData({
      [`operateForm.${key}`]: e.detail.value
    });
  },
  onRepairStatusChange: function(e) {
    const selectedIndex = parseInt(e.detail.value);
    const selectedStatus = this.data.repairStatusOptions[selectedIndex].value;
    this.setData({
      repairStatusIndex: selectedIndex,
      'operateForm.repairStatus': selectedStatus
    });
  },
  submitOperate: function() {
    const { currentRepairId, operateForm, isAdmin } = this.data;
    if (!isAdmin || !currentRepairId) {
      this.showMessage('无操作权限', 'error');
      return;
    }
    function formatFormData(data) {
      let arr = [];
      for (let key in data) {
        if (data.hasOwnProperty(key) && (data[key] !== undefined && data[key] !== null)) {
          arr.push(`${encodeURIComponent(key)}=${encodeURIComponent(data[key])}`);
        }
      }
      return arr.join('&');
    }
    const selectedStatus = operateForm.repairStatus;
    const repairerId = operateForm.repairerId.trim();
    const expectedTime = operateForm.expectedTime.trim();
    const repairResult = operateForm.repairResult.trim();
    const cost = operateForm.cost.trim();
    const validStatuses = this.data.repairStatusOptions.map(item => item.value);
    if (!selectedStatus || !validStatuses.includes(selectedStatus)) {
      this.showMessage(`无效状态！可选值：${validStatuses.join(',')}`, 'error');
      return;
    }
    if (repairerId && isNaN(parseInt(repairerId))) {
      this.showMessage('维修人员ID必须为数字', 'error');
      return;
    }
    if (expectedTime && !/^\d{4}-\d{2}-\d{2}$/.test(expectedTime)) {
      this.showMessage('预计时间格式错误，需为YYYY-MM-DD', 'error');
      return;
    }
    if (selectedStatus === 'completed' && (!repairResult || !cost || isNaN(parseFloat(cost)))) {
      this.showMessage('已完成状态需填写有效维修结果和费用', 'error');
      return;
    }
    if (this.data.isOperating) {
      return;
    }
    this.setData({ isOperating: true });
    wx.showLoading({ title: '操作中...' });
    const updateStatus = () => {
      const statusUrl = `/api/v1/repair/${currentRepairId}/status`;
      const statusFormData = { repair_status: selectedStatus };
      return getApp().request({
        url: statusUrl,
        method: 'PUT',
        header: {
          'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8',
          'Authorization': `Bearer ${wx.getStorageSync('token')}`
        },
        data: formatFormData(statusFormData)
      });
    };
    const handleOtherOperations = () => {
      let promise = Promise.resolve();
      if (repairerId) {
        const assignUrl = `/api/v1/repair/${currentRepairId}/assign`;
        const assignFormData = {
          repairer_id: parseInt(repairerId),
          expected_time: expectedTime || ''
        };
        promise = promise.then(() => getApp().request({
          url: assignUrl,
          method: 'PUT',
          header: {
            'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8',
            'Authorization': `Bearer ${wx.getStorageSync('token')}`
          },
          data: formatFormData(assignFormData)
        }));
      }
      if (repairResult) {
        const resultUrl = `/api/v1/repair/${currentRepairId}/result`;
        const resultFormData = {
          repair_notes: operateForm.repairNotes.trim() || '',
          repair_result: repairResult,
          cost: parseFloat(cost) || 0,
          completed: selectedStatus === 'completed' ? 'true' : 'false'
        };
        promise = promise.then(() => getApp().request({
          url: resultUrl,
          method: 'PUT',
          header: {
            'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8',
            'Authorization': `Bearer ${wx.getStorageSync('token')}`
          },
          data: formatFormData(resultFormData)
        }));
      }
      return promise;
    };
    updateStatus()
      .then(statusRes => {
        if (statusRes.code !== 200) {
          throw new Error(`状态更新失败：${statusRes.message || statusRes.detail || '未知错误'}`);
        }
        return handleOtherOperations();
      })
      .then(otherRes => {
        wx.hideLoading();
        this.setData({ isOperating: false });
        this.showMessage('操作成功（状态已同步更新）', 'success');
        this.closeOperateModal();
        this.loadRepairRecords();
      })
      .catch(err => {
        wx.hideLoading();
        this.setData({ isOperating: false });
        console.error('操作失败:', err);
        this.showMessage(`操作失败：${err.message}`, 'error');
      });
  },
  showMessage: function(message, type = 'info') {
    this.setData({ message, messageType: type });
    setTimeout(() => {
      this.setData({ message: '', messageType: '' });
    }, 3000);
  }
});