# 第三阶段：多商家数据管理与认证系统完善

## 背景

核心计费功能已稳定。现在系统有完整的JWT认证基础设施（`auth.py`）、商家管理后端（`merchants.py`）、前端登录页（`login.html`）和注册页（`register.html`），但**认证链路和数据隔离实际上并未真正启用**——目前 `index.html` 的请求虽带了 `Authorization` 头，但实际的体验流程存在以下断点和隐患。

## 当前状态分析

### ✅ 已有（后端）
- JWT Token 生成/验证/刷新（`auth.py`）
- 密码 bcrypt 哈希（`PasswordService`）
- 验证码生成/保存（`VerifyCodeService`，控制台输出，无短信对接）
- 注册接口（`POST /api/merchants/register`）含完整流程：验证码 → 创建Shop → 创建User → 初始化配置 → 返回Token
- 登录接口（`POST /api/merchants/login`）：手机号+密码+JWT
- `get_current_user` / `get_current_shop` 依赖注入
- 商家信息 CRUD / 用户管理 CRUD

### ✅ 已有（前端）
- `login.html`：商家编码(选填)+手机号+密码 → 调用 `/api/merchants/login`
- `register.html`：三步注册流程(基本信息→验证码→成功)
- `index.html`：`fetch` 拦截器自动加 `Authorization` Bearer Token，401 跳登录页

### ❌ 问题清单

| # | 问题 | 严重性 | 说明 |
|---|------|--------|------|
| 1 | **登录后 shopInfo 初始化断裂** | 🔴 | `login.html` 存为 `user_info`，`index.html` 读取 `shop_info` → key 不匹配，导航栏显示默认值 |
| 2 | **shop_code 未保存** | 🔴 | 登录后请求头带 `X-Shop-Code`，但 `localStorage` 中没有存 `shop_code` |
| 3 | **注册成功后跳转到登录而非主页** | 🟡 | 注册成功已经拿到了 Token，不需要重新登录 |
| 4 | **Token 过期无静默刷新** | 🟡 | 2小时过期后直接跳登录，没有用 refresh_token 续期 |
| 5 | **开发环境无法实际发验证码** | 🟡 | 验证码输出在控制台，用户看不到，需要简化开发体验 |
| 6 | **数据隔离已有但需验证** | 🟢 | `get_current_shop` 已在 orders/config/history 使用，理论上已隔离 |

---

## 实施方案

### 1. 修复 localStorage Key 不匹配

#### [MODIFY] [login.html](file:///e:/antigravity_project_01/web_app/static/login.html)
登录成功后 `localStorage.setItem('user_info', ...)` → 改为同时存 `shop_info` 和 `shop_code`：
```js
localStorage.setItem('shop_info', JSON.stringify({
    shop_name: data.shop.shop_name,
    shop_code: data.shop.shop_code,
    username: data.user.real_name || data.user.username
}));
localStorage.setItem('shop_code', data.shop.shop_code);
```

#### [MODIFY] [register.html](file:///e:/antigravity_project_01/web_app/static/register.html)
注册成功后做同样的存储操作，并自动跳转到主页而非登录页。

#### [MODIFY] [index.html](file:///e:/antigravity_project_01/web_app/static/index.html)
- 保持读 `shop_info` 不变（已一致）
- `mounted()` 时调 `/api/merchants/info` 刷新 `shopInfo`

---

### 2. 加入 Token 静默刷新

#### [MODIFY] [index.html](file:///e:/antigravity_project_01/web_app/static/index.html)
在 fetch 拦截器中，当收到 401 时先尝试用 `refresh_token` 刷新，成功则重试原请求，失败才跳登录页：
```js
if (res.status === 401) {
    const refreshed = await tryRefreshToken();
    if (refreshed) return originalFetch(url, config); // 重试
    localStorage.clear();
    window.location.href = '/login.html';
}
```

---

### 3. 优化开发环境验证码体验

#### [MODIFY] [register.html](file:///e:/antigravity_project_01/web_app/static/register.html)
发送验证码后显示提示："验证码已发送到控制台（开发模式）"，使开发测试更顺畅。

---

### 4. mounted 同步商家信息

#### [MODIFY] [index.html](file:///e:/antigravity_project_01/web_app/static/index.html)
`mounted()` 调用 `/api/merchants/info` 获取最新商家名、编码等，写入 `shopInfo` 和 `localStorage`，确保多端登录后信息始终最新。

---

## User Review Required

> [!IMPORTANT]
> 以上方案聚焦在**打通认证链路 + 数据一致性**，**不涉及**引入新的多商家管理后台（如超管查看所有商家列表等）。如果你后续需要超级管理员后台，那是另一个独立模块。

> [!NOTE]
> 验证码目前仍然是控制台输出，如果需要对接真实短信（阿里云/腾讯云 SMS），那属于部署阶段的工作，建议当前先不做。

## 验证计划

1. **注册流程测试**：新注册一个商家 → 验证自动跳转主页 → 导航栏显示正确店名
2. **登录流程测试**：退出 → 重新登录 → 导航栏显示正确店名/用户名
3. **数据隔离验证**：注册第二个商家 → 登录后确认看不到第一个商家的订单/配置/历史
4. **Token 刷新测试**：手动过期 access_token → 确认自动刷新，不跳登录页
