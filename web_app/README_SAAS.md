# TimerPro SaaS 多商家智能计时收银系统 (手作/DIY版)

## 系统概述

TimerPro SaaS 是一款专为各类按时计费实体店（特别优化的场景为：手作店、DIY工坊、桌游店、台球厅等）打造的多租户智能收银系统。
系统采用真·SaaS架构设计，支持多个商家独立注册、独立设置、完全数据物理隔离。前端采用现代化动态响应设计，体验媲美原生App。

## 系统升级特性（最新 SaaS 版）

1. **多端时钟同步机制**：首创基于 `elapsed_sec` 增量计算的纯净前端渲染机制，永久解决 Safari/Chrome 等跨浏览器 `Date` 对象解析不一致导致的计时器乱码跳 0 Bug。
2. **场景文案适配**：深度贴合手作店场景逻辑，摒弃传统网吧的“上机/下机”词汇，采用“制作中/开单”等优雅文案。
3. **精准的进阶核心计费引擎**：
   - 独家实现了“进阶阶梯计速”与“精确按比例计速”自如切换。
   - 具有智能“抹零免单界限(X)”、“进位分割系数(K)”等专业级行业特性。
   - 大幅优化了团购券加时算法与基础全局时价的解耦映射模式。
4. **灵活的安全与推广机制**：
   - 引入精简注册流程：支持直接免验证码秒级开店，并自动通过 SMTP 服务发送专属开通欢迎邮件。
   - 登录凭据优化：“记住我”选项下放长达 30 天的超长效 Token 体验。
   - **一键游客免密体验**：内建系统级沙盒店体验账号（`guest@timerpro.com`），方便推广引流。

---

## 技术栈

- **后端核心**: FastAPI (Python) + SQLAlchemy + SQLite
- **安全认证**: JWT Token 双令牌机制 + Bcrypt 密码强加密
- **前端页面**: Vue 3 (Options API) + Tailwind CSS + RemixIcon
- **部署环境**: Docker + Docker Compose

---

## 快速部署指南

### 1. 环境与配置初始化

```bash
cd web_app
pip install -r requirements.txt

# (可选) 复制并配置环境变量文件，填入 SMTP_ 等邮件服务参数
# cp .env.example .env

python init_db.py  # 首次运行：创建所有基础数据库结构
```

### 2. 启动服务 

```bash
python main_saas.py  # 默认在 5050 端口启动
```

*(注：生产环境建议配合 `nohup` 或 PM2/Supervisor 等进程守护工具运行。如果使用了 Nginx 反向代理，请务必在 Nginx 配置中加上 `proxy_set_header Host $host;` 以保证二维码域名获取准确)*

### 3. 访问入口 (本地测试)

- **主入口(自动拦截未登录)**: `http://localhost:5050/index.html`
- **注册页面**: `http://localhost:5050/register.html`
- **登录页面**: `http://localhost:5050/login.html`
- **超级管理后台**: `http://localhost:5051` （需管理员账号密码）

---

## 核心数据库组成

- `shops`: 商家基本信息及核心计费规则大 JSON (Config_data)
- `users`: 全局商家及员工账号系统 
- `verify_codes`: 邮箱验证码流转表
- `orders`: 当前活跃状态的客流/制单数据表
- `order_history` / `order_pause_logs`: 挂账、报表结算流水相关核心账本

---

## 项目开发&迭代里程碑

- [x] 多租户架构底层逻辑重构
- [x] 全面转为邮箱验证码校验流转
- [x] PC & 移动端全兼容的玻璃拟态(Glassmorphism)自适应 UI
- [x] iOS/Mac Safari 计时器归零漏洞终极修复
- [x] SaaS设置项全面引入悬浮 Tooltip 专业级提示气泡
- [x] 单机/连坐同行订单一键批量结账逻辑
- [x] 独立超级管理后台 (端口 5051，HTTP Basic Auth 认证)
- [x] 增加演示模式/沙盒临时店功能 (免密一键游客体验)
- [x] Nginx 反向代理 Host 溯源降级兼容 (修复顾客端扫码域名丢失问题)
- [ ] 系统数据报表大屏可视化 (规划中)
- [ ] 日志追溯与错误上报中心 (规划中)
