# TimerPro SaaS 多商家系统 - 项目交接文档

**交接时间**: 2026年4月17日
**交接人**: Claude AI
**接收人**: antigravity

---

## 一、项目概述

### 1.1 项目目标
将 TimerPro Web 版本从单商家架构改造为多商家 SaaS 架构，支持多个商家同时在线使用，数据完全隔离。

### 1.2 技术栈
- **后端**: FastAPI + SQLAlchemy + SQLite
- **认证**: JWT Token + Bcrypt 密码加密
- **前端**: Vue 3 + Tailwind CSS
- **部署**: Docker + Docker Compose

---

## 二、已完成的功能

### 2.1 数据库架构
✅ **完成** - 完整的数据库表结构设计

| 表名 | 说明 | 状态 |
|------|------|------|
| shops | 商家表 | ✅ |
| users | 用户表 | ✅ |
| orders | 订单表 | ✅ |
| order_pause_logs | 暂停日志表 | ✅ |
| order_add_times | 加时记录表 | ✅ |
| order_group_buys | 团购订单关联表 | ✅ |
| group_buys | 团购配置表 | ✅ |
| system_configs | 系统配置表 | ✅ |
| order_history | 订单历史表 | ✅ |
| api_keys | API密钥表 | ✅ |
| verify_codes | 验证码表 | ✅ |
| merchant_applications | 商家申请表 | ✅ |
| system_logs | 系统日志表 | ✅ |

### 2.2 认证系统
✅ **完成** - JWT Token 认证机制

- JWT Token 生成和验证
- 访问令牌和刷新令牌
- Bcrypt 密码加密
- 手机验证码生成
- 商家认证依赖注入
- 角色权限控制 (admin/employee/staff)

### 2.3 商家管理 API
✅ **完成** - 完整的商家管理接口

| 接口 | 方法 | 路径 | 状态 |
|------|------|------|------|
| 发送验证码 | POST | /api/merchants/verify-code/send | ✅ |
| 检查编码 | GET | /api/merchants/check-code | ✅ |
| 商家注册 | POST | /api/merchants/register | ✅ |
| 商家登录 | POST | /api/merchants/login | ✅ |
| 刷新Token | POST | /api/merchants/refresh | ✅ |
| 获取商家信息 | GET | /api/merchants/info | ✅ |
| 更新商家信息 | PUT | /api/merchants/info | ✅ |
| 获取用户列表 | GET | /api/merchants/users | ✅ |
| 创建用户 | POST | /api/merchants/users | ✅ |
| 更新用户 | PUT | /api/merchants/users/{user_id} | ✅ |
| 删除用户 | DELETE | /api/merchants/users/{user_id} | ✅ |
| 商家统计 | GET | /api/merchants/stats | ✅ |

### 2.4 订单和配置 API
✅ **完成** - 基础配置和订单查询接口

| 接口 | 方法 | 路径 | 状态 |
|------|------|------|------|
| 获取店铺配置 | GET | /api/config/shop | ✅ |
| 更新店铺配置 | PUT | /api/config/shop | ✅ |
| 获取团购配置 | GET | /api/config/group-buys | ✅ |
| 创建团购 | POST | /api/config/group-buys | ✅ |
| 更新团购 | PUT | /api/config/group-buys/{gb_config_id} | ✅ |
| 删除团购 | DELETE | /api/config/group-buys/{gb_config_id} | ✅ |
| 获取活跃订单 | GET | /api/data/active | ✅ |
| 更新活跃订单 | POST | /api/data/active | ✅ |
| 获取历史订单 | GET | /api/history | ✅ |
| 清空历史 | DELETE | /api/history | ✅ |

### 2.5 前端界面
✅ **完成** - 基础前端页面

- 注册页面 (`register.html`) - 多步骤表单
- 登录页面 (`login.html`) - 带记住我功能
- 主界面框架 (`index.html`) - 响应式布局

---

## 三、文件结构

