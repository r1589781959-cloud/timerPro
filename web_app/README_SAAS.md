# TimerPro SaaS 多商家收银系统

## 系统概述

TimerPro SaaS 是一个多商家智能收银系统，支持多个商家同时在线使用，数据完全隔离。

## 技术栈

- **后端**: FastAPI + SQLAlchemy + SQLite
- **认证**: JWT Token + Bcrypt 密码加密
- **前端**: Vue 3 + Tailwind CSS
- **部署**: Docker + Docker Compose

## 快速开始

### 1. 安装依赖

```bash
cd web_app
pip install -r requirements.txt
```

### 2. 初始化数据库

```bash
python init_db.py
```

这将创建数据库表并初始化测试数据：
- 测试商家: `starbilliards`
- 管理员账号: `admin` / `admin888`

### 3. 启动服务器

```bash
# 开发模式
python main_saas.py

# 或使用 uvicorn
uvicorn main_saas:app --reload --host 0.0.0.0 --port 8000
```

### 4. 访问系统

- **注册页面**: http://localhost:8000/register.html
- **登录页面**: http://localhost:8000/login.html
- **主界面**: http://localhost:8000/index.html

## Docker 部署

```bash
# 构建镜像
docker-compose build

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f
```

## API 文档

启动服务器后访问：
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 主要功能

### 商家管理
- 商家注册（手机验证码验证）
- 商家登录（JWT Token 认证）
- 商家信息管理
- 员工账号管理

### 订单管理
- 开台/结账
- 订单状态管理（暂停/恢复/挂账）
- 加时功能
- 团购核销
- 历史记录查询

### 配置管理
- 店铺配置（价格、时间等）
- 团购配置管理
- 计费模式设置

## 测试

运行测试脚本：

```bash
python test_saas.py
```

## 数据库结构

### 主要表

- `shops` - 商家表
- `users` - 用户表
- `orders` - 订单表
- `order_pause_logs` - 暂停日志表
- `order_add_times` - 加时记录表
- `order_group_buys` - 团购订单关联表
- `group_buys` - 团购配置表
- `system_configs` - 系统配置表
- `order_history` - 订单历史表
- `verify_codes` - 验证码表

## 安全说明

1. **密码加密**: 使用 Bcrypt 算法加密存储
2. **JWT Token**: 支持访问令牌和刷新令牌
3. **数据隔离**: 每个商家的数据完全隔离
4. **权限控制**: 支持角色权限管理（admin/employee/staff）

## 与单商家版本的兼容性

- 桌面版（timerProV15.py）保持独立，使用文件存储
- Web 版本已升级为多商家 SaaS 架构
- 小程序版本通过 API 接口使用云端数据

## 开发计划

- [ ] 完善订单管理功能（开台、结账等）
- [ ] 添加数据统计和报表
- [ ] 实现消息通知功能
- [ ] 集成短信验证码服务
- [ ] 添加文件上传功能（Logo等）
- [ ] 小程序端对接

## 问题反馈

如有问题，请联系开发团队。
