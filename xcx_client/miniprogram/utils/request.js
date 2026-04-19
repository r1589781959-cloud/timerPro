/**
 * TimerPro API 请求封装
 */
const BASE_URL_DEV = 'http://localhost:8000'; // 尝试使用 localhost 替代 127.0.0.1
const BASE_URL_PROD = 'https://your-cloud-domain.com'; // 生产环境地址 (云端)

const isDev = true; // 开发阶段开关
const baseUrl = isDev ? BASE_URL_DEV : BASE_URL_PROD;

const request = (url, method = 'GET', data = {}) => {
  return new Promise((resolve, reject) => {
    wx.request({
      url: baseUrl + url,
      method: method,
      data: data,
      header: {
        'content-type': 'application/json'
      },
      success: (res) => {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data);
        } else {
          wx.showToast({
            title: '请求失败: ' + res.statusCode,
            icon: 'none'
          });
          reject(res);
        }
      },
      fail: (err) => {
        wx.showToast({
          title: '网络错误，请检查后端状态',
          icon: 'none'
        });
        reject(err);
      }
    });
  });
};

module.exports = {
  get: (url, data) => request(url, 'GET', data),
  post: (url, data) => request(url, 'POST', data),
  put: (url, data) => request(url, 'PUT', data),
  delete: (url, data) => request(url, 'DELETE', data),
  baseUrl
};