```
E:/antigravity_project_01/
├── README.md                      # 项目总览
├── timerProV15.py                # 桌面版（保持独立）
├── Dockerfile                     # Docker配置（已更新）
├── docker-compose.yml             # Docker Compose配置
│
├── web_app/                      # Web应用目录
│   ├── main.py                   # 单商家版本（保留）
│   ├── main_saas.py              # SaaS版本主文件 ✅新增
│   ├── database.py               # 数据库模型 ✅新增
│   ├── init_db.py                # 数据库初始化 ✅新增
│   ├── auth.py                   # 认证服务 ✅新增
│   ├── requirements.txt           # 依赖清单（已更新）
│   │
│   ├── routers/                  # API路由模块 ✅新增
│   │   ├── __init__.py
│   │   ├── merchants.py          # 商家管理API
│   │   └── orders.py            # 订单配置API
│   │
│   ├── static/                   # 静态文件
│   │   ├── index.html            # 主界面（已更新）
│   │   ├── login.html            # 登录页面 ✅新增
│   │   └── register.html         # 注册页面 ✅新增
│   │
│   ├── test_saas.py              # 测试脚本 ✅新增
│   ├── README_SAAS.md            # SaaS文档 ✅新增
│   └── QUICKSTART.md             # 快速指南 ✅新增
│
├── documents/                    # 文档目录
│   ├── SaaS_改造总结.md          # 改造总结 ✅新增
│   └── SaaS系统交接文档.md       # 本文档 ✅新增
│
└── xcx_client/                   # 微信小程序（保持不变）
```

---

## 四、当前问题

### 4.1 Token验证问题
**状态**: ⚠️ 部分存在

**现象**: 
- 登录API可以正常返回token
- 核心API（商家信息、配置等）可以正常调用
- 部分API返回"无法验证凭据"错误

**可能原因**:
1. Token过期时间设置问题
2. 部分依赖注入方式不统一
3. 请求头格式问题

**调试方法**:
```python
# 检查token是否正确传递
import requests
headers = {"Authorization": f"Bearer {token}"}
response = requests.get("http://localhost:8000/api/xxx", headers=headers)
print(response.status_code, response.json())
```

### 4.2 需要完善的API
**状态**: ⏳ 待实现

以下API从单商家版本(`main.py`)迁移到SaaS版本(`main_saas.py`):

| 功能 | 原API | 状态 |
|------|--------|------|
| 开台/开桌 | POST /api/tables/open | ⏳ |
| 查看账单 | POST /api/tables/bill | ⏳ |
| 结账 | POST /api/tables/checkout | ⏳ |
| 删除订单 | DELETE /api/tables/{order_id} | ⏳ |
| 暂停 | POST /api/tables/pause | ⏳ |
| 挂账 | POST /api/tables/suspend | ⏳ |
| 取消挂账 | POST /api/tables/cancel-suspend | ⏳ |
| 加时 | POST /api/tables/add-time | ⏳ |
| 添加备注 | POST /api/tables/remark | ⏳ |
| 核销团购 | POST /api/tables/verify | ⏳ |

### 4.3 配置和部署

**JWT密钥**:
- 开发环境使用固定密钥: `timerpro-saas-secret-key-2024`
- 生产环境应从环境变量读取: `JWT_SECRET_KEY`

**数据库**:
- SQLite文件位置: `web_app/timerpro_saas.db`
- 首次运行需执行: `python init_db.py`

---

## 五、使用指南

### 5.1 快速启动

```bash
cd web_app
pip install -r requirements.txt
python init_db.py
python main_saas.py
```

### 5.2 默认测试账号

```
商家编码: starbilliards
用户名: admin 或 13800138000
密码: admin123
```

### 5.3 访问地址

- 登录页: http://localhost:8000/login.html
- 注册页: http://localhost:8000/register.html
- 主界面: http://localhost:8000/index.html
- API文档: http://localhost:8000/docs

### 5.4 Docker部署

```bash
docker-compose up -d
```

