# TimerPro SaaS 快速启动指南

## 5 分钟快速开始

### 1. 安装依赖

```bash
cd web_app
pip install -r requirements.txt
```

### 2. 初始化数据库

```bash
python init_db.py
```

输出示例：
```
============================================================
数据库表创建成功
============================================================
开始初始化默认数据...
============================================================
数据库初始化完成！
============================================================
测试商家:
  - 商家名称: 星空桌球俱乐部
  - 商家编码: starbilliards
  - 联系电话: 13800138000

管理员账号:
  - 用户名: admin
  - 密码: admin888
  - 角色: admin
============================================================
```

### 3. 启动服务器

```bash
python main_saas.py
```

输出示例：
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

### 4. 访问系统

打开浏览器访问：

- **登录页面**: http://localhost:8000/login.html
- **注册页面**: http://localhost:8000/register.html
- **主界面**: http://localhost:8000/index.html
- **API 文档**: http://localhost:8000/docs

### 5. 测试登录

使用默认账号登录：
- **用户名**: `admin`
- **密码**: `admin888`

或者使用手机号：
- **手机号**: `13800138000`
- **密码**: `admin888`

## 注册新商家

### 方式 1: 使用注册页面

1. 访问 http://localhost:8000/register.html
2. 填写店铺信息
3. 填写管理员信息
4. 发送验证码（测试环境验证码会显示在服务器控制台）
5. 完成注册

### 方式 2: 使用 API

```bash
# 发送验证码
curl -X POST http://localhost:8000/api/merchants/verify-code/send \
  -H "Content-Type: application/json" \
  -d '{"phone": "13900139000", "code_type": "register"}'

# 注册商家
curl -X POST http://localhost:8000/api/merchants/register \
  -H "Content-Type: application/json" \
  -d '{
    "shop_name": "我的店铺",
    "shop_code": "myshop001",
    "contact_phone": "13900139000",
    "admin_name": "店长",
    "password": "password123",
    "password_confirm": "password123",
    "verify_code": "123456"
  }'
```

## 测试系统

运行自动化测试脚本：

```bash
python test_saas.py
```

## Docker 部署

### 使用 Docker Compose

```bash
# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### 手动构建

```bash
# 构建镜像
docker build -t timerpro-saas .

# 运行容器
docker run -d -p 8000:8000 \
  -v $(pwd)/shop_config.json:/app/shop_config.json \
  -v $(pwd)/active_data.json:/app/active_data.json \
  timerpro-saas
```

## 常见问题

### Q: 数据库文件在哪里？

A: SQLite 数据库文件 `timerpro_saas.db` 会在 `web_app` 目录下自动创建。

### Q: 如何重置数据库？

A: 删除 `timerpro_saas.db` 文件，然后重新运行 `python init_db.py`。

### Q: 验证码怎么获取？

A: 测试环境下验证码会输出到服务器控制台，生产环境需要集成短信服务。

### Q: 如何添加员工账号？

A: 登录后调用 `/api/merchants/users` 接口创建员工账号。

### Q: 如何修改商家配置？

A: 登录后调用 `/api/config/shop` 接口修改配置。

## 下一步

- 查看完整文档: `README_SAAS.md`
- 查看 API 文档: http://localhost:8000/docs
- 运行测试: `python test_saas.py`
- 查看改造总结: `../documents/SaaS_改造总结.md`
