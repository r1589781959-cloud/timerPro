const api = require('../../utils/request.js');

Page({
  data: {
    orders: [],
    loading: false,
    shopConfig: null,
    now: Date.now(),
    // 开台弹窗表单
    showOpenDialog: false,
    newOrder: {
      phone: '',
      count: 1,
      mode: 'pay_later',
      configId: null,
      remark: ''
    },
    // 选项数据
    modeLabels: ['🕒 先玩后付', '⏳ 固定时长', '🎫 团购套餐', '♾️ 全天畅玩', '🎨 单板不限时'],
    modeValues: ['pay_later', 'fixed', 'group_buy', 'unlimited', 'single_board'],
    selectedModeLabel: '🕒 先玩后付',
    showModeDropdown: false, // 控制自定义下拉显示
    fixedTimeOptions: [60, 120, 180, 240, 300],
    
    // 过滤与排序
    filterMode: 'all',
    searchQuery: '',
    sortMode: 'id_desc'
  },

  onLoad() {
    this.fetchConfig();
    this.fetchActiveData();
    // 启动全局计时器，每秒刷新一次
    this.timer = setInterval(() => {
      this.updateDisplayData();
    }, 1000);
  },

  onUnload() {
    if (this.timer) clearInterval(this.timer);
  },

  // 获取店铺配置
  async fetchConfig() {
    try {
      const config = await api.get('/api/config/shop');
      this.setData({ shopConfig: config });
    } catch (err) { console.error('获取配置失败', err); }
  },

  // 获取正在上机的数据
  async fetchActiveData() {
    this.setData({ loading: true });
    try {
      const res = await api.get('/api/data/active');
      this.rawOrders = Object.entries(res.g || {}).map(([id, val]) => ({ id, ...val }));
      this.updateDisplayData();
    } catch (err) { console.error('获取订单失败', err); } finally { this.setData({ loading: false }); }
  },

  // 核心渲染逻辑：计算时间、进度、过滤、排序
  updateDisplayData() {
    if (!this.rawOrders) return;
    const { searchQuery, sortMode, filterMode } = this.data;
    const nowTs = Date.now();

    const modeMap = {
      'pay_later': '先玩后付',
      'fixed': '固定时长',
      'group_buy': '团购套餐',
      'unlimited': '畅玩',
      'single_board': '单板不限',
      'time_slot': '时段模式'
    };

    let list = this.rawOrders.map(order => {
      const startPieces = order.start_time.split(' ');
      const startTimeShort = startPieces.length > 1 ? startPieces[1].substring(0, 5) : order.start_time;
      const startTs = new Date(order.start_time.replace(/-/g, '/')).getTime();
      const elapsedSec = Math.floor((nowTs - startTs) / 1000);
      
      // 计算显示文字
      const h = Math.floor(elapsedSec / 3600);
      const m = Math.floor((elapsedSec % 3600) / 60);
      const s = elapsedSec % 60;
      const timeStr = `${h.toString().padStart(2,'0')}:${m.toString().padStart(2,'0')}:${s.toString().padStart(2,'0')}`;
      
      return { 
        ...order, 
        timeStr, 
        start_time_short: startTimeShort,
        mode_label: modeMap[order.mode] || order.mode,
        progress: this.calculateProgress(order, elapsedSec),
        isOvertime: order.limit_min > 0 && elapsedSec > (order.limit_min * 60)
      };
    });

    // 过滤
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      list = list.filter(o => o.phone.includes(q) || (o.remark || '').toLowerCase().includes(q));
    }

    // 排序
    list.sort((a, b) => {
      if (sortMode === 'id_desc') return b.id - a.id;
      if (sortMode === 'id_asc') return a.id - b.id;
      if (sortMode === 'phone_asc') return a.phone.localeCompare(b.phone);
      if (sortMode === 'progress_desc') return b.progress - a.progress;
      return 0;
    });

    this.setData({ orders: list });
  },

  calculateProgress(order, elapsedSec) {
    if (order.limit_min > 0) {
      return Math.min(100, (elapsedSec / (order.limit_min * 60)) * 100);
    } else if (order.mode === 'pay_later') {
      return (elapsedSec % 3600) / 36; // 先玩后付显示小时内进度
    }
    return 0;
  },

  onInputSearch(e) {
    this.setData({ searchQuery: e.detail.value }, () => this.updateDisplayData());
  },

  onSortChange(e) {
    const modes = ['id_desc', 'id_asc', 'phone_asc', 'progress_desc'];
    this.setData({ sortMode: modes[e.detail.value] }, () => this.updateDisplayData());
  },

  // --- 弹窗与表单逻辑 ---
  toggleModeDropdown() {
    this.setData({ showModeDropdown: !this.data.showModeDropdown });
  },

  selectMode(e) {
    const { val, label } = e.currentTarget.dataset;
    this.setData({
      'newOrder.mode': val,
      selectedModeLabel: label,
      showModeDropdown: false,
      'newOrder.configId': null
    });
  },

  onOpenTable() {
    this.setData({
      showOpenDialog: true,
      newOrder: { phone: '', count: 1, mode: 'pay_later', configId: null, remark: '' },
      selectedModeLabel: '🕒 先玩后付'
    });
  },

  onCloseDialog() {
    this.setData({ showOpenDialog: false });
  },

  stopBubble() {}, // 阻止冒泡

  onInputPhone(e) {
    this.setData({ 'newOrder.phone': e.detail.value });
  },

  onInputCount(e) {
    this.setData({ 'newOrder.count': parseInt(e.detail.value) || 1 });
  },

  onModeChange(e) {
    const idx = e.detail.value;
    this.setData({
      'newOrder.mode': this.data.modeValues[idx],
      selectedModeLabel: this.data.modeLabels[idx],
      'newOrder.configId': null
    });
  },

  onFixedTimeChange(e) {
    const val = this.data.fixedTimeOptions[e.detail.value];
    this.setData({ 'newOrder.configId': val });
  },

  onInputConfigId(e) {
    this.setData({ 'newOrder.configId': e.detail.value });
  },

  onQuickSelectTime(e) {
    const val = e.currentTarget.dataset.val;
    this.setData({ 'newOrder.configId': val });
  },

  onSelectGroupBuy(e) {
    const item = e.currentTarget.dataset.item;
    this.setData({ 'newOrder.configId': item });
  },

  onInputRemark(e) {
    this.setData({ 'newOrder.remark': e.detail.value });
  },

  async onSubmitOpen() {
    const { newOrder } = this.data;
    if (!newOrder.phone) {
      return wx.showToast({ title: '请输入标识/台号', icon: 'none' });
    }

    wx.showLoading({ title: '正在开台...' });
    try {
      const res = await api.post('/api/tables/open', newOrder);
      if (res.success) {
        wx.showToast({ title: '开台成功', icon: 'success' });
        this.onCloseDialog();
        this.fetchActiveData(); // 刷新列表
      }
    } catch (err) {
      console.error('开台失败', err);
    } finally {
      wx.hideLoading();
    }
  },

  // 下拉刷新
  onPullDownRefresh() {
    this.fetchActiveData().then(() => {
      wx.stopPullDownRefresh();
    });
  },

  // 辅助函数：格式化显示（此处逻辑后续完善）
  formatCard(order) {
    // 逻辑待实现
  }
});