---

## 六、数据迁移

### 6.1 现有数据位置
- `shop_config.json` - 店铺配置
- `active_data.json` - 活跃订单数据
- `history_data.json` - 历史数据
- `history_log.csv` - 操作日志

### 6.2 迁移方案
参考 `init_db.py` 中的 `migrate_from_files()` 函数，需要：
1. 将JSON数据解析并转换为数据库记录
2. 指定目标商家ID（shop_id）
3. 批量插入数据库

---

## 七、后续开发建议

### 7.1 高优先级
1. **完善订单操作API** - 迁移开台、结账等核心功能
2. **修复Token验证问题** - 统一认证逻辑
3. **数据迁移工具** - 实现JSON到数据库的完整迁移

### 7.2 中优先级
4. **集成短信服务** - 阿里云/腾讯云验证码
5. **文件上传功能** - Logo等图片上传
6. **数据统计和报表** - 营业数据统计

### 7.3 低优先级
7. **性能优化** - 数据库索引、缓存
8. **操作日志** - 完整的审计日志
9. **数据备份恢复** - 定期备份机制

---

## 八、兼容性说明

### 8.1 桌面版
- **文件**: `timerProV15.py`
- **状态**: 保持独立，使用文件存储
- **影响**: 无

### 8.2 单商家Web版
- **文件**: `web_app/main.py`
- **状态**: 保留，继续使用JSON文件存储
- **影响**: 无

### 8.3 小程序
- **目录**: `xcx_client/`
- **状态**: 保持不变
- **对接方式**: 通过API连接，需在请求头携带 `X-Shop-Code`

---

## 九、调试日志

### 9.1 最近解决的问题
1. ✅ 修复 `aiosqlite` 异步引擎问题 → 改用同步引擎
2. ✅ 修复 `on_event` 废弃警告 → 改用 `lifespan`
3. ✅ 修复数据库关系配置错误 → 添加 `order` relationship
4. ✅ 修复 bcrypt 版本兼容性 → 直接使用 bcrypt 模块
5. ✅ 修复 JWT_SECRET_KEY 问题 → 使用固定密钥

### 9.2 当前代码状态

**服务器启动**: ✅ 正常
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

**数据库初始化**: ✅ 成功
```
数据库表创建成功
数据库初始化完成！
```

**登录功能**: ✅ 正常
```
curl -X POST /api/merchants/login
# 返回: access_token, refresh_token, shop, user
```

**API测试结果**:
```
✓ /api/merchants/info - 商家信息
✓ /api/config/shop - 店铺配置
✓ /api/config/group-buys - 团购配置
```

---

## 十、交付清单

### 10.1 代码文件
- [x] 数据库模型 (`database.py`)
- [x] 认证服务 (`auth.py`)
- [x] 主应用文件 (`main_saas.py`)
- [x] 初始化脚本 (`init_db.py`)
- [x] 商家管理路由 (`routers/merchants.py`)
- [x] 订单配置路由 (`routers/orders.py`)
- [x] 前端页面 (login.html, register.html, index.html)
- [x] 测试脚本 (`test_saas.py`)

### 10.2 文档文件
- [x] SaaS使用文档 (`web_app/README_SAAS.md`)
- [x] 快速启动指南 (`web_app/QUICKSTART.md`)
- [x] 改造总结 (`documents/SaaS_改造总结.md`)
- [x] 交接文档 (`documents/SaaS系统交接文档.md`)

### 10.3 配置文件
- [x] 依赖清单 (`web_app/requirements.txt`)
- [x] Docker配置 (`Dockerfile`)

---

## 十一、联系方式

如有问题，请参考：
- API文档: http://localhost:8000/docs
- 完整文档: `web_app/README_SAAS.md`
- 快速指南: `web_app/QUICKSTART.md`

---

**交接完成日期**: 2026年4月17日
**项目版本**: 2.0.0
**总体状态**: 基础架构完成，核心API可用，需继续完善订单操作功能
